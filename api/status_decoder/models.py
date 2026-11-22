from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DecodeStatusRequest(BaseModel):
    status_text: str = Field(..., description="Pasted portal status or rejection message")
    lang: str = Field(default="en", description="Language code: 'en' or 'hi'")


class DecodeStatusResponse(BaseModel):
    matched_cause_id: Optional[str] = Field(default=None, description="Known cause ID if matched")
    title: str = Field(..., description="Human-readable title of status")
    root_cause: str = Field(..., description="Explanation of why this happened")
    fix_action: List[str] = Field(default_factory=list, description="Step-by-step fix action items")
    clause_id: Optional[str] = Field(default=None, description="Official scheme clause ID")
    clause_text: Optional[str] = Field(default=None, description="Official clause text")
    designated_office: str = Field(..., description="Government office or portal to resolve this")
    is_known_cause: bool = Field(..., description="True if mapped to known causes YAML")
    needs_escalation: bool = Field(..., description="True if unknown or requires administrative intervention")
    confidence: float = Field(..., description="Confidence score")
    extracted_status_text: str = Field(..., description="The raw or extracted status text analyzed")
