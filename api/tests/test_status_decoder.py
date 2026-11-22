import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from main import app, rag_service
from status_decoder import get_status_decoder


@pytest.fixture(scope="session", autouse=True)
def setup_rag():
    corpus_dir = Path(__file__).resolve().parent.parent.parent / "corpus" / "pmkisan"
    rag_service.index_corpus(str(corpus_dir))
    return rag_service


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def decoder():
    return get_status_decoder()


def test_decode_ekyc_pending(decoder):
    """Test matching e-KYC pending status message."""
    res = decoder.decode("Beneficiary Status: e-KYC Pending. Please complete eKYC to receive installments.", lang="en")
    assert res.is_known_cause is True
    assert res.matched_cause_id == "CAUSE_EKYC_PENDING"
    assert res.needs_escalation is False
    assert res.clause_id == "PMK-A-1.1"
    assert "e-KYC" in res.title
    assert len(res.fix_action) >= 2
    assert "CSC" in res.designated_office or "Online" in res.designated_office or "Portal" in res.designated_office


def test_decode_land_seeding_no(decoder):
    """Test matching Land Seeding No status message."""
    res = decoder.decode("Land Seeding: No. Eligibility status withheld pending verification.", lang="en")
    assert res.is_known_cause is True
    assert res.matched_cause_id == "CAUSE_LAND_SEEDING_PENDING"
    assert "PMK-A-1.2" in (res.clause_id or "")
    assert "Patwari" in res.designated_office or "Revenue" in res.designated_office or "Tehsil" in res.designated_office
    assert len(res.fix_action) >= 2


def test_decode_aadhaar_bank_mismatch(decoder):
    """Test matching Aadhaar-Bank NPCI mapping failure."""
    res = decoder.decode("Payment Failed: Aadhaar not seeded with account / NPCI mapping pending.", lang="en")
    assert res.is_known_cause is True
    assert res.matched_cause_id == "CAUSE_AADHAAR_BANK_MISMATCH"
    assert res.clause_id == "PMK-G-6.0"
    assert "Bank" in res.designated_office or "Post Office" in res.designated_office or "IPPB" in res.designated_office


def test_decode_pfms_account_rejected(decoder):
    """Test matching PFMS bank rejection."""
    res = decoder.decode("PFMS Status: Account rejected by bank due to invalid account number or IFSC.", lang="en")
    assert res.is_known_cause is True
    assert res.matched_cause_id == "CAUSE_PFMS_ACCOUNT_REJECTED"
    assert res.clause_id == "PMK-G-6.0"


def test_decode_exclusion_income_tax(decoder):
    """Test matching Income Tax exclusion status."""
    res = decoder.decode("Ineligible: Income tax payee in previous assessment year.", lang="en")
    assert res.is_known_cause is True
    assert res.matched_cause_id == "CAUSE_INCOME_TAX_EXCLUSION"
    assert res.clause_id == "PMK-A-2.0"
    assert res.needs_escalation is True  # Non-recoverable exclusion requires escalation


def test_decode_unknown_status_rag_fallback(decoder):
    """Test unknown or cryptic status code falls back to RAG with needs_escalation=True."""
    res = decoder.decode("CRITICAL_ERR_CODE_98812_STATE_PAYMENT_NODE_GLITCH", lang="en")
    assert res.is_known_cause is False
    assert res.matched_cause_id is None
    assert res.needs_escalation is True
    assert res.confidence < 0.60
    assert len(res.fix_action) > 0


def test_decode_hindi_translation(decoder):
    """Test status decoding in Hindi."""
    res = decoder.decode("eKYC is not complete. Status rejected.", lang="hi")
    assert res.is_known_cause is True
    assert "ई-केवाईसी" in res.title
    assert "सत्यापन" in res.title or "लंबित" in res.title
    assert len(res.fix_action) >= 2


def test_api_decode_status_json(client):
    """Test POST /decode-status with JSON payload."""
    resp = client.post(
        "/decode-status",
        json={"status_text": "Land Seeding: No. Record not verified.", "lang": "en"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_known_cause"] is True
    assert data["matched_cause_id"] == "CAUSE_LAND_SEEDING_PENDING"
    assert data["designated_office"] is not None
    assert data["clause_id"] is not None


def test_api_decode_status_multipart(client):
    """Test POST /decode-status with form upload."""
    resp = client.post(
        "/decode-status",
        data={"status_text": "Aadhaar e-KYC pending for installment 14", "lang": "en"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_known_cause"] is True
    assert data["matched_cause_id"] == "CAUSE_EKYC_PENDING"
