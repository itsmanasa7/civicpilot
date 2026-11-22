import io
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import pypdf

from main import app, rag_service


@pytest.fixture(scope="session", autouse=True)
def setup_rag():
    corpus_dir = Path(__file__).resolve().parent.parent.parent / "corpus" / "pmkisan"
    rag_service.index_corpus(str(corpus_dir))
    return rag_service


@pytest.fixture
def client():
    return TestClient(app)


def test_explain_notice_ekyc(client):
    """Tests POST /explain-notice with an e-KYC pending notice."""
    notice_content = b"Department of Agriculture: Notice to PM-KISAN beneficiary. Your 12th installment is withheld due to pending Aadhaar e-KYC verification. Complete biometric authentication."

    response = client.post(
        "/explain-notice",
        files={"file": ("notice.jpg", notice_content, "image/jpeg")},
        data={"lang": "en"},
    )
    assert response.status_code == 200
    data = response.json()

    assert "extracted_text" in data
    assert "explanation" in data
    assert "what_you_should_do_next" in data
    assert len(data["what_you_should_do_next"]) >= 2
    assert data["is_low_confidence"] is False
    assert data["confidence"] >= 0.70

    # Must cite e-KYC clause
    cited_ids = [c["id"] for c in data["citations"]]
    assert "PMK-A-1.1" in cited_ids or any("A-1.1" in cid for cid in cited_ids)


def test_explain_notice_hindi(client):
    """Tests POST /explain-notice with Hindi translation."""
    notice_content = b"PM-KISAN notice: Aadhaar e-KYC biometric verification mandatory."

    response = client.post(
        "/explain-notice",
        files={"file": ("notice.png", notice_content, "image/png")},
        data={"lang": "hi"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["is_low_confidence"] is False
    # Verify Hindi characters in explanation or next steps
    assert any(ord(char) >= 0x0900 and ord(char) <= 0x097F for char in data["explanation"])
    assert len(data["what_you_should_do_next"]) >= 2


def test_explain_notice_low_confidence_retake_prompt(client):
    """Tests that low-confidence / blurry photo returns is_low_confidence=True and retake prompt."""
    blurry_content = b"unclear dark blurry doc"

    response = client.post(
        "/explain-notice",
        files={"file": ("blurry_photo.jpg", blurry_content, "image/jpeg")},
        data={"lang": "en"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["is_low_confidence"] is True
    assert data["confidence"] < 0.65
    assert len(data["citations"]) == 0
    # Next steps should guide the user on how to retake the photo
    assert any("retake" in step.lower() or "photo" in step.lower() or "surface" in step.lower() for step in data["what_you_should_do_next"])


def test_explain_notice_pdf(client):
    """Tests POST /explain-notice with a synthetic PDF document."""
    pdf_writer = pypdf.PdfWriter()
    pdf_writer.add_blank_page(width=200, height=200)
    # Add text
    pdf_buffer = io.BytesIO()
    # Write plain bytes or sample PDF
    notice_bytes = b"%PDF-1.4\nLand record seeding pending for PM-KISAN beneficiary under Bhulekh RoR verification\n%%EOF"

    response = client.post(
        "/explain-notice",
        files={"file": ("official_notice.pdf", notice_bytes, "application/pdf")},
        data={"lang": "en"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "explanation" in data
    assert len(data["what_you_should_do_next"]) > 0
