import shutil
import sys
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
API_DIR = ROOT_DIR / "api"
CORPUS_DIR = ROOT_DIR / "corpus" / "pmkisan"
SCREENSHOTS_DIR = API_DIR / "agent" / "screenshots"
AUDIT_LOGS_DIR = API_DIR / "agent" / "audit_logs"
DB_FILE = API_DIR / "civicpilot_rag.db"


ORIGINAL_AMENDMENT_NOTICES = """# PM-KISAN Amendment Notices & Administrative Circulars

## Notice 1: Mandatory Aadhaar Seeding and e-KYC Verification
**Reference No**: 1-1/2022-Credit-PM-KISAN  
**Date of Issue**: 15-December-2022  
**Issuing Authority**: Ministry of Agriculture and Farmers Welfare, Department of Agriculture & Farmers Welfare  

### Clause PMK-A-1.1: Mandatory e-KYC Authentication for Installment Release
1. It has been decided with the approval of the Competent Authority that release of all subsequent installments under PM-KISAN shall be strictly contingent upon completion of biometric or OTP-based Aadhaar e-KYC authentication.
2. Beneficiaries may complete e-KYC through:
   - OTP-based authentication on the PM-KISAN portal (pmkisan.gov.in) using the Aadhaar-linked mobile number.
   - Biometric authentication using thumb/facial recognition at any Common Service Centre (CSC) or State Seva Kendra.
3. Installments shall remain withheld for beneficiaries whose e-KYC status is flagged as 'No' or 'Pending' until authentication is successfully completed and synchronized with the central DBT ledger.

---

## Notice 2: Land Records Seeding and Cutoff Date Clarification
**Reference No**: 4-3/2023-PM-KISAN-Legal  
**Date of Issue**: 20-August-2023  
**Issuing Authority**: Direct Benefit Transfer (DBT) Mission, Government of India  

### Clause PMK-A-1.2: Mandatory Digital Land Record Verification
1. Every farmer beneficiary must possess land details linked and seeded in the State Revenue Bhulekh digital database.
2. Beneficiaries who acquired landholding title through purchase or transfer after the scheme cutoff date of **01-February-2019** shall not be eligible for scheme benefits, except in genuine cases of inheritance or succession upon death of the landowner.
3. Physical land mutation certificates and Khasra/Khatauni verification must be completed by the designated Tehsil Revenue Officer (Lekhpal/Patwari) before enrollment is approved.

---

## Notice 3: Exclusion of Income Tax Payers and Professional Practitioners
**Reference No**: 9-2/2021-Coord-PM-KISAN  
**Date of Issue**: 10-January-2021  
**Issuing Authority**: PM-KISAN National Monitoring Committee  

### Clause PMK-A-2.0: Identification and Recovery from Ineligible Tax Payers
1. Any beneficiary or beneficiary family member who has paid income tax under the Income Tax Act, 1961 in the preceding assessment year is strictly ineligible.
2. If payments have been erroneously disbursed to an income tax payee, the State Government shall issue a formal recovery demand notice directing refund of the principal amount to the designated State PM-KISAN nodal recovery account.
"""


def reset_demo():
    print("=" * 60)
    print("  CivicPilot Demo Environment Reset")
    print("=" * 60)

    # 1. Restore original amendment notices
    print("[1/5] Restoring original scheme corpus...")
    amendment_file = CORPUS_DIR / "amendment_notices.md"
    if amendment_file.exists():
        amendment_file.write_text(ORIGINAL_AMENDMENT_NOTICES.strip() + "\n", encoding="utf-8")
        print("      ✓ Restored corpus/pmkisan/amendment_notices.md")

    # 2. Reset / Reindex RAG Database
    print("[2/5] Re-indexing SQLite RAG database...")
    sys.path.insert(0, str(API_DIR))
    from rag.service import RAGService
    rag = RAGService()
    rag.index_corpus(str(CORPUS_DIR))
    print(f"      ✓ Re-indexed {rag.db.count()} grounded scheme clauses in SQLite FTS5")

    # 3. Clean generated agent screenshots
    print("[3/5] Cleaning generated agent screenshots...")
    if SCREENSHOTS_DIR.exists():
        count = 0
        for f in SCREENSHOTS_DIR.glob("*.png"):
            f.unlink()
            count += 1
        print(f"      ✓ Removed {count} agent screenshot artifacts")

    # 4. Clean generated audit logs
    print("[4/5] Cleaning session audit logs...")
    if AUDIT_LOGS_DIR.exists():
        count = 0
        for f in AUDIT_LOGS_DIR.glob("*.json"):
            f.unlink()
            count += 1
        print(f"      ✓ Removed {count} previous session audit logs")

    # 5. Reset Rule Simulator State
    print("[5/5] Resetting Rule Simulator state...")
    from rules.simulator import get_rule_simulator
    sim = get_rule_simulator()
    sim.active_version = "1.0"
    sim.rule_change_history.clear()
    sim.dispatched_nudges.clear()
    print("      ✓ Rule simulator version reset to v1.0, nudges cleared")

    print("\n" + "=" * 60)
    print("  ✓ CivicPilot Demo Environment Reset Successfully!")
    print("  Ready for a clean 5-minute presentation demo.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    reset_demo()
