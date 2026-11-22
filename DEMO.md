# CivicPilot 🏛️ — 5-Minute Live Demonstration Script

> **Theme**: Grounded Citizen Engagement, Deterministic Eligibility, Safe Browser Automation & Proactive Nudges for PM-KISAN.

---

## Pre-Demo Quick Setup (30 Seconds)

Before starting the presentation, run:

```bash
# 1. Reset demo environment to pristine state
make reset

# 2. Start all services (API on :8000, Web on :3000, Mirror on :4000)
make dev
```

Open your browser to:
- **Web App**: `http://localhost:3000`
- **Mirror Portal**: `http://localhost:4000`
- **Benchmark Metrics**: `http://localhost:3000/metrics`

---

## Demo Script (5 Minutes Breakdown)

### Minute 1: The Problem & Grounded Conversational Intake (0:00 – 1:00)
* **Narrative**:
  > *"Over 110 million Indian farmers rely on PM-KISAN DBT installments, but millions are blocked by cryptic rejections, e-KYC hurdles, and administrative friction. Generic chatbots hallucinate legal rules. CivicPilot solves this by combining grounded Gemini intelligence with an uncompromising deterministic rules engine."*
* **Actions on Screen**:
  1. Show the **"Synthetic Data Only"** sandbox banner at the top of `http://localhost:3000`.
  2. In the top bar, show the **Bilingual Switcher** (`English` / `हिन्दी`). Switch to Hindi and back to English to show instant UI localization.
  3. Under the **Intake & What-If** tab:
     - Click the **🎙️ Voice** button and speak or click quick chips (`Yes`, `1.5 ha`, `No`).
     - Point out the **🔊 Listen** button on assistant replies using browser speech synthesis.
     - Observe how the LLM asks questions one by one and extracts structured values, but **never states eligibility itself**.
     - Once answered, the **Deterministic Verdict Card** renders: **"ELIGIBLE FOR PM-KISAN"** citing Clause `PMK-G-4.1`.
     - In the **What-If Simulation Panel**, toggle *"Paid Income Tax in previous AY"* to `Yes` and click **"Simulate Changes"** — the verdict instantly shifts to **"NOT ELIGIBLE"** citing Clause `PMK-A-2.0` with a red badge!

---

### Minute 2: Document Reconciliation & Notice Explainer (1:00 – 2:00)
* **Narrative**:
  > *"Aadhaar names rarely match handwritten Revenue records or bank passbooks. Let's see how CivicPilot resolves multi-document discrepancies."*
* **Actions on Screen**:
  1. Switch to **Reconcile Documents** tab (`🔍`).
  2. Click **"Load Demo Sample Documents"** (Aadhaar, Land Record, Bank Passbook, Self-Declaration).
  3. Click **"Run Reconciliation"**:
     - Show the **Discrepancy Matrix**:
       * `dob`: Mismatch between Aadhaar (1978) and Passbook (1983) flagged as **CRITICAL**, with **"Fix at UIDAI Seva Kendra"**.
       * `khasra_number`: Plot `142/3` vs `142/8` flagged as **CRITICAL**, with **"Fix at Tehsil / Lekhpal Office"**.
       * `name`: Transliteration variation (*"Ram Prasad Sharma"* vs *"Ramprasad Sharma"*) correctly identified via RapidFuzz.
     - Click **"Correct"** on the DOB field, update to `1978-05-12`, and click **"Save & Re-evaluate"** to show instant discrepancy resolution.
  4. Switch to **Explain Notice** tab (`📄`):
     - Click quick preset notice *"e-KYC Pending Notice"*.
     - Show Gemini Vision extraction + RAG grounding producing a plain-language explanation, official clause citation `[PMK-A-1.1]`, and a concrete 3-step action checklist.

---

### Minute 3: Status Decoder & Safe Playwright Agent (2:00 – 3:15)
* **Narrative**:
  > *"When a farmer's payment fails, portals show cryptic errors. Here's how we decode them and safely automate form registration with human-in-the-loop guardrails."*
* **Actions on Screen**:
  1. Switch to **Decode Status** tab (`🚦`):
     - Click the chip **"Land Seeding: No"** and click **"Decode Status"**:
       * Instantly matches `status_causes.yaml`: *"Bhulekh Linkage Required"* citing Clause `PMK-A-1.2`, designated office *"Tehsil / Lekhpal"*, with step-by-step resolution.
     - Click **"Unknown Error Code"**:
       * Unknown code falls back safely to RAG with **"Requires Official Escalation"** badge and nodal helpline guidance.
  2. Switch to **Registration Agent** tab (`🤖`):
     - Show verified profile for *"Ram Prasad Sharma"*.
     - Click **"🚀 Launch Agent & Fill Form"**:
       * Playwright opens headless Chromium, connects to `http://localhost:4000`, enters 15 verified fields, and captures live before/after screenshots.
     - Step 2: **Diff Inspection & Approval**:
       * Review the side-by-side portal screenshots and the interactive **Field Comparison Table**.
       * Click **"Approve Verified Details & Proceed to OTP ➔"**.
     - Step 3: **Paused at Aadhaar OTP Step**:
       * Show that the browser is paused at the portal OTP gateway.
       * Show that the **Submit button is DISABLED** if the citizen consent checkbox is unchecked.
       * Check the **"Explicit Citizen Consent (Mandatory)"** box and enter OTP `123456`.
       * Click **"Verify OTP & Submit Application ✓"**.
     - Step 4: **Acknowledgement & Tamper-Evident Audit Record**:
       * Application submitted with official reference `PMK-REG-2026-XXXXX`.
       * Expand the **Cryptographic Audit Log**: show timestamps, masked Aadhaar `XXXX-XXXX-1098`, and the **SHA-256 non-repudiation signature**.

---

### Minute 4: Proactive Nudges & Rule Versioning (3:15 – 4:15)
* **Narrative**:
  > *"Schemes constantly evolve. What happens when the Government updates rules? CivicPilot doesn't spam everyone—it only notifies affected citizens."*
* **Actions on Screen**:
  1. In the header bar, click **"⚡ Simulate Rule Change"**:
     - System versions corpus with Amendment 2026.2 (Clause `PMK-A-1.3`: Land transfer cutoff date enforcement).
     - The engine re-evaluates all seeded demo users.
     - Show the instant banner: *"⚡ Rule Amendment 2026.2 Enacted! Only affected citizen (Anita Patel) was notified via Telegram."*
     - Click the **🔔 Bell Icon** to inspect the dispatched nudge drawer:
       * **Anita Patel**: Status shifted from `ELIGIBLE` to `NOT_ELIGIBLE` under Clause `PMK-A-1.3`.
       * **Ram Prasad Sharma**: Remained eligible; zero unnecessary spam sent!
  2. Click **"⏰ Run Cron Nudges"**:
     - Shows proactive background reminders dispatched:
       * **Sunita Devi**: *"⏰ Deadline Reminder: 3 days remain for Aadhaar e-KYC"*.
       * **Vikram Singh**: *"📄 Document Missing: Land record seeding pending with Lekhpal"*.
  3. Mention the **Telegram Bot** (`api/bot/telegram_bot.py`):
     - Citizens can send voice notes directly to the bot on Telegram and receive immediate audio/text scheme guidance.

---

### Minute 5: Evaluation Suite (/metrics) & One-Command Reset (4:15 – 5:00)
* **Narrative**:
  > *"CivicPilot is verified with an automated 30-case evaluation benchmark testing eligibility, citation grounding, escalation safety, and reconciliation recall."*
* **Actions on Screen**:
  1. Click the **📊 /metrics** button in the header (navigates to `/metrics`):
     - Display the KPI dashboard:
       * **Overall Accuracy: 100% (30 / 30 Cases Passed)**
       * **Eligibility Accuracy: 100% (10 / 10)**
       * **Citation Grounding: 100% (8 / 8)**
       * **Escalation Safety: 100% (6 / 6)**
       * **Reconciliation Recall: 100% (6 / 6)**
     - Filter through the categories (`Eligibility`, `Citations`, `Escalation`, `Reconciliation`) to show real execution latencies.
     - Click **"Re-run Live Benchmark"** to show live evaluation across all 30 ground-truth scenarios.
  2. Return to the terminal and run:
     ```bash
     make reset
     ```
     - Show the clean reset restoring the original corpus, re-indexing FTS5, and cleaning audit logs in under 2 seconds.

---

## Key Talking Points for Judges & Evaluators

1. **Deterministic Guardrails**: LLMs extract inputs and explain clauses; they **never** calculate eligibility. Rule logic is 100% pure Python/YAML.
2. **Citizen Protection**: Strict human-in-the-loop review, visual before/after diffs, and refusal to submit without explicit consent.
3. **Multi-Modal Accessibility**: Speech-to-text, text-to-speech, camera OCR, and Telegram bot voice notes make civic benefits accessible to citizens regardless of literacy.
4. **Verifiable Quality**: 77 automated unit tests + 30-case benchmark suite running at 100% accuracy.
