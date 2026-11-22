import pytest
from fastapi.testclient import TestClient

from main import app
from rules.engine import EligibilityEngine, evaluate_profile, whatif_analysis


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def base_eligible_profile():
    """A valid, fully eligible farmer profile."""
    return {
        "owns_cultivable_land": True,
        "land_area_hectares": 1.5,
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
        "is_registered_professional": False,
    }


# ============================================================================
# UNIT TESTS FIRST (At least 25 cases, including edge cases)
# ============================================================================

def test_case_01_fully_eligible_small_farmer(base_eligible_profile):
    """Case 1: Standard eligible farmer with all criteria met."""
    res = evaluate_profile(base_eligible_profile)
    assert res["verdict"] == "ELIGIBLE"
    assert len(res["failed_rules"]) == 0
    assert len(res["missing_inputs"]) == 0
    assert len(res["passed_rules"]) >= 6


def test_case_02_landless_tenant_farmer(base_eligible_profile):
    """Case 2: Landless tenant farmer (Clause PMK-G-4.2)."""
    profile = {**base_eligible_profile, "owns_cultivable_land": False}
    res = evaluate_profile(profile)
    assert res["verdict"] == "INELIGIBLE"
    failed_ids = [r["rule_id"] for r in res["failed_rules"]]
    assert "RULE_LAND_OWNERSHIP" in failed_ids
    citations = [c["id"] for c in res["citations"]]
    assert "PMK-G-4.2" in citations


def test_case_03_zero_or_negative_land_area(base_eligible_profile):
    """Case 3: Land area is zero."""
    profile = {**base_eligible_profile, "land_area_hectares": 0.0}
    res = evaluate_profile(profile)
    assert res["verdict"] == "INELIGIBLE"
    failed_ids = [r["rule_id"] for r in res["failed_rules"]]
    assert "RULE_LAND_AREA" in failed_ids


def test_case_04_marginal_farmer_positive_area(base_eligible_profile):
    """Case 4: Edge case - tiny fractional land area (marginal farmer, 0.02 ha)."""
    profile = {**base_eligible_profile, "land_area_hectares": 0.02}
    res = evaluate_profile(profile)
    assert res["verdict"] == "ELIGIBLE"


def test_case_05_land_record_seeding_pending(base_eligible_profile):
    """Case 5: Land records not seeded in state portal (Clause PMK-A-1.2)."""
    profile = {**base_eligible_profile, "land_record_seeded": False}
    res = evaluate_profile(profile)
    assert res["verdict"] == "INELIGIBLE"
    failed_ids = [r["rule_id"] for r in res["failed_rules"]]
    assert "RULE_LAND_RECORD_SEEDING" in failed_ids
    citations = [c["id"] for c in res["citations"]]
    assert "PMK-A-1.2" in citations


def test_case_06_aadhaar_not_seeded_in_bank(base_eligible_profile):
    """Case 6: Aadhaar not seeded with bank account (Clause PMK-A-1.1)."""
    profile = {**base_eligible_profile, "aadhaar_seeded": False}
    res = evaluate_profile(profile)
    assert res["verdict"] == "INELIGIBLE"
    failed_ids = [r["rule_id"] for r in res["failed_rules"]]
    assert "RULE_AADHAAR_SEEDED" in failed_ids
    citations = [c["id"] for c in res["citations"]]
    assert "PMK-A-1.1" in citations


def test_case_07_ekyc_pending(base_eligible_profile):
    """Case 7: e-KYC verification pending (Clause PMK-A-1.1)."""
    profile = {**base_eligible_profile, "ekyc_completed": False}
    res = evaluate_profile(profile)
    assert res["verdict"] == "INELIGIBLE"
    failed_ids = [r["rule_id"] for r in res["failed_rules"]]
    assert "RULE_EKYC_MANDATORY" in failed_ids


def test_case_08_bank_account_dbt_inactive(base_eligible_profile):
    """Case 8: Bank account not enabled for DBT / NPCI bridge (Clause PMK-G-6.0)."""
    profile = {**base_eligible_profile, "bank_account_dbt_active": False}
    res = evaluate_profile(profile)
    assert res["verdict"] == "INELIGIBLE"
    failed_ids = [r["rule_id"] for r in res["failed_rules"]]
    assert "RULE_BANK_DBT_ACTIVE" in failed_ids
    citations = [c["id"] for c in res["citations"]]
    assert "PMK-G-6.0" in citations


def test_case_09_institutional_landholder(base_eligible_profile):
    """Case 9: Institutional landholder exclusion (Clause PMK-G-5.1)."""
    profile = {**base_eligible_profile, "is_institutional_landholder": True}
    res = evaluate_profile(profile)
    assert res["verdict"] == "INELIGIBLE"
    failed_ids = [r["rule_id"] for r in res["failed_rules"]]
    assert "RULE_EXCL_INSTITUTIONAL" in failed_ids
    citations = [c["id"] for c in res["citations"]]
    assert "PMK-G-5.1" in citations


def test_case_10_constitutional_post_holder(base_eligible_profile):
    """Case 10: Former/present constitutional post holder (Clause PMK-G-5.0)."""
    profile = {**base_eligible_profile, "is_constitutional_post_holder": True}
    res = evaluate_profile(profile)
    assert res["verdict"] == "INELIGIBLE"
    failed_ids = [r["rule_id"] for r in res["failed_rules"]]
    assert "RULE_EXCL_CONSTITUTIONAL" in failed_ids
    citations = [c["id"] for c in res["citations"]]
    assert "PMK-G-5.0" in citations


def test_case_11_govt_officer_regular(base_eligible_profile):
    """Case 11: Regular government officer (non-Class IV) exclusion (Clause PMK-G-5.1)."""
    profile = {**base_eligible_profile, "is_government_employee": True, "is_class_iv_or_group_d": False}
    res = evaluate_profile(profile)
    assert res["verdict"] == "INELIGIBLE"
    failed_ids = [r["rule_id"] for r in res["failed_rules"]]
    assert "RULE_EXCL_GOVT_EMPLOYEE" in failed_ids


def test_case_12_govt_employee_group_d_exemption(base_eligible_profile):
    """Case 12: Group D / Class IV / MTS employee exception -> ELIGIBLE (Clause PMK-G-5.1)."""
    profile = {**base_eligible_profile, "is_government_employee": True, "is_class_iv_or_group_d": True}
    res = evaluate_profile(profile)
    assert res["verdict"] == "ELIGIBLE"


def test_case_13_pensioner_exact_threshold(base_eligible_profile):
    """Case 13: Pensioner with exactly Rs. 10,000 monthly pension (Clause PMK-G-5.1)."""
    profile = {**base_eligible_profile, "monthly_pension": 10000.0, "is_class_iv_or_group_d": False}
    res = evaluate_profile(profile)
    assert res["verdict"] == "INELIGIBLE"
    failed_ids = [r["rule_id"] for r in res["failed_rules"]]
    assert "RULE_EXCL_PENSIONER" in failed_ids


def test_case_14_pensioner_above_threshold(base_eligible_profile):
    """Case 14: Pensioner with Rs. 20,000 monthly pension."""
    profile = {**base_eligible_profile, "monthly_pension": 20000.0, "is_class_iv_or_group_d": False}
    res = evaluate_profile(profile)
    assert res["verdict"] == "INELIGIBLE"
    failed_ids = [r["rule_id"] for r in res["failed_rules"]]
    assert "RULE_EXCL_PENSIONER" in failed_ids


def test_case_15_pensioner_below_threshold(base_eligible_profile):
    """Case 15: Pensioner with Rs. 9,999 monthly pension -> ELIGIBLE."""
    profile = {**base_eligible_profile, "monthly_pension": 9999.0, "is_class_iv_or_group_d": False}
    res = evaluate_profile(profile)
    assert res["verdict"] == "ELIGIBLE"


def test_case_16_pensioner_class_iv_exemption(base_eligible_profile):
    """Case 16: Retired Class IV / Group D pensioner receiving >= 10,000 -> ELIGIBLE."""
    profile = {**base_eligible_profile, "monthly_pension": 14000.0, "is_class_iv_or_group_d": True}
    res = evaluate_profile(profile)
    assert res["verdict"] == "ELIGIBLE"


def test_case_17_income_tax_payer_last_ay(base_eligible_profile):
    """Case 17: Individual paid income tax in last assessment year (Clause PMK-A-2.0)."""
    profile = {**base_eligible_profile, "paid_income_tax_last_ay": True}
    res = evaluate_profile(profile)
    assert res["verdict"] == "INELIGIBLE"
    failed_ids = [r["rule_id"] for r in res["failed_rules"]]
    assert "RULE_EXCL_INCOME_TAX" in failed_ids
    citations = [c["id"] for c in res["citations"]]
    assert "PMK-A-2.0" in citations


def test_case_18_family_member_income_tax_payer(base_eligible_profile):
    """Case 18: Family member paid income tax (Clause PMK-A-2.0)."""
    profile = {**base_eligible_profile, "family_member_paid_income_tax": True}
    res = evaluate_profile(profile)
    assert res["verdict"] == "INELIGIBLE"
    failed_ids = [r["rule_id"] for r in res["failed_rules"]]
    assert "RULE_EXCL_FAMILY_INCOME_TAX" in failed_ids


def test_case_19_registered_doctor(base_eligible_profile):
    """Case 19: Registered professional (Doctor) (Clause PMK-G-5.0)."""
    profile = {**base_eligible_profile, "is_registered_professional": True, "professional_type": "Doctor"}
    res = evaluate_profile(profile)
    assert res["verdict"] == "INELIGIBLE"
    failed_ids = [r["rule_id"] for r in res["failed_rules"]]
    assert "RULE_EXCL_PROFESSIONAL" in failed_ids


def test_case_20_registered_lawyer_or_ca(base_eligible_profile):
    """Case 20: Registered professional (Lawyer / CA)."""
    profile = {**base_eligible_profile, "is_registered_professional": True, "professional_type": "Lawyer"}
    res = evaluate_profile(profile)
    assert res["verdict"] == "INELIGIBLE"
    failed_ids = [r["rule_id"] for r in res["failed_rules"]]
    assert "RULE_EXCL_PROFESSIONAL" in failed_ids


def test_case_21_missing_land_ownership_input(base_eligible_profile):
    """Case 21: Required input missing (owns_cultivable_land is None/missing)."""
    profile = {**base_eligible_profile}
    del profile["owns_cultivable_land"]
    res = evaluate_profile(profile)
    assert res["verdict"] == "INCOMPLETE"
    assert "owns_cultivable_land" in res["missing_inputs"]


def test_case_22_missing_multiple_inputs(base_eligible_profile):
    """Case 22: Multiple required inputs missing."""
    profile = {**base_eligible_profile}
    del profile["ekyc_completed"]
    del profile["aadhaar_seeded"]
    res = evaluate_profile(profile)
    assert res["verdict"] == "INCOMPLETE"
    assert "ekyc_completed" in res["missing_inputs"]
    assert "aadhaar_seeded" in res["missing_inputs"]


def test_case_23_empty_profile():
    """Case 23: Completely empty profile."""
    res = evaluate_profile({})
    assert res["verdict"] == "INCOMPLETE"
    assert len(res["missing_inputs"]) >= 5


def test_case_24_multiple_failures(base_eligible_profile):
    """Case 24: Multiple disqualifying conditions simultaneously."""
    profile = {
        **base_eligible_profile,
        "owns_cultivable_land": False,
        "ekyc_completed": False,
        "paid_income_tax_last_ay": True,
    }
    res = evaluate_profile(profile)
    assert res["verdict"] == "INELIGIBLE"
    assert len(res["failed_rules"]) == 3
    failed_ids = {r["rule_id"] for r in res["failed_rules"]}
    assert failed_ids == {"RULE_LAND_OWNERSHIP", "RULE_EKYC_MANDATORY", "RULE_EXCL_INCOME_TAX"}


def test_case_25_string_boolean_edge_case(base_eligible_profile):
    """Case 25: Edge case - string booleans ('yes', 'true', 'false')."""
    profile = {
        **base_eligible_profile,
        "owns_cultivable_land": "yes",
        "ekyc_completed": "true",
        "paid_income_tax_last_ay": "no",
    }
    res = evaluate_profile(profile)
    assert res["verdict"] == "ELIGIBLE"


def test_case_26_rule_version_and_clause_id_presence(base_eligible_profile):
    """Case 26: Verify each rule carries clause_id and rule_version."""
    profile = {**base_eligible_profile, "ekyc_completed": False}
    res = evaluate_profile(profile)
    for rule in res["failed_rules"] + res["passed_rules"]:
        assert "clause_id" in rule and rule["clause_id"]
        assert "rule_version" in rule and rule["rule_version"]


def test_case_27_whatif_resolution(base_eligible_profile):
    """Case 27: What-If simulation resolving a failure."""
    ineligible_profile = {**base_eligible_profile, "ekyc_completed": False}
    diff = whatif_analysis(ineligible_profile, {"ekyc_completed": True})

    assert diff["original_verdict"] == "INELIGIBLE"
    assert diff["new_verdict"] == "ELIGIBLE"
    assert diff["verdict_changed"] is True
    assert "RULE_EKYC_MANDATORY" in diff["fixed_rules"]
    assert len(diff["newly_failed_rules"]) == 0


def test_case_28_whatif_new_failure(base_eligible_profile):
    """Case 28: What-If simulation introducing a new failure."""
    diff = whatif_analysis(base_eligible_profile, {"paid_income_tax_last_ay": True})

    assert diff["original_verdict"] == "ELIGIBLE"
    assert diff["new_verdict"] == "INELIGIBLE"
    assert diff["verdict_changed"] is True
    assert "RULE_EXCL_INCOME_TAX" in diff["newly_failed_rules"]
    assert len(diff["fixed_rules"]) == 0


def test_case_29_post_eligibility_endpoint(client, base_eligible_profile):
    """Case 29: Test POST /eligibility endpoint."""
    response = client.post("/eligibility", json={"profile": base_eligible_profile})
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] == "ELIGIBLE"
    assert "failed_rules" in data
    assert "passed_rules" in data
    assert "missing_inputs" in data
    assert "citations" in data


def test_case_30_post_whatif_endpoint(client, base_eligible_profile):
    """Case 30: Test POST /whatif endpoint."""
    ineligible = {**base_eligible_profile, "aadhaar_seeded": False}
    response = client.post(
        "/whatif",
        json={
            "profile": ineligible,
            "changes": {"aadhaar_seeded": True},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["original_verdict"] == "INELIGIBLE"
    assert data["new_verdict"] == "ELIGIBLE"
    assert data["verdict_changed"] is True
    assert "RULE_AADHAAR_SEEDED" in data["fixed_rules"]
