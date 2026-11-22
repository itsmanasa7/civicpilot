import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from main import app, rag_service
from rag.chunker import Chunker
from rag.db import RAGDatabase
from rag.service import RAGService


@pytest.fixture(scope="session", autouse=True)
def setup_rag():
    """Ensure RAG corpus is indexed before tests run."""
    corpus_dir = Path(__file__).resolve().parent.parent.parent / "corpus" / "pmkisan"
    rag_service.index_corpus(str(corpus_dir))
    return rag_service


@pytest.fixture
def client():
    return TestClient(app)


def test_chunker_stable_ids():
    """Tests chunking of markdown documents and assignment of stable IDs like PMK-G-4.2."""
    corpus_dir = Path(__file__).resolve().parent.parent.parent / "corpus" / "pmkisan"
    chunks = Chunker.chunk_directory(corpus_dir)
    assert len(chunks) > 0

    chunk_ids = {c.id for c in chunks}
    # Check specific stable IDs
    assert "PMK-G-4.2" in chunk_ids, f"PMK-G-4.2 should be present. Found: {chunk_ids}"
    assert "PMK-G-1.0" in chunk_ids
    assert "PMK-G-3.0" in chunk_ids
    assert "PMK-FAQ-3" in chunk_ids
    assert "PMK-A-1.1" in chunk_ids
    assert "PMK-A-2.0" in chunk_ids

    # Verify chunk structure
    chunk_4_2 = next(c for c in chunks if c.id == "PMK-G-4.2")
    assert "cultivable" in chunk_4_2.text.lower()
    assert chunk_4_2.clause_num == "4.2"


def test_fts5_search(setup_rag):
    """Tests SQLite FTS5 full-text indexing and retrieval."""
    db = setup_rag.db
    results = db.search_fts("cultivable landholding clause 4.2", limit=3)
    assert len(results) > 0
    top_chunk, score = results[0]
    assert top_chunk.id == "PMK-G-4.2"
    assert score > 0.0


# 10 Questions Test Suite
# 7 Covered Questions (Must answer and cite clause IDs)
# 3 Out-of-Scope Questions (Must escalate)
QUESTIONS_10_SUITE = [
    # 1. Covered: Clause 4.2 eligibility
    {
        "question": "Who is eligible for PM-KISAN benefits under clause 4.2?",
        "expected_escalate": False,
        "expected_citation": "PMK-G-4.2",
        "description": "Eligibility criteria for landholding farmers",
    },
    # 2. Covered: Benefit amount & installments
    {
        "question": "What is the financial benefit amount and installment schedule under clause 3.0?",
        "expected_escalate": False,
        "expected_citation": "PMK-G-3.0",
        "description": "Rs. 6000 per year in 3 installments",
    },
    # 3. Covered: Exclusion criteria (pensioners & institutions)
    {
        "question": "Are institutional landholders and government pensioners excluded under clause 5.1?",
        "expected_escalate": False,
        "expected_citation": "PMK-G-5.1",
        "description": "Clause 5.1 institutional and pensioner exclusions",
    },
    # 4. Covered: Mandatory Aadhaar & e-KYC
    {
        "question": "Is biometric or OTP e-KYC mandatory for installments under amendment 1.1?",
        "expected_escalate": False,
        "expected_citation": "PMK-A-1.1",
        "description": "Mandatory Aadhaar and e-KYC amendment",
    },
    # 5. Covered: Income tax exclusion
    {
        "question": "Are income tax payers excluded from benefits according to amendment 2.0?",
        "expected_escalate": False,
        "expected_citation": "PMK-A-2.0",
        "description": "Exclusion of income tax payers",
    },
    # 6. Covered: Beneficiary status check via portal
    {
        "question": "How can a farmer check their beneficiary payment status as per FAQ 3?",
        "expected_escalate": False,
        "expected_citation": "PMK-FAQ-3",
        "description": "FAQ 3 status check on pmkisan.gov.in",
    },
    # 7. Covered: Incorrect declaration recovery
    {
        "question": "What is the recovery procedure for incorrect declarations under clause 7.0?",
        "expected_escalate": False,
        "expected_citation": "PMK-G-7.0",
        "description": "Clause 7.0 recovery of funds",
    },
    # 8. OUT OF SCOPE 1: PM Mudra loan
    {
        "question": "How do I apply for the PM Mudra business loan under PM-KISAN?",
        "expected_escalate": True,
        "expected_citation": None,
        "description": "Unrelated central loan scheme",
    },
    # 9. OUT OF SCOPE 2: Tractor subsidy in Punjab
    {
        "question": "What is the government subsidy rate for purchasing a commercial tractor in Punjab?",
        "expected_escalate": True,
        "expected_citation": None,
        "description": "State tractor machinery subsidy",
    },
    # 10. OUT OF SCOPE 3: Crypto trading profits
    {
        "question": "Can I transfer my crypto and bitcoin trading profits into the PM-KISAN bank account?",
        "expected_escalate": True,
        "expected_citation": None,
        "description": "Cryptocurrency trading completely out of scope",
    },
]


@pytest.mark.parametrize("item", QUESTIONS_10_SUITE, ids=lambda x: x["description"])
def test_10_questions_via_ask_endpoint(client, item):
    """Tests all 10 questions via POST /ask: 7 covered must not escalate, 3 uncovered must escalate."""
    response = client.post("/ask", json={"question": item["question"], "lang": "en"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    data = response.json()
    assert "answer" in data
    assert "citations" in data
    assert "confidence" in data
    assert "needs_escalation" in data

    if item["expected_escalate"]:
        # Must escalate
        assert data["needs_escalation"] is True, (
            f"Question should escalate: {item['question']}\nGot response: {data}"
        )
        assert len(data["citations"]) == 0, "Out of scope questions must not cite clauses"
        assert "escalat" in data["answer"].lower() or "not covered" in data["answer"].lower()
    else:
        # Covered: must cite and not escalate
        assert data["needs_escalation"] is False, (
            f"Question should NOT escalate: {item['question']}\nGot response: {data}"
        )
        assert len(data["citations"]) > 0, f"Expected citations for covered question: {item['question']}"
        cited_ids = [c["id"] for c in data["citations"]]
        assert item["expected_citation"] in cited_ids, (
            f"Expected {item['expected_citation']} in {cited_ids}"
        )
        assert data["confidence"] > 0.0


def test_ask_endpoint_hindi(client):
    """Tests POST /ask with Hindi language translation."""
    response = client.post("/ask", json={"question": "Who is eligible under clause 4.2?", "lang": "hi"})
    assert response.status_code == 200
    data = response.json()
    assert data["needs_escalation"] is False
    assert len(data["citations"]) > 0
    # Check that Hindi text is returned
    assert "खंड" in data["answer"] or "पीएम-किसान" in data["answer"] or "पात्र" in data["answer"]
