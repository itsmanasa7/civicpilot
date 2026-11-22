from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class InterviewRequest(BaseModel):
    message: Optional[str] = Field(default="", description="The citizen's message or response")
    profile: Dict[str, Any] = Field(default_factory=dict, description="Accumulated profile fields")
    current_field: Optional[str] = Field(default=None, description="Field currently awaiting user input")
    lang: str = Field(default="en", description="User's language: 'en' or 'hi'")


class InterviewResponse(BaseModel):
    assistant_message: str = Field(..., description="Short conversational question or intake prompt")
    current_field: Optional[str] = Field(default=None, description="Field name being asked")
    extracted_profile: Dict[str, Any] = Field(default_factory=dict)
    missing_fields: List[str] = Field(default_factory=list)
    is_complete: bool = Field(default=False)
    verdict_result: Optional[Dict[str, Any]] = Field(default=None, description="Engine evaluate() result")
