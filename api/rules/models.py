from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RuleEvaluationResult(BaseModel):
    rule_id: str
    name: str
    clause_id: str
    rule_version: str
    reason: Optional[str] = None
    citation: Optional[str] = None


class RuleCitation(BaseModel):
    id: str
    text: str


class EligibilityResponse(BaseModel):
    verdict: str = Field(..., description="ELIGIBLE, INELIGIBLE, or INCOMPLETE")
    failed_rules: List[Dict[str, Any]] = Field(default_factory=list)
    passed_rules: List[Dict[str, Any]] = Field(default_factory=list)
    missing_inputs: List[str] = Field(default_factory=list)
    citations: List[RuleCitation] = Field(default_factory=list)


class EligibilityRequest(BaseModel):
    profile: Dict[str, Any]


class WhatIfRequest(BaseModel):
    profile: Dict[str, Any]
    changes: Dict[str, Any]


class WhatIfResponse(BaseModel):
    original_verdict: str
    new_verdict: str
    verdict_changed: bool
    changes_applied: Dict[str, Any]
    fixed_rules: List[str] = Field(default_factory=list)
    newly_failed_rules: List[str] = Field(default_factory=list)
    original_result: EligibilityResponse
    updated_result: EligibilityResponse
