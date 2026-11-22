import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import yaml

from .models import EligibilityResponse, RuleCitation, WhatIfResponse


def coerce_boolean(val: Any) -> Optional[bool]:
    """Coerces various truthy/falsy representations to boolean or None if invalid."""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val != 0
    if isinstance(val, str):
        v = val.strip().lower()
        if v in ("true", "yes", "1", "t", "y"):
            return True
        if v in ("false", "no", "0", "f", "n"):
            return False
    return None


class EligibilityEngine:
    """Deterministic YAML-driven rules engine for PM-KISAN eligibility. No LLM used."""

    def __init__(self, rules_path: Optional[str] = None):
        if rules_path is None:
            rules_path = str(Path(__file__).resolve().parent / "pmkisan_rules.yaml")
        self.rules_path = rules_path
        self.rules_config = self._load_rules()

    def _load_rules(self) -> Dict[str, Any]:
        with open(self.rules_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    @property
    def rules(self) -> List[Dict[str, Any]]:
        return self.rules_config.get("rules", [])

    def evaluate(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluates a citizen profile against PM-KISAN rules without an LLM."""
        failed_rules: List[Dict[str, Any]] = []
        passed_rules: List[Dict[str, Any]] = []
        missing_inputs: Set[str] = set()
        citations_map: Dict[str, str] = {}

        for rule in self.rules:
            req_fields = rule.get("required_fields", [])
            field_name = rule.get("field")
            rule_id = rule["rule_id"]
            clause_id = rule["clause_id"]
            rule_version = rule["rule_version"]
            name = rule["name"]
            citation = rule.get("citation", "")
            failure_reason = rule.get("failure_reason", "")
            rule_type = rule.get("type")

            # Check if required fields are present in profile
            is_missing = False
            for req in req_fields:
                if req not in profile or profile[req] is None:
                    missing_inputs.add(req)
                    is_missing = True

            if is_missing:
                continue

            raw_val = profile.get(field_name)
            has_failed = False
            override_reason = None

            # Rule evaluation dispatch
            if rule_type == "boolean_true":
                b_val = coerce_boolean(raw_val)
                if b_val is not True:
                    has_failed = True

            elif rule_type == "boolean_false":
                b_val = coerce_boolean(raw_val)
                if b_val is True:
                    has_failed = True

            elif rule_type == "greater_than_zero":
                try:
                    num_val = float(raw_val)
                    if num_val <= 0.0:
                        has_failed = True
                except (ValueError, TypeError):
                    has_failed = True

            elif rule_type == "govt_employee_check":
                is_govt = coerce_boolean(raw_val)
                is_class_iv = coerce_boolean(profile.get("is_class_iv_or_group_d", False))
                # Excluded if government employee UNLESS Class IV / Group D / MTS
                if is_govt is True and is_class_iv is not True:
                    has_failed = True

            elif rule_type == "pension_limit_check":
                try:
                    pension = float(raw_val) if raw_val is not None else 0.0
                except (ValueError, TypeError):
                    pension = 0.0

                is_class_iv = coerce_boolean(profile.get("is_class_iv_or_group_d", False))
                # Excluded if pension >= 10,000 UNLESS Class IV / Group D
                if pension >= 10000.0 and is_class_iv is not True:
                    has_failed = True
                    override_reason = f"Monthly pension of Rs. {pension:,.2f} is equal to or exceeds the Rs. 10,000 limit."

            if has_failed:
                failed_rules.append({
                    "rule_id": rule_id,
                    "name": name,
                    "clause_id": clause_id,
                    "rule_version": rule_version,
                    "reason": override_reason or failure_reason,
                    "citation": citation,
                })
                if clause_id not in citations_map:
                    citations_map[clause_id] = citation
            else:
                passed_rules.append({
                    "rule_id": rule_id,
                    "name": name,
                    "clause_id": clause_id,
                    "rule_version": rule_version,
                })

        # Verdict calculation
        if failed_rules:
            verdict = "INELIGIBLE"
        elif missing_inputs:
            verdict = "INCOMPLETE"
        else:
            verdict = "ELIGIBLE"

        # Format citations
        citations = [{"id": cid, "text": text} for cid, text in citations_map.items()]

        return {
            "verdict": verdict,
            "failed_rules": failed_rules,
            "passed_rules": passed_rules,
            "missing_inputs": sorted(list(missing_inputs)),
            "citations": citations,
        }

    def whatif(self, profile: Dict[str, Any], changes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates verdict diff when applying hypothetical changes to a profile."""
        original_result = self.evaluate(profile)
        updated_profile = {**profile, **changes}
        updated_result = self.evaluate(updated_profile)

        orig_failed_ids = {r["rule_id"] for r in original_result["failed_rules"]}
        new_failed_ids = {r["rule_id"] for r in updated_result["failed_rules"]}

        fixed_rules = sorted(list(orig_failed_ids - new_failed_ids))
        newly_failed_rules = sorted(list(new_failed_ids - orig_failed_ids))

        verdict_changed = original_result["verdict"] != updated_result["verdict"]

        return {
            "original_verdict": original_result["verdict"],
            "new_verdict": updated_result["verdict"],
            "verdict_changed": verdict_changed,
            "changes_applied": changes,
            "fixed_rules": fixed_rules,
            "newly_failed_rules": newly_failed_rules,
            "original_result": original_result,
            "updated_result": updated_result,
        }


# Singleton engine instance
_engine: Optional[EligibilityEngine] = None


def get_engine() -> EligibilityEngine:
    global _engine
    if _engine is None:
        _engine = EligibilityEngine()
    return _engine


def evaluate_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    return get_engine().evaluate(profile)


def whatif_analysis(profile: Dict[str, Any], changes: Dict[str, Any]) -> Dict[str, Any]:
    return get_engine().whatif(profile, changes)
