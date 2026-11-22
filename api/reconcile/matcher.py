import json
import re
from typing import Any, Dict, List, Optional, Tuple
import rapidfuzz.fuzz as fuzz

from rag.gemini import GeminiClient
from .models import DiscrepancyItem, ReconcileResponse


EXTRACTION_PROMPT = """You are a Document Field Extractor for Indian citizen documents (Aadhaar, Land Record/Khasra, Bank Passbook, Self-Declaration).
Extract these fields if present in the document:
- document_type (e.g. "Aadhaar Card", "Land Record", "Bank Passbook", "Self-Declaration")
- name (full person name)
- father_or_spouse_name
- dob (YYYY-MM-DD format if date of birth exists)
- khasra_number (land parcel / gata number, e.g. "142/3")
- account_number (bank account number digits)
- address (full address string)
- district
- state

Output strictly JSON with these keys."""


KNOWN_EQUIVALENCES = [
    ({"prayagraj", "allahabad"}, "Historical official district renaming (Allahabad -> Prayagraj)"),
]

OFFICE_GUIDANCE = {
    "name": "Tehsil / Lekhpal (Patwari) Office & State Bhulekh Portal to synchronize land records with Aadhaar",
    "father_or_spouse_name": "Tehsil / Revenue Office or Aadhaar Enrollment Kendra (UIDAI)",
    "dob": "Aadhaar Seva Kendra (UIDAI) or Municipal Birth Registrar",
    "khasra_number": "Tehsil / Revenue Inspector (Lekhpal) with Registered Land Mutation Deed",
    "account_number": "Bank Home Branch / Post Office (IPPB) with Passbook and Aadhaar copy",
    "address": "Gram Panchayat Secretary / Village Nodal Officer or Aadhaar Kendra",
}

FIELD_LABELS = {
    "name": "Applicant Name",
    "father_or_spouse_name": "Father / Spouse Name",
    "dob": "Date of Birth (DOB)",
    "khasra_number": "Khasra / Plot Number",
    "account_number": "Bank Account Number",
    "address": "Address / Village Details",
}


def normalize_name(text: str) -> str:
    """Removes honorifics and non-alphanumeric noise for transliteration-aware comparisons."""
    cleaned = re.sub(r"\b(shri|smt|mr|mrs|ms|late|kumar|kmr|chandra|chander)\b", "", text.lower())
    cleaned = re.sub(r"[^a-z0-9]", "", cleaned)
    return cleaned


def normalize_address(addr: str) -> str:
    """Normalizes known city variations (e.g. Allahabad -> Prayagraj)."""
    cleaned = addr.lower()
    cleaned = cleaned.replace("allahabad", "prayagraj")
    return re.sub(r"[,\-\.\s]+", " ", cleaned).strip()


class DocumentReconciler:
    """Reconciles extracted citizen records across multiple documents using RapidFuzz."""

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.gemini = gemini_client or GeminiClient()

    def parse_document_text_or_json(self, raw_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Parses JSON or extracts fields from document bytes."""
        text = raw_bytes.decode("utf-8", errors="ignore").strip()

        # If already valid JSON
        if text.startswith("{") and text.endswith("}"):
            try:
                return json.loads(text)
            except Exception:
                pass

        # Text-based keyword extraction for text files / mock docs
        fields: Dict[str, Any] = {}
        for line in text.splitlines():
            line_str = line.strip()
            if not line_str:
                continue

            lower = line_str.lower()
            if "aadhaar card" in lower:
                fields["document_type"] = "Aadhaar Card"
            elif "khasra" in lower or "land record" in lower or "khatauni" in lower:
                fields["document_type"] = "Land Record (Khasra/Khatauni)"
            elif "passbook" in lower or "bank" in lower:
                fields["document_type"] = "Bank Passbook"
            elif "declaration" in lower:
                fields["document_type"] = "Self-Declaration Form"

            if "name" in lower and "father" not in lower:
                val = re.sub(r"^.*?name\s*(?:\/|\:|\-)?\s*", "", line_str, flags=re.I).split("/")[0].strip()
                if val:
                    fields["name"] = val

            if "father" in lower or "s/o" in lower:
                val = re.sub(r"^.*?(?:father['\w\s]*|s\/o)\s*(?:\/|\:|\-)?\s*", "", line_str, flags=re.I).strip()
                if val:
                    fields["father_or_spouse_name"] = val

            if "birth" in lower or "dob" in lower:
                match = re.search(r"(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})", line_str)
                if match:
                    parts = match.group(1).replace("/", "-").split("-")
                    if len(parts[0]) == 4:
                        fields["dob"] = f"{parts[0]}-{parts[1]}-{parts[2]}"
                    else:
                        fields["dob"] = f"{parts[2]}-{parts[1]}-{parts[0]}"

            if "khasra" in lower or "plot" in lower:
                match = re.search(r"(\d+/\d+|\d+)", line_str)
                if match and "/" in match.group(1):
                    fields["khasra_number"] = match.group(1)

            if "a/c no" in lower or "account" in lower:
                match = re.search(r"(\d{9,16})", line_str)
                if match:
                    fields["account_number"] = match.group(1)

            if "address" in lower or "village" in lower:
                val = re.sub(r"^.*?address\s*(?:\/|\:|\-)?\s*", "", line_str, flags=re.I).strip()
                if val and len(val) > 10:
                    fields["address"] = val

        return fields

    def compare_field(self, field: str, doc_values: Dict[str, str]) -> DiscrepancyItem:
        """Compares values of a specific field across documents."""
        unique_vals = list(set(v.strip() for v in doc_values.values() if v.strip()))
        label = FIELD_LABELS.get(field, field.replace("_", " ").title())
        fix_office = OFFICE_GUIDANCE.get(field, "District Agriculture Office")

        # If all documents agree or only 1 value present
        if len(unique_vals) <= 1:
            val = unique_vals[0] if unique_vals else ""
            return DiscrepancyItem(
                field=field,
                field_label=label,
                values_per_document=doc_values,
                severity="MATCHED",
                similarity_score=1.0,
                description="Consistent across all provided documents.",
                fix_at_office=fix_office,
                canonical_value=val,
            )

        # 1. Date of Birth comparison
        if field == "dob":
            # Compare years
            years = set()
            for v in unique_vals:
                m = re.search(r"(\d{4})", v)
                if m:
                    years.add(m.group(1))

            score = 0.5 if len(years) > 1 else 0.8
            desc = (
                f"Date of birth mismatch: different birth years recorded ({', '.join(sorted(years))})."
                if len(years) > 1
                else "Date format or day variation detected."
            )
            return DiscrepancyItem(
                field=field,
                field_label=label,
                values_per_document=doc_values,
                severity="CRITICAL",
                similarity_score=score,
                description=desc,
                fix_at_office=fix_office,
                canonical_value=doc_values.get("aadhaar", unique_vals[0]),
            )

        # 2. Khasra / Plot Number comparison
        if field == "khasra_number":
            return DiscrepancyItem(
                field=field,
                field_label=label,
                values_per_document=doc_values,
                severity="CRITICAL",
                similarity_score=0.4,
                description=f"Plot/Khasra number mismatch ({', '.join(unique_vals)}). Land record will be rejected during Bhulekh verification.",
                fix_at_office=fix_office,
                canonical_value=doc_values.get("land_record", unique_vals[0]),
            )

        # 3. Bank Account Number comparison
        if field == "account_number":
            digits_list = [re.sub(r"\D", "", v) for v in unique_vals]
            if len(set(digits_list)) > 1:
                return DiscrepancyItem(
                    field=field,
                    field_label=label,
                    values_per_document=doc_values,
                    severity="CRITICAL",
                    similarity_score=0.2,
                    description=f"Bank account number digits differ between documents ({', '.join(unique_vals)}).",
                    fix_at_office=fix_office,
                    canonical_value=doc_values.get("bank_passbook", unique_vals[0]),
                )

        # 4. Name comparison with transliteration awareness
        if field in ("name", "father_or_spouse_name"):
            v1, v2 = unique_vals[0], unique_vals[1]
            token_sort = fuzz.token_sort_ratio(v1, v2) / 100.0
            norm1 = normalize_name(v1)
            norm2 = normalize_name(v2)
            norm_ratio = fuzz.ratio(norm1, norm2) / 100.0
            best_score = round(max(token_sort, norm_ratio), 2)

            # Check if spacing variation e.g. "Ramesh Kumar" vs "Rameshkumar"
            v1_nospace = v1.replace(" ", "").lower()
            v2_nospace = v2.replace(" ", "").lower()

            if v1_nospace == v2_nospace:
                severity = "MINOR"
                desc = "Minor spacing variation (merged name tokens)."
            elif norm_ratio >= 0.90 or token_sort >= 0.85:
                severity = "MODERATE"
                desc = "Middle name or initial variation (e.g. 'Kumar' omitted or abbreviated)."
            else:
                severity = "CRITICAL"
                desc = "Substantial spelling or identity discrepancy."

            return DiscrepancyItem(
                field=field,
                field_label=label,
                values_per_document=doc_values,
                severity=severity,
                similarity_score=best_score,
                description=desc,
                fix_at_office=fix_office,
                canonical_value=doc_values.get("aadhaar", unique_vals[0]),
            )

        # 5. Address comparison
        if field == "address":
            norm_addrs = [normalize_address(v) for v in unique_vals]
            addr_score = round(fuzz.token_set_ratio(norm_addrs[0], norm_addrs[1]) / 100.0, 2)
            has_rename = any("prayagraj" in v.lower() and "allahabad" in " ".join(unique_vals).lower() for v in unique_vals)

            if has_rename:
                severity = "MODERATE"
                desc = "District name terminology difference (Prayagraj vs Allahabad)."
            elif addr_score >= 0.80:
                severity = "MINOR"
                desc = "Minor village/pargana formatting variation."
            else:
                severity = "MODERATE"
                desc = "Address wording variation between records."

            return DiscrepancyItem(
                field=field,
                field_label=label,
                values_per_document=doc_values,
                severity=severity,
                similarity_score=addr_score,
                description=desc,
                fix_at_office=fix_office,
                canonical_value=doc_values.get("aadhaar", unique_vals[0]),
            )

        # Generic fallback
        score = round(fuzz.token_sort_ratio(unique_vals[0], unique_vals[1]) / 100.0, 2)
        return DiscrepancyItem(
            field=field,
            field_label=label,
            values_per_document=doc_values,
            severity="MODERATE" if score >= 0.70 else "CRITICAL",
            similarity_score=score,
            description=f"Discrepancy found across documents ({', '.join(unique_vals)}).",
            fix_at_office=fix_office,
            canonical_value=unique_vals[0],
        )

    def reconcile(
        self,
        docs: Dict[str, Dict[str, Any]],
        corrections: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> ReconcileResponse:
        """Reconciles extracted documents, applying any user manual corrections."""
        active_docs = dict(docs)

        # Apply user corrections if provided
        if corrections:
            for doc_key, corr_fields in corrections.items():
                if doc_key in active_docs:
                    active_docs[doc_key] = {**active_docs[doc_key], **corr_fields}

        # Collect all fields across documents
        target_fields = ["name", "father_or_spouse_name", "dob", "khasra_number", "account_number", "address"]
        discrepancies: List[DiscrepancyItem] = []

        critical_count = 0
        moderate_count = 0
        minor_count = 0

        for field in target_fields:
            doc_values: Dict[str, str] = {}
            for doc_key, fields in active_docs.items():
                if field in fields and fields[field] is not None and str(fields[field]).strip():
                    doc_values[doc_key] = str(fields[field]).strip()

            if len(doc_values) >= 1:
                item = self.compare_field(field, doc_values)
                discrepancies.append(item)

                if item.severity == "CRITICAL":
                    critical_count += 1
                elif item.severity == "MODERATE":
                    moderate_count += 1
                elif item.severity == "MINOR":
                    minor_count += 1

        total_issues = critical_count + moderate_count + minor_count
        overall_status = "DISCREPANCIES_FOUND" if total_issues > 0 else "MATCHED"

        return ReconcileResponse(
            documents_analyzed=list(active_docs.keys()),
            extracted_fields_by_doc=active_docs,
            discrepancies=discrepancies,
            overall_status=overall_status,
            total_discrepancies=total_issues,
            critical_count=critical_count,
            moderate_count=moderate_count,
            minor_count=minor_count,
        )


# Singleton
_reconciler: Optional[DocumentReconciler] = None


def get_reconciler() -> DocumentReconciler:
    global _reconciler
    if _reconciler is None:
        _reconciler = DocumentReconciler()
    return _reconciler
