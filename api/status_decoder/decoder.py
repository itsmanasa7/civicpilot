import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from rag.service import RAGService
from .models import DecodeStatusResponse


class StatusDecoder:
    """Decodes PM-KISAN portal status or rejection messages using known-causes YAML + RAG fallback."""

    def __init__(self, causes_path: Optional[str] = None, rag_service: Optional[RAGService] = None):
        if causes_path is None:
            causes_path = str(Path(__file__).resolve().parent.parent / "rules" / "status_causes.yaml")
        self.causes_path = causes_path
        self.rag = rag_service or RAGService()
        self.causes_config = self._load_causes()

    def _load_causes(self) -> Dict[str, Any]:
        with open(self.causes_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    @property
    def causes(self) -> List[Dict[str, Any]]:
        return self.causes_config.get("causes", [])

    def decode(self, status_text: str, lang: str = "en") -> DecodeStatusResponse:
        """Matches status against known causes YAML, or falls back to RAG with needs_escalation."""
        text_clean = status_text.strip()
        lower_text = text_clean.lower()

        # Helper to normalize spacing and hyphenated variations like e-kyc vs ekyc
        def norm(s: str) -> str:
            cleaned = s.lower().replace("e-kyc", "ekyc").replace("e_kyc", "ekyc").replace("e kyc", "ekyc")
            return re.sub(r"\s+", " ", cleaned).strip()

        norm_lower_text = norm(lower_text)

        # 1. Match against known causes table
        for cause in self.causes:
            patterns = cause.get("patterns", [])
            for pattern in patterns:
                pat_lower = pattern.lower()
                norm_pat = norm(pat_lower)
                # Check substring or word boundary match on raw and normalized text
                if (
                    pat_lower in lower_text
                    or norm_pat in norm_lower_text
                    or re.search(r"\b" + re.escape(pat_lower) + r"\b", lower_text)
                    or re.search(r"\b" + re.escape(norm_pat) + r"\b", norm_lower_text)
                ):
                    clause_id = cause.get("clause_id")
                    clause_chunk = self.rag.db.get_chunk(clause_id) if clause_id else None
                    clause_text = clause_chunk.text if clause_chunk else None

                    # If Hindi, provide translated title / summary
                    title = cause["title"]
                    root_cause = cause["root_cause"]
                    fix_action = list(cause.get("fix_action", []))

                    if lang == "hi":
                        if "ekyc" in cause["id"].lower():
                            title = "ई-केवाईसी (e-KYC) सत्यापन लंबित"
                            root_cause = "लाभार्थी ने पीएम-किसान पोर्टल या सीएससी पर बायोमेट्रिक या ओटीपी ई-केवाईसी पूरा नहीं किया है।"
                            fix_action = [
                                "पीएम-किसान पोर्टल (pmkisan.gov.in) पर 'e-KYC' विकल्प पर जाएं।",
                                "आधार नंबर दर्ज कर ओटीपी से सत्यापन करें अथवा सीएससी पर बायोमेट्रिक अंगूठा लगाएं।",
                            ]
                        elif "land" in cause["id"].lower():
                            title = "भूलेख / भूमि सीडिंग लंबित (Land Seeding Pending)"
                            root_cause = "राज्य राजस्व पोर्टल (भूलेख) पर आपकी कृषि भूमि का सत्यापन अभी तक 'Yes' नहीं हुआ है।"
                            fix_action = [
                                "अपनी खतौनी / खसरा नकल लेकर स्थानीय लेखपाल / पटवारी से संपर्क करें।",
                                "तहसील स्तर पर लैंड सीडिंग स्थिति को 'Yes' अपडेट करवाएं।",
                            ]
                        elif "aadhaar" in cause["id"].lower():
                            title = "आधार बैंक खाता लिंक नहीं (NPCI मैपिंग लंबित)"
                            root_cause = "आपका आधार नंबर बैंक खाते के साथ एनपीसीआई (NPCI) मैपर पर डीबीटी हेतु सक्रिय रूप से मैप नहीं है।"
                            fix_action = [
                                "अपनी बैंक शाखा जाकर 'Aadhaar NPCI Seeding' फॉर्म जमा करें।",
                                "या नजदीकी डाकघर (IPPB) में नया डीबीटी सक्षम खाता खुलवाएं।",
                            ]

                    return DecodeStatusResponse(
                        matched_cause_id=cause["id"],
                        title=title,
                        root_cause=root_cause,
                        fix_action=fix_action,
                        clause_id=clause_id,
                        clause_text=clause_text,
                        designated_office=cause.get("designated_office", "District Agriculture Office"),
                        is_known_cause=True,
                        needs_escalation=not cause.get("is_recoverable", True),
                        confidence=0.96,
                        extracted_status_text=text_clean,
                    )

        # 2. Unknown status -> Fall back to RAG with needs_escalation=True
        rag_res = self.rag.ask(f"Portal status rejection: {text_clean}", lang=lang)
        clause_id = rag_res.citations[0].id if rag_res.citations else None
        clause_text = rag_res.citations[0].text if rag_res.citations else None

        if lang == "hi":
            title = "अज्ञात अस्वीकृति कोड / पोर्टल स्थिति"
            root_cause = f"यह पोर्टल स्थिति संदेश सामान्य ज्ञात कारणों में सीधे नहीं मिला। {rag_res.answer}"
            fix_action = [
                "अपनी पंजीकरण संख्या के साथ जिला कृषि अधिकारी / नोडल अधिकारी से संपर्क करें।",
                "पीएम-किसान पोर्टल पर 'Helpdesk' में ऑनलाइन शिकायत दर्ज करें।",
            ]
            office = "जिला कृषि कार्यालय / तहसील नोडल अधिकारी"
        else:
            title = "Unknown Status or Unresolved Rejection Message"
            root_cause = (
                f"This rejection message or code does not match standard automated causes. "
                f"RAG Scheme Analysis: {rag_res.answer}"
            )
            fix_action = [
                "Visit the District Agriculture Officer with your PM-KISAN registration number and application slip.",
                "Register an official administrative grievance on pmkisan.gov.in under the Helpdesk module.",
                "Ensure your identity and land documents are submitted for physical verification.",
            ]
            office = "District Agriculture Office / Block Nodal Officer"

        return DecodeStatusResponse(
            matched_cause_id=None,
            title=title,
            root_cause=root_cause,
            fix_action=fix_action,
            clause_id=clause_id,
            clause_text=clause_text,
            designated_office=office,
            is_known_cause=False,
            needs_escalation=True,
            confidence=0.45,
            extracted_status_text=text_clean,
        )


# Singleton
_status_decoder: Optional[StatusDecoder] = None


def get_status_decoder() -> StatusDecoder:
    global _status_decoder
    if _status_decoder is None:
        _status_decoder = StatusDecoder()
    return _status_decoder

