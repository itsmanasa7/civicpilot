import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_interview_turn_flow(client):
    """Tests conversational interview turn-by-turn intake."""
    # Turn 1: Initial call
    r1 = client.post("/interview", json={"message": "", "profile": {}, "current_field": None, "lang": "en"})
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["is_complete"] is False
    assert d1["current_field"] == "owns_cultivable_land"
    assert "cultivable" in d1["assistant_message"].lower()

    # Turn 2: Citizen answers "Yes, we own our farm"
    r2 = client.post(
        "/interview",
        json={"message": "Yes, we own our farm", "profile": d1["extracted_profile"], "current_field": d1["current_field"], "lang": "en"},
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["extracted_profile"]["owns_cultivable_land"] is True
    assert d2["current_field"] == "land_area_hectares"

    # Turn 3: Citizen answers "1.5 hectares"
    r3 = client.post(
        "/interview",
        json={"message": "1.5 hectares", "profile": d2["extracted_profile"], "current_field": d2["current_field"], "lang": "en"},
    )
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["extracted_profile"]["land_area_hectares"] == 1.5
    assert d3["is_complete"] is False


def test_interview_hindi_language(client):
    """Tests interview turn in Hindi."""
    res = client.post("/interview", json={"message": "", "profile": {}, "current_field": None, "lang": "hi"})
    assert res.status_code == 200
    data = res.json()
    assert data["current_field"] == "owns_cultivable_land"
    # Hindi text assertion
    assert any(ord(c) >= 0x0900 and ord(c) <= 0x097F for c in data["assistant_message"])


def test_interview_completion_calls_rule_engine(client):
    """Tests that when all fields are populated, the rule engine is invoked and verdict returned."""
    full_profile = {
        "owns_cultivable_land": True,
        "land_area_hectares": 1.2,
        "land_record_seeded": True,
        "aadhaar_seeded": True,
        "ekyc_completed": True,
        "bank_account_dbt_active": True,
        "is_institutional_landholder": False,
        "is_constitutional_post_holder": False,
        "is_government_employee": False,
        "is_class_iv_or_group_d": False,
        "monthly_pension": 0.0,
        "paid_income_tax_last_ay": False,
        "family_member_paid_income_tax": False,
        # Leaving last field for user to supply
    }

    res = client.post(
        "/interview",
        json={
            "message": "No, I am not a doctor or professional",
            "profile": full_profile,
            "current_field": "is_registered_professional",
            "lang": "en",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_complete"] is True
    assert data["verdict_result"] is not None
    assert data["verdict_result"]["verdict"] == "ELIGIBLE"
    assert len(data["verdict_result"]["failed_rules"]) == 0


def test_reconcile_synthetic_demo_documents(client):
    """Tests POST /reconcile with synthetic demo documents in /demo-data."""
    res = client.post("/reconcile")
    assert res.status_code == 200
    data = res.json()

    assert "documents_analyzed" in data
    assert len(data["documents_analyzed"]) >= 4
    assert data["overall_status"] == "DISCREPANCIES_FOUND"
    assert data["critical_count"] >= 1

    disc_fields = {d["field"]: d for d in data["discrepancies"]}

    # Verify DOB mismatch is detected as CRITICAL
    assert "dob" in disc_fields
    assert disc_fields["dob"]["severity"] == "CRITICAL"
    assert "UIDAI" in disc_fields["dob"]["fix_at_office"] or "Kendra" in disc_fields["dob"]["fix_at_office"]

    # Verify Khasra mismatch is detected as CRITICAL
    assert "khasra_number" in disc_fields
    assert disc_fields["khasra_number"]["severity"] == "CRITICAL"
    assert "Tehsil" in disc_fields["khasra_number"]["fix_at_office"] or "Lekhpal" in disc_fields["khasra_number"]["fix_at_office"]

    # Verify Name variation detected
    assert "name" in disc_fields
    assert disc_fields["name"]["severity"] in ("CRITICAL", "MODERATE", "MINOR")

    # Verify Address renaming detected
    assert "address" in disc_fields


def test_reconcile_manual_correction(client):
    """Tests POST /reconcile/correct when user updates mismatched DOB to resolve discrepancy."""
    initial_res = client.post("/reconcile")
    extracted_docs = initial_res.json()["extracted_fields_by_doc"]

    # Citizen manually corrects self_declaration DOB from 1979-05-12 to 1978-05-12
    corrections = {
        "self_declaration": {"dob": "1978-05-12"},
    }

    res = client.post(
        "/reconcile/correct",
        json={
            "extracted_fields_by_doc": extracted_docs,
            "corrections": corrections,
        },
    )
    assert res.status_code == 200
    data = res.json()

    disc_fields = {d["field"]: d for d in data["discrepancies"]}
    assert disc_fields["dob"]["severity"] == "MATCHED"
    assert disc_fields["dob"]["similarity_score"] == 1.0
