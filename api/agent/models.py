from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RegistrationProfile(BaseModel):
    """Farmer profile data mapped to the PM-KISAN registration portal."""
    farmer_name: str = Field(..., description="Full Name as on Aadhaar")
    gender: str = Field(default="Male", description="Male, Female, or Other")
    category: str = Field(default="General", description="General, SC, ST, or OBC")
    farmer_type: str = Field(default="Small (1-2 Ha)", description="Small (1-2 Ha), Marginal (<1 Ha), or Other")
    aadhaar_number: str = Field(..., description="12-digit Aadhaar Number")
    mobile_number: str = Field(..., description="10-digit Mobile Number linked to Aadhaar")
    state: str = Field(default="Uttar Pradesh", description="State")
    district: str = Field(..., description="District")
    sub_district: str = Field(..., description="Tehsil or Sub-District")
    village: str = Field(..., description="Village")
    khasra_number: str = Field(..., description="Khasra / Plot Number")
    land_area_ha: float = Field(..., description="Cultivable Land Area in Hectares")
    ifsc_code: str = Field(..., description="Bank IFSC Code")
    bank_name: str = Field(..., description="Bank Name")
    account_number: str = Field(..., description="Bank Account Number")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RegistrationProfile":
        """Helper to accept alternative field naming conventions."""
        return cls(
            farmer_name=data.get("farmer_name") or data.get("name") or data.get("farmerName", ""),
            gender=data.get("gender") or "Male",
            category=data.get("category") or "General",
            farmer_type=data.get("farmer_type") or data.get("farmerType") or "Small (1-2 Ha)",
            aadhaar_number=str(data.get("aadhaar_number") or data.get("aadhaar_no") or data.get("aadhaarNo") or ""),
            mobile_number=str(data.get("mobile_number") or data.get("mobile_no") or data.get("mobileNo") or ""),
            state=data.get("state") or "Uttar Pradesh",
            district=data.get("district") or "",
            sub_district=data.get("sub_district") or data.get("subDistrict") or data.get("tehsil") or "",
            village=data.get("village") or "",
            khasra_number=str(data.get("khasra_number") or data.get("khasra_no") or data.get("khasraNo") or ""),
            land_area_ha=float(data.get("land_area_ha") or data.get("land_area") or data.get("landArea") or 1.0),
            ifsc_code=data.get("ifsc_code") or data.get("ifscCode") or "",
            bank_name=data.get("bank_name") or data.get("bankName") or "",
            account_number=str(data.get("account_number") or data.get("account_no") or data.get("accountNo") or ""),
        )


class FieldDiff(BaseModel):
    field_id: str = Field(..., description="DOM Element ID in portal")
    label: str = Field(..., description="Human readable label")
    before_value: str = Field(..., description="Value prior to automation")
    after_value: str = Field(..., description="Value populated from verified profile")
    is_modified: bool = Field(default=True, description="True if value was inserted or updated")


class StartFillRequest(BaseModel):
    profile: Dict[str, Any] = Field(..., description="Verified citizen profile fields")
    portal_url: Optional[str] = Field(default="http://localhost:8000/mirror", description="Mirror portal URL")


class StartFillResponse(BaseModel):
    session_id: str
    status: str = Field(..., description="Current agent workflow state")
    before_screenshot: str = Field(..., description="Base64 PNG screenshot before fill")
    after_screenshot: str = Field(..., description="Base64 PNG screenshot after fill")
    diffs: List[FieldDiff] = Field(default_factory=list, description="Field comparison list")
    message: str


class ApproveDiffRequest(BaseModel):
    session_id: str = Field(..., description="Active registration session ID")


class ApproveDiffResponse(BaseModel):
    session_id: str
    status: str = Field(..., description="Current agent workflow state (PAUSED_FOR_OTP)")
    otp_screenshot: str = Field(..., description="Base64 PNG screenshot showing paused OTP step")
    message: str


class SubmitConsentRequest(BaseModel):
    session_id: str = Field(..., description="Active registration session ID")
    otp: str = Field(..., description="6-digit fake Aadhaar OTP")
    explicit_consent: bool = Field(..., description="Mandatory citizen explicit consent")


class SubmitConsentResponse(BaseModel):
    session_id: str
    status: str = Field(..., description="Final workflow state (SUBMITTED)")
    registration_number: str = Field(..., description="Generated registration reference ID")
    submitted_screenshot: str = Field(..., description="Base64 PNG screenshot of acknowledgement")
    audit_log_path: str = Field(..., description="Local filepath to JSON audit log")
    audit_log: Dict[str, Any] = Field(..., description="Full audit log record")
    message: str
