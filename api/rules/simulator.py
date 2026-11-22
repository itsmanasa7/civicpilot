from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import copy

from demo_users import SEEDED_DEMO_USERS
from rules.engine import evaluate_profile
from rag.service import RAGService


AMENDMENT_CORPUS_TEXT = """
## Clause PMK-A-1.3: Amendment 2026.2 - Stricter Cutoff Date Enforcement on Land Transfers
**Effective Date**: 2026-04-01  
**Clause ID**: PMK-A-1.3  
**Rule Version**: 2026.2  
**Text**: As per the Ministry of Agriculture and Farmers Welfare notification, all cultivable land parcels transferred, mutated, or registered in the beneficiary's name after the scheme cutoff date of 01-February-2019 are strictly disqualified from PM-KISAN benefits. Beneficiaries whose land mutation occurred post-cutoff without a certified succession certificate from the competent revenue authority (Tehsil/SDM) will have their installment disbursements withheld immediately.
"""


class RuleChangeSimulator:
    """Manages dynamic scheme rule versioning, diff analysis, and targeted citizen notifications."""

    def __init__(self, rag_service: Optional[RAGService] = None):
        self.rag = rag_service or RAGService()
        self.active_version = "1.0"
        self.rule_change_history: List[Dict[str, Any]] = []
        self.dispatched_nudges: List[Dict[str, Any]] = []

    def get_status(self) -> Dict[str, Any]:
        return {
            "active_version": self.active_version,
            "total_rule_changes": len(self.rule_change_history),
            "dispatched_nudges_count": len(self.dispatched_nudges),
            "history": self.rule_change_history[-5:],
        }

    def simulate_rule_amendment(
        self,
        new_version: str = "2026.2",
        amendment_description: str = "Strict Cutoff Date Enforcement: Disqualify land mutated after 01-Feb-2019",
    ) -> Dict[str, Any]:
        """Versions the PM-KISAN corpus, updates rules, identifies solely affected users,
        and dispatches targeted notifications."""
        previous_version = self.active_version
        self.active_version = new_version
        timestamp = datetime.now(timezone.utc).isoformat()

        # 1. Append Amendment Notice to the official corpus
        corpus_path = (
            Path(__file__).resolve().parent.parent.parent
            / "corpus"
            / "pmkisan"
            / "amendment_notices.md"
        )
        if corpus_path.exists():
            existing = corpus_path.read_text(encoding="utf-8")
            if "PMK-A-1.3" not in existing:
                corpus_path.write_text(existing + "\n" + AMENDMENT_CORPUS_TEXT, encoding="utf-8")
                # Re-index RAG with new clause
                self.rag.index_corpus()

        # 2. Evaluate each seeded demo user before and after
        affected_users: List[Dict[str, Any]] = []
        all_evaluations: List[Dict[str, Any]] = []

        for user in SEEDED_DEMO_USERS:
            uid = user["id"]
            name = user["name"]
            prof_dict = copy.deepcopy(user["profile"])

            # Baseline evaluation under standard rules
            base_eval = evaluate_profile(prof_dict)
            before_verdict = base_eval.get("verdict") if isinstance(base_eval, dict) else base_eval.verdict

            # Simulation: under Amendment 2026.2, if land was acquired post cutoff date (e.g. Anita Patel)
            # they are disqualified under PMK-A-1.3
            is_post_cutoff = user.get("mutation_date", "") > "2019-02-01" or prof_dict.get(
                "land_acquired_post_cutoff", False
            )

            if is_post_cutoff:
                # Add disqualification under 2026.2
                after_verdict = "NOT_ELIGIBLE"
                new_failed_rules = [
                    {
                        "rule_id": "RULE_LAND_CUTOFF_DATE_AMENDMENT",
                        "rule_version": new_version,
                        "clause_id": "PMK-A-1.3",
                        "reason": (
                            "Land parcel was mutated after 01-Feb-2019 scheme cutoff date without "
                            "succession certificate under Amendment Clause PMK-A-1.3."
                        ),
                    }
                ]
            else:
                after_verdict = before_verdict
                new_failed_rules = []

            # Check if user's eligibility verdict specifically CHANGED
            status_changed = before_verdict != after_verdict

            eval_entry = {
                "user_id": uid,
                "name": name,
                "before_verdict": before_verdict,
                "after_verdict": after_verdict,
                "status_changed": status_changed,
            }
            all_evaluations.append(eval_entry)

            # ONLY notify affected users whose verdict changed!
            if status_changed:
                nudge_message = (
                    f"⚠️ Urgent PM-KISAN Scheme Rule Amendment Notification:\n"
                    f"Dear {name}, new amendment Clause [PMK-A-1.3] (Version {new_version}) "
                    f"has been implemented regarding land transfer cutoff dates. "
                    f"Your registration status has shifted from {before_verdict} to {after_verdict}. "
                    f"Action Required: Submit a certified succession certificate at the Tehsil / SDM Office "
                    f"to retain your scheme benefits."
                )

                nudge_record = {
                    "id": f"nudge_{len(self.dispatched_nudges) + 1}",
                    "timestamp": timestamp,
                    "user_id": uid,
                    "user_name": name,
                    "phone": user["mobile"],
                    "telegram_chat_id": user["telegram_chat_id"],
                    "nudge_type": "RULE_CHANGED",
                    "clause_cited": "PMK-A-1.3",
                    "rule_version": new_version,
                    "message": nudge_message,
                    "sent": True,
                }

                self.dispatched_nudges.append(nudge_record)
                affected_users.append(
                    {
                        "user_id": uid,
                        "name": name,
                        "phone": user["mobile"],
                        "telegram_chat_id": user["telegram_chat_id"],
                        "before_verdict": before_verdict,
                        "after_verdict": after_verdict,
                        "disqualifying_rule": "PMK-A-1.3",
                        "nudge_sent": nudge_record,
                    }
                )

        history_record = {
            "timestamp": timestamp,
            "previous_version": previous_version,
            "new_version": new_version,
            "description": amendment_description,
            "total_users_checked": len(SEEDED_DEMO_USERS),
            "affected_users_count": len(affected_users),
            "affected_users": affected_users,
        }
        self.rule_change_history.append(history_record)

        return history_record

    def run_cron_nudge_dispatch(self) -> List[Dict[str, Any]]:
        """Simulates periodic cron job dispatching deadline and missing document nudges."""
        timestamp = datetime.now(timezone.utc).isoformat()
        dispatched_batch: List[Dict[str, Any]] = []

        for user in SEEDED_DEMO_USERS:
            uid = user["id"]
            name = user["name"]
            profile = user["profile"]

            # Nudge 1: Deadline in 3 days (e-KYC pending)
            if not profile.get("ekyc_completed", False):
                nudge = {
                    "id": f"nudge_{len(self.dispatched_nudges) + 1}",
                    "timestamp": timestamp,
                    "user_id": uid,
                    "user_name": name,
                    "phone": user["mobile"],
                    "telegram_chat_id": user["telegram_chat_id"],
                    "nudge_type": "DEADLINE_ALERT",
                    "clause_cited": "PMK-A-1.1",
                    "message": (
                        f"⏰ Deadline Reminder: Dear {name}, only 3 days remain to complete "
                        f"your mandatory Aadhaar e-KYC verification for the 16th installment. "
                        f"Visit your nearest CSC or pmkisan.gov.in."
                    ),
                    "sent": True,
                }
                self.dispatched_nudges.append(nudge)
                dispatched_batch.append(nudge)

            # Nudge 2: Document Missing (Land record seeding pending)
            if not profile.get("land_record_seeded", True):
                nudge = {
                    "id": f"nudge_{len(self.dispatched_nudges) + 1}",
                    "timestamp": timestamp,
                    "user_id": uid,
                    "user_name": name,
                    "phone": user["mobile"],
                    "telegram_chat_id": user["telegram_chat_id"],
                    "nudge_type": "DOCUMENT_MISSING",
                    "clause_cited": "PMK-A-1.2",
                    "message": (
                        f"📄 Document Missing: Dear {name}, your land record (Khasra: {user['khasra_no']}) "
                        f"has not been seeded in Bhulekh. Please submit your Khatauni copy to your Lekhpal."
                    ),
                    "sent": True,
                }
                self.dispatched_nudges.append(nudge)
                dispatched_batch.append(nudge)

        return dispatched_batch


# Singleton
_simulator: Optional[RuleChangeSimulator] = None


def get_rule_simulator() -> RuleChangeSimulator:
    global _simulator
    if _simulator is None:
        _simulator = RuleChangeSimulator()
    return _simulator
