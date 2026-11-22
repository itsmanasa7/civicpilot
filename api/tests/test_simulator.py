import pytest
from fastapi.testclient import TestClient

from main import app
from rules.simulator import get_rule_simulator


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def simulator():
    return get_rule_simulator()


def test_simulate_rule_amendment_notifies_only_affected_users(simulator):
    """Verifies that simulating a rule amendment notifies ONLY affected users whose verdict changed."""
    res = simulator.simulate_rule_amendment(
        new_version="2026.2_TEST",
        amendment_description="Strict Cutoff Date Enforcement",
    )

    assert res["new_version"] == "2026.2_TEST"
    assert res["total_users_checked"] >= 4

    # Only Anita Patel (acquired land post cutoff) should be affected!
    affected_names = [u["name"] for u in res["affected_users"]]
    assert "Anita Patel" in affected_names
    # Ram Prasad Sharma remains eligible and must NOT be in affected_names
    assert "Ram Prasad Sharma" not in affected_names
    # Ramesh Kumar was already ineligible and must NOT be in affected_names
    assert "Ramesh Kumar" not in affected_names

    # Check notification contents
    anita_nudge = next(u["nudge_sent"] for u in res["affected_users"] if u["name"] == "Anita Patel")
    assert anita_nudge["nudge_type"] == "RULE_CHANGED"
    assert "PMK-A-1.3" in anita_nudge["clause_cited"]
    assert "Anita Patel" in anita_nudge["message"]


def test_cron_nudge_dispatch(simulator):
    """Tests periodic cron job dispatching deadline reminders and missing document nudges."""
    nudges = simulator.run_cron_nudge_dispatch()
    assert len(nudges) >= 2

    nudge_types = [n["nudge_type"] for n in nudges]
    assert "DEADLINE_ALERT" in nudge_types
    assert "DOCUMENT_MISSING" in nudge_types

    # e-KYC deadline alert for Sunita Devi
    sunita_nudge = next((n for n in nudges if "Sunita Devi" in n["message"]), None)
    assert sunita_nudge is not None
    assert "3 days" in sunita_nudge["message"]
    assert "e-KYC" in sunita_nudge["message"]

    # Missing land record for Vikram Singh
    vikram_nudge = next((n for n in nudges if "Vikram Singh" in n["message"]), None)
    assert vikram_nudge is not None
    assert "land record" in vikram_nudge["message"].lower()


def test_api_simulate_rule_change_endpoint(client):
    """Tests POST /simulate-rule-change endpoint."""
    resp = client.post(
        "/simulate-rule-change",
        params={"new_version": "2026.3", "description": "Group D Verification Mandate"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["new_version"] == "2026.3"
    assert "affected_users" in data
