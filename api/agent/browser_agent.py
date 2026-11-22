import asyncio
import base64
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from mirror_server import start_mirror_in_background
from .models import (
    ApproveDiffResponse,
    FieldDiff,
    RegistrationProfile,
    StartFillResponse,
    SubmitConsentResponse,
)

BASE_DIR = Path(__file__).resolve().parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
AUDIT_LOGS_DIR = BASE_DIR / "audit_logs"

SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Field definitions mapping DOM selector ID to Human readable label and profile property
FIELD_DEFINITIONS = [
    {"id": "farmerName", "label": "Farmer Full Name", "attr": "farmer_name", "type": "text"},
    {"id": "gender", "label": "Gender", "attr": "gender", "type": "select"},
    {"id": "category", "label": "Social Category", "attr": "category", "type": "select"},
    {"id": "farmerType", "label": "Farmer Landholding Type", "attr": "farmer_type", "type": "select"},
    {"id": "aadhaarNo", "label": "Aadhaar Card Number", "attr": "aadhaar_number", "type": "text"},
    {"id": "mobileNo", "label": "Linked Mobile Number", "attr": "mobile_number", "type": "text"},
    {"id": "state", "label": "State", "attr": "state", "type": "select"},
    {"id": "district", "label": "District", "attr": "district", "type": "text"},
    {"id": "subDistrict", "label": "Sub-District / Tehsil", "attr": "sub_district", "type": "text"},
    {"id": "village", "label": "Village", "attr": "village", "type": "text"},
    {"id": "khasraNo", "label": "Khasra / Plot Number", "attr": "khasra_number", "type": "text"},
    {"id": "landArea", "label": "Cultivable Area (Ha)", "attr": "land_area_ha", "type": "text"},
    {"id": "ifscCode", "label": "Bank IFSC Code", "attr": "ifsc_code", "type": "text"},
    {"id": "bankName", "label": "Bank Name", "attr": "bank_name", "type": "text"},
    {"id": "accountNo", "label": "Bank Account Number", "attr": "account_number", "type": "text"},
]


class PlaywrightRegistrationAgent:
    """Automates PM-KISAN registration form completion via Playwright.
    Enforces a strict human-in-the-loop workflow:
    1. Fill form and capture before/after field diffs + screenshots.
    2. Pause for citizen/operator review & approval.
    3. Transition to OTP screen & pause for user to enter OTP.
    4. Validate explicit citizen consent (SUBMISSION BLOCKED if not granted).
    5. Submit and record immutable JSON audit log.
    """

    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def _ensure_mirror_available(self, portal_url: str) -> str:
        """Auto-starts background mirror if targeting localhost:4000 or if 8000 is not active."""
        import socket
        if "localhost:4000" in portal_url or "127.0.0.1:4000" in portal_url:
            start_mirror_in_background(4000)
            return portal_url
        if "localhost:8000" in portal_url or "127.0.0.1:8000" in portal_url:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            is_open = sock.connect_ex(("127.0.0.1", 8000)) == 0
            sock.close()
            if not is_open:
                start_mirror_in_background(4000)
                return "http://localhost:4000"
        return portal_url

    async def start_fill(
        self, profile_data: Dict[str, Any], portal_url: str = "http://localhost:8000/mirror"
    ) -> StartFillResponse:
        """Launches browser, takes blank screenshot, fills form fields, takes filled screenshot,
        and computes field diffs."""
        portal_url = self._ensure_mirror_available(portal_url)
        profile = RegistrationProfile.from_dict(profile_data)
        session_id = f"sess_{uuid.uuid4().hex[:12]}"

        # Initialize Playwright
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 920})
        page = await context.new_page()

        try:
            # Navigate to portal
            await page.goto(portal_url, timeout=15000, wait_until="domcontentloaded")
            await page.wait_for_selector("#registrationForm", timeout=10000)

            # 1. Take Before Screenshot
            before_png = await page.screenshot(full_page=True)
            before_path = SCREENSHOTS_DIR / f"{session_id}_before.png"
            before_path.write_bytes(before_png)
            before_b64 = f"data:image/png;base64,{base64.b64encode(before_png).decode('utf-8')}"

            # 2. Record initial field values
            initial_values: Dict[str, str] = {}
            for field in FIELD_DEFINITIONS:
                fid = field["id"]
                try:
                    val = await page.input_value(f"#{fid}")
                except Exception:
                    val = ""
                initial_values[fid] = val

            # 3. Fill fields from profile
            for field in FIELD_DEFINITIONS:
                fid = field["id"]
                attr = field["attr"]
                raw_val = getattr(profile, attr, "")
                str_val = str(raw_val)

                if field["type"] == "select":
                    try:
                        # Attempt to select by label or value
                        await page.select_option(f"#{fid}", label=str_val)
                    except Exception:
                        try:
                            await page.select_option(f"#{fid}", value=str_val)
                        except Exception:
                            pass
                else:
                    await page.fill(f"#{fid}", str_val)

            # Small delay for UI rendering
            await asyncio.sleep(0.3)

            # 4. Take After Fill Screenshot
            after_png = await page.screenshot(full_page=True)
            after_path = SCREENSHOTS_DIR / f"{session_id}_after.png"
            after_path.write_bytes(after_png)
            after_b64 = f"data:image/png;base64,{base64.b64encode(after_png).decode('utf-8')}"

            # 5. Compute Field Diffs
            diffs: List[FieldDiff] = []
            for field in FIELD_DEFINITIONS:
                fid = field["id"]
                try:
                    val_after = await page.input_value(f"#{fid}")
                except Exception:
                    val_after = ""
                val_before = initial_values.get(fid, "")
                diffs.append(
                    FieldDiff(
                        field_id=fid,
                        label=field["label"],
                        before_value=val_before,
                        after_value=val_after,
                        is_modified=(val_before != val_after or bool(val_after)),
                    )
                )

            # Store active session
            self.sessions[session_id] = {
                "session_id": session_id,
                "playwright": pw,
                "browser": browser,
                "context": context,
                "page": page,
                "portal_url": portal_url,
                "profile": profile,
                "diffs": diffs,
                "status": "PENDING_APPROVAL",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "approved_at": None,
                "screenshots": {
                    "before": str(before_path),
                    "after": str(after_path),
                },
            }

            return StartFillResponse(
                session_id=session_id,
                status="PENDING_APPROVAL",
                before_screenshot=before_b64,
                after_screenshot=after_b64,
                diffs=diffs,
                message="Form populated. Review field diffs and approve to proceed to OTP verification.",
            )

        except Exception as e:
            # Clean up on failure
            await browser.close()
            await pw.stop()
            raise RuntimeError(f"Playwright automation failed during form filling: {e}")

    async def approve_diff(self, session_id: str) -> ApproveDiffResponse:
        """User approves the field diffs. Agent clicks proceed and pauses at the OTP step."""
        session = self.sessions.get(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found or expired.")

        if session["status"] != "PENDING_APPROVAL":
            raise ValueError(f"Session '{session_id}' is in state {session['status']}, expected PENDING_APPROVAL.")

        page: Page = session["page"]

        try:
            # Click Proceed to OTP button
            await page.click("#btnProceedToOtp")
            # Wait for OTP section to appear
            await page.wait_for_selector("#otpSection", state="visible", timeout=10000)
            await asyncio.sleep(0.3)

            # Take screenshot of OTP paused state
            otp_png = await page.screenshot(full_page=True)
            otp_path = SCREENSHOTS_DIR / f"{session_id}_otp.png"
            otp_path.write_bytes(otp_png)
            otp_b64 = f"data:image/png;base64,{base64.b64encode(otp_png).decode('utf-8')}"

            session["status"] = "PAUSED_FOR_OTP"
            session["approved_at"] = datetime.now(timezone.utc).isoformat()
            session["screenshots"]["otp"] = str(otp_path)

            return ApproveDiffResponse(
                session_id=session_id,
                status="PAUSED_FOR_OTP",
                otp_screenshot=otp_b64,
                message="Paused at Aadhaar OTP step. Enter 6-digit OTP and provide explicit consent to submit.",
            )

        except Exception as e:
            raise RuntimeError(f"Failed transitioning to OTP screen: {e}")

    async def submit_with_consent(
        self, session_id: str, otp: str, explicit_consent: bool
    ) -> SubmitConsentResponse:
        """Enforces mandatory explicit consent. Fills OTP, submits application,
        extracts registration number, and writes JSON audit log."""
        session = self.sessions.get(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found or expired.")

        # STRICT CONSENT CHECK: Block immediately if user has not given explicit consent
        if not explicit_consent:
            raise ValueError(
                "SUBMISSION_BLOCKED: Explicit citizen consent is legally mandatory. "
                "The agent will never submit an application without explicit consent."
            )

        clean_otp = otp.strip()
        if not clean_otp or len(clean_otp) < 6:
            raise ValueError("Invalid OTP: 6-digit Aadhaar OTP required.")

        page: Page = session["page"]
        profile: RegistrationProfile = session["profile"]

        try:
            # Check the consent box in the DOM
            await page.check("#consentCheckbox")
            # Fill the OTP input
            await page.fill("#otpInput", clean_otp)
            await asyncio.sleep(0.2)

            # Click Submit Application
            await page.click("#btnSubmitApplication")

            # Wait for success acknowledgement section
            await page.wait_for_selector("#successSection", state="visible", timeout=12000)
            await asyncio.sleep(0.3)

            # Extract registration ID & timestamp
            reg_element = await page.query_selector("#registrationNumber")
            reg_id = (await reg_element.inner_text()).strip() if reg_element else "PMK-REG-2026-UNKNOWN"

            # Take final submitted confirmation screenshot
            submitted_png = await page.screenshot(full_page=True)
            submitted_path = SCREENSHOTS_DIR / f"{session_id}_submitted.png"
            submitted_path.write_bytes(submitted_png)
            submitted_b64 = f"data:image/png;base64,{base64.b64encode(submitted_png).decode('utf-8')}"

            session["screenshots"]["submitted"] = str(submitted_path)
            session["status"] = "SUBMITTED"
            submitted_at = datetime.now(timezone.utc).isoformat()

            # Compile Audit Log
            # Mask sensitive values for audit record privacy
            aadhaar_raw = profile.aadhaar_number
            masked_aadhaar = f"XXXX-XXXX-{aadhaar_raw[-4:]}" if len(aadhaar_raw) >= 4 else "XXXXXXXX"

            mobile_raw = profile.mobile_number
            masked_mobile = f"XXXXXX{mobile_raw[-4:]}" if len(mobile_raw) >= 4 else "XXXXXX"

            audit_record = {
                "audit_version": "1.0",
                "session_id": session_id,
                "portal_url": session["portal_url"],
                "registration_number": reg_id,
                "submission_status": "SUCCESS_RECORDED",
                "timestamps": {
                    "session_created": session["created_at"],
                    "diff_approved": session["approved_at"],
                    "application_submitted": submitted_at,
                },
                "consent_verification": {
                    "explicit_citizen_consent_granted": True,
                    "consent_text": (
                        "Explicit Citizen Consent: I hereby give my explicit and informed consent "
                        "to submit this PM-KISAN registration application on my behalf with the "
                        "verified details provided. I declare that all landholding and banking "
                        "particulars are accurate."
                    ),
                    "consent_confirmed_at": submitted_at,
                    "otp_verification_completed": True,
                    "otp_masked": f"***{clean_otp[-2:]}",
                },
                "citizen_profile_snapshot": {
                    "farmer_name": profile.farmer_name,
                    "gender": profile.gender,
                    "category": profile.category,
                    "farmer_type": profile.farmer_type,
                    "masked_aadhaar": masked_aadhaar,
                    "masked_mobile": masked_mobile,
                    "state": profile.state,
                    "district": profile.district,
                    "sub_district": profile.sub_district,
                    "village": profile.village,
                    "khasra_number": profile.khasra_number,
                    "land_area_ha": profile.land_area_ha,
                    "ifsc_code": profile.ifsc_code,
                    "bank_name": profile.bank_name,
                    "account_number_last4": profile.account_number[-4:] if len(profile.account_number) >= 4 else "XXXX",
                },
                "field_diffs": [d.model_dump() for d in session["diffs"]],
                "screenshot_artifacts": {
                    "before_fill": str(session["screenshots"].get("before")),
                    "after_fill": str(session["screenshots"].get("after")),
                    "otp_paused": str(session["screenshots"].get("otp")),
                    "submitted_confirmation": str(submitted_path),
                },
            }

            # Generate SHA-256 non-repudiation signature
            serialized = json.dumps(audit_record, sort_keys=True, indent=2)
            sha256_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
            audit_record["tamper_evident_sha256"] = sha256_hash

            # Save to disk
            audit_path = AUDIT_LOGS_DIR / f"{session_id}.json"
            audit_path.write_text(json.dumps(audit_record, indent=2), encoding="utf-8")

            # Clean up browser resources
            browser: Browser = session["browser"]
            pw = session["playwright"]
            await browser.close()
            await pw.stop()

            # Remove session
            del self.sessions[session_id]

            return SubmitConsentResponse(
                session_id=session_id,
                status="SUBMITTED",
                registration_number=reg_id,
                submitted_screenshot=submitted_b64,
                audit_log_path=str(audit_path),
                audit_log=audit_record,
                message=f"Application submitted successfully with registration number {reg_id}. Audit log written.",
            )

        except Exception as e:
            # Keep browser open if there is an error during submission so user can inspect or retry
            raise RuntimeError(f"Error during application submission: {e}")

    async def cleanup_all(self):
        """Clean up any open browsers."""
        for sess in list(self.sessions.values()):
            try:
                await sess["browser"].close()
                await sess["playwright"].stop()
            except Exception:
                pass
        self.sessions.clear()


# Singleton instance
_agent_instance: Optional[PlaywrightRegistrationAgent] = None


def get_registration_agent() -> PlaywrightRegistrationAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = PlaywrightRegistrationAgent()
    return _agent_instance
