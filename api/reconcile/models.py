from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DiscrepancyItem(BaseModel):
    field: str = Field(..., description="Field name (e.g. name, dob, khasra_number)")
    field_label: str = Field(..., description="Human-readable label")
    values_per_document: Dict[str, str] = Field(..., description="Document source -> Extracted value")
    severity: str = Field(..., description="MATCHED, MINOR, MODERATE, or CRITICAL")
    similarity_score: float = Field(..., description="Fuzzy match similarity score (0.0 to 1.0)")
    description: str = Field(..., description="Explanation of difference or pattern detected")
    fix_at_office: str = Field(..., description="Specific designated government office to resolve this discrepancy")
    canonical_value: Optional[str] = Field(default=None, description="Recommended standard value")


class ExtractedDocument(BaseModel):
    document_type: str
    document_id: Optional[str] = None
    fields: Dict[str, Any]


class ReconcileResponse(BaseModel):
    documents_analyzed: List[str]
    extracted_fields_by_doc: Dict[str, Dict[str, Any]]
    discrepancies: List[DiscrepancyItem]
    overall_status: str = Field(..., description="MATCHED or DISCREPANCIES_FOUND")
    total_discrepancies: int
    critical_count: int
    moderate_count: int
    minor_count: int


class ManualCorrectionRequest(BaseModel):
    extracted_fields_by_doc: Dict[str, Dict[str, Any]]
    corrections: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
