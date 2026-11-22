import asyncio
import json
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from agent import get_registration_agent
from mirror_server import start_mirror_in_background


@pytest.fixture(scope="session", autouse=True)
def setup_mirror():
    """Ensure mirror server is listening on port 4000."""
    start_mirror_in_background(4000)


@pytest.fixture
def sample_profile():
    return {
        "farmer_name": "Ram Prasad Sharma",
        "gender": "Male",
        "category": "General",
        "farmer_type": "Small (1-2 Ha)",
        "aadhaar_number": "992812341098",
        "mobile_number": "9876543210",
        "state": "Uttar Pradesh",
        "district": "Prayagraj",
        "sub_district": "Karchana",
        "village": "Rampur",
        "khasra_number": "142/3",
        "land_area_ha": 1.45,
        "ifsc_code": "SBIN0001234",
        "bank_name": "State Bank of India",
        "account_number": "30981245678",
    }


def test_agent_end_to_end_flow(sample_profile):
    """Direct agent integration test: fill -> diff -> approve -> submit with consent -> audit log."""
    async def _test():
        agent = get_registration_agent()

        # Step 1: Start Fill
        fill_res = await agent.start_fill(sample_profile, portal_url="http://localhost:4000")
        assert fill_res.session_id.startswith("sess_")
        assert fill_res.status == "PENDING_APPROVAL"
        assert fill_res.before_screenshot.startswith("data:image/png;base64,")
        assert fill_res.after_screenshot.startswith("data:image/png;base64,")
        assert len(fill_res.diffs) >= 10

        # Verify farmerName diff
        name_diff = next((d for d in fill_res.diffs if d.field_id == "farmerName"), None)
        assert name_diff is not None
        assert name_diff.after_value == "Ram Prasad Sharma"
        assert name_diff.is_modified is True

        # Step 2: Approve Diff -> Pause at OTP
        approve_res = await agent.approve_diff(fill_res.session_id)
        assert approve_res.session_id == fill_res.session_id
        assert approve_res.status == "PAUSED_FOR_OTP"
        assert approve_res.otp_screenshot.startswith("data:image/png;base64,")

        # Step 3: Safety Constraint: Submit WITHOUT consent MUST raise ValueError
        with pytest.raises(ValueError) as excinfo:
            await agent.submit_with_consent(
                session_id=fill_res.session_id,
                otp="123456",
                explicit_consent=False,
            )
        assert "SUBMISSION_BLOCKED" in str(excinfo.value)

        # Step 4: Submit WITH explicit consent
        submit_res = await agent.submit_with_consent(
            session_id=fill_res.session_id,
            otp="123456",
            explicit_consent=True,
        )
        assert submit_res.status == "SUBMITTED"
        assert submit_res.registration_number.startswith("PMK-REG-2026-")
        assert submit_res.submitted_screenshot.startswith("data:image/png;base64,")

        # Step 5: Verify Audit Log on Disk
        audit_path = Path(submit_res.audit_log_path)
        assert audit_path.exists()

        log_data = json.loads(audit_path.read_text(encoding="utf-8"))
        assert log_data["session_id"] == fill_res.session_id
        assert log_data["registration_number"] == submit_res.registration_number
        assert log_data["consent_verification"]["explicit_citizen_consent_granted"] is True
        assert "XXXX" in log_data["citizen_profile_snapshot"]["masked_aadhaar"]
        assert log_data["citizen_profile_snapshot"]["farmer_name"] == "Ram Prasad Sharma"
        assert "tamper_evident_sha256" in log_data
        assert len(log_data["tamper_evident_sha256"]) == 64

    asyncio.run(_test())


def test_api_agent_http_endpoints(sample_profile):
    """Tests the full agent flow via FastAPI HTTP endpoints, verifying consent blocking."""
    async def _test_http():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. POST /agent/start-fill
            r_fill = await client.post("/agent/start-fill", json={"profile": sample_profile})
            assert r_fill.status_code == 200
            fill_data = r_fill.json()
            session_id = fill_data["session_id"]
            assert fill_data["status"] == "PENDING_APPROVAL"
            assert len(fill_data["diffs"]) > 0

            # 2. POST /agent/approve-diff
            r_appr = await client.post("/agent/approve-diff", json={"session_id": session_id})
            assert r_appr.status_code == 200
            appr_data = r_appr.json()
            assert appr_data["status"] == "PAUSED_FOR_OTP"

            # 3. POST /agent/submit-with-consent without consent MUST return 400
            r_no_consent = await client.post(
                "/agent/submit-with-consent",
                json={"session_id": session_id, "otp": "654321", "explicit_consent": False},
            )
            assert r_no_consent.status_code == 400
            assert "SUBMISSION_BLOCKED" in r_no_consent.json()["detail"]

            # 4. POST /agent/submit-with-consent WITH explicit consent MUST succeed
            r_submit = await client.post(
                "/agent/submit-with-consent",
                json={"session_id": session_id, "otp": "654321", "explicit_consent": True},
            )
            assert r_submit.status_code == 200
            sub_data = r_submit.json()
            assert sub_data["status"] == "SUBMITTED"
            assert "PMK-REG-2026-" in sub_data["registration_number"]

            # 5. GET /agent/audit-log/{session_id}
            r_audit = await client.get(f"/agent/audit-log/{session_id}")
            assert r_audit.status_code == 200
            audit_json = r_audit.json()
            assert audit_json["registration_number"] == sub_data["registration_number"]
            assert audit_json["consent_verification"]["explicit_citizen_consent_granted"] is True

    asyncio.run(_test_http())
