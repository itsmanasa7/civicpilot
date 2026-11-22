"""CivicPilot PM-KISAN Rules Engine.
Purely deterministic rule evaluation from YAML specifications without LLM dependencies.
"""

from .engine import EligibilityEngine, evaluate_profile, whatif_analysis, get_engine
from .models import (
    EligibilityRequest,
    EligibilityResponse,
    RuleCitation,
    RuleEvaluationResult,
    WhatIfRequest,
    WhatIfResponse,
)

__all__ = [
    "EligibilityEngine",
    "evaluate_profile",
    "whatif_analysis",
    "get_engine",
    "EligibilityRequest",
    "EligibilityResponse",
    "RuleCitation",
    "RuleEvaluationResult",
    "WhatIfRequest",
    "WhatIfResponse",
]
