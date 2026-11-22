"use client";

import React, { useState } from "react";
import { Locale } from "@/lib/i18n";

interface FieldDiff {
  field_id: string;
  label: string;
  before_value: string;
  after_value: string;
  is_modified: boolean;
}

interface StartFillResult {
  session_id: string;
  status: string;
  before_screenshot: string;
  after_screenshot: string;
  diffs: FieldDiff[];
  message: string;
}

interface ApproveDiffResult {
  session_id: string;
  status: string;
  otp_screenshot: string;
  message: string;
}

interface SubmitResult {
  session_id: string;
  status: string;
  registration_number: string;
  submitted_screenshot: string;
  audit_log_path: string;
  audit_log: any;
  message: string;
}

interface RegistrationAgentProps {
  locale: Locale;
}

export default function RegistrationAgent({ locale }: RegistrationAgentProps) {
  // Verified Citizen Profile
  const [profile, setProfile] = useState({
    farmer_name: "Ram Prasad Sharma",
    gender: "Male",
    category: "General",
    farmer_type: "Small (1-2 Ha)",
    aadhaar_number: "992812341098",
    mobile_number: "9876543210",
    state: "Uttar Pradesh",
    district: "Prayagraj",
    sub_district: "Karchana",
    village: "Rampur",
    khasra_number: "142/3",
    land_area_ha: 1.45,
    ifsc_code: "SBIN0001234",
    bank_name: "State Bank of India",
    account_number: "30981245678",
  });

  // Workflow State: 'PROFILE' | 'FILLING' | 'DIFF_VIEW' | 'OTP_PAUSED' | 'SUBMITTED'
  const [workflowState, setWorkflowState] = useState<
    "PROFILE" | "FILLING" | "DIFF_VIEW" | "OTP_PAUSED" | "SUBMITTED"
  >("PROFILE");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Session Data
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [diffData, setDiffData] = useState<StartFillResult | null>(null);
  const [otpData, setOtpData] = useState<ApproveDiffResult | null>(null);
  const [submitData, setSubmitData] = useState<SubmitResult | null>(null);

  // OTP & Consent Form State
  const [otpInput, setOtpInput] = useState("123456");
  const [explicitConsent, setExplicitConsent] = useState(false);
  const [showFullAuditLog, setShowFullAuditLog] = useState(false);
  const [activeScreenshotTab, setActiveScreenshotTab] = useState<"after" | "before">("after");

  // Step 1: Start Fill via Playwright
  const handleStartFill = async () => {
    setLoading(true);
    setError(null);
    setWorkflowState("FILLING");

    try {
      const resp = await fetch("http://localhost:8000/agent/start-fill", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profile: profile,
          portal_url: "http://localhost:4000",
        }),
      });

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({}));
        throw new Error(errJson.detail || `Fill failed with HTTP ${resp.status}`);
      }

      const data: StartFillResult = await resp.json();
      setSessionId(data.session_id);
      setDiffData(data);
      setWorkflowState("DIFF_VIEW");
    } catch (err: any) {
      setError(err.message || "Automation failed to populate form.");
      setWorkflowState("PROFILE");
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Approve Diff and Proceed to OTP
  const handleApproveDiff = async () => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);

    try {
      const resp = await fetch("http://localhost:8000/agent/approve-diff", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({}));
        throw new Error(errJson.detail || `Approval failed with HTTP ${resp.status}`);
      }

      const data: ApproveDiffResult = await resp.json();
      setOtpData(data);
      setWorkflowState("OTP_PAUSED");
    } catch (err: any) {
      setError(err.message || "Failed to transition to OTP screen.");
    } finally {
      setLoading(false);
    }
  };

  // Step 3: Final Submit with Explicit Consent
  const handleSubmitWithConsent = async () => {
    if (!sessionId) return;

    if (!explicitConsent) {
      setError(
        locale === "hi"
          ? "स्पष्ट नागरिक सहमति अनिवार्य है। बिना सहमति के आवेदन जमा नहीं किया जा सकता।"
          : "Explicit citizen consent is legally mandatory. Cannot submit without consent."
      );
      return;
    }

    if (!otpInput || otpInput.trim().length < 6) {
      setError(locale === "hi" ? "कृपया 6 अंकों का ओटीपी दर्ज करें।" : "Please enter a valid 6-digit OTP.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const resp = await fetch("http://localhost:8000/agent/submit-with-consent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          otp: otpInput.trim(),
          explicit_consent: explicitConsent,
        }),
      });

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({}));
        throw new Error(errJson.detail || `Submission failed with HTTP ${resp.status}`);
      }

      const data: SubmitResult = await resp.json();
      setSubmitData(data);
      setWorkflowState("SUBMITTED");
    } catch (err: any) {
      setError(err.message || "Application submission failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setWorkflowState("PROFILE");
    setSessionId(null);
    setDiffData(null);
    setOtpData(null);
    setSubmitData(null);
    setExplicitConsent(false);
    setError(null);
  };

  const downloadAuditLog = () => {
    if (!submitData?.audit_log) return;
    const blob = new Blob([JSON.stringify(submitData.audit_log, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `PMKISAN_Audit_${submitData.registration_number}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Workflow Progress Stepper */}
      <div className="bg-white rounded-2xl p-4 border border-gray-200 shadow-2xs">
        <div className="flex items-center justify-between text-xs font-bold text-gray-500 overflow-x-auto gap-2">
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg whitespace-nowrap ${
              workflowState === "PROFILE" || workflowState === "FILLING"
                ? "bg-blue-50 text-blue-700 border border-blue-200"
                : "text-emerald-700 bg-emerald-50"
            }`}
          >
            <span>1.</span>
            <span>{locale === "hi" ? "सत्यापित प्रोफाइल" : "Verified Profile"}</span>
          </div>

          <span>➔</span>

          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg whitespace-nowrap ${
              workflowState === "DIFF_VIEW"
                ? "bg-blue-50 text-blue-700 border border-blue-200"
                : workflowState === "OTP_PAUSED" || workflowState === "SUBMITTED"
                ? "text-emerald-700 bg-emerald-50"
                : "text-gray-400"
            }`}
          >
            <span>2.</span>
            <span>{locale === "hi" ? "डिफ निरीक्षण व अनुमोदन" : "Diff Inspection & Approval"}</span>
          </div>

          <span>➔</span>

          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg whitespace-nowrap ${
              workflowState === "OTP_PAUSED"
                ? "bg-blue-50 text-blue-700 border border-blue-200"
                : workflowState === "SUBMITTED"
                ? "text-emerald-700 bg-emerald-50"
                : "text-gray-400"
            }`}
          >
            <span>3.</span>
            <span>{locale === "hi" ? "आधार ओटीपी व सहमति" : "Aadhaar OTP & Consent"}</span>
          </div>

          <span>➔</span>

          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg whitespace-nowrap ${
              workflowState === "SUBMITTED"
                ? "bg-emerald-600 text-white shadow-xs"
                : "text-gray-400"
            }`}
          >
            <span>4.</span>
            <span>{locale === "hi" ? "पंजीकरण व ऑडिट लॉग" : "Submission & Audit Log"}</span>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl font-medium">
          {error}
        </div>
      )}

      {/* STEP 1: VERIFIED CITIZEN PROFILE REVIEW */}
      {workflowState === "PROFILE" && (
        <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-xs space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-700 flex items-center justify-center text-xl font-bold border border-blue-200">
                🤖
              </div>
              <div>
                <h2 className="text-base sm:text-lg font-bold text-gray-900">
                  {locale === "hi"
                    ? "प्लेराइट ऑटोमेशन एजेंट: नया किसान पंजीकरण"
                    : "Playwright Agent: PM-KISAN Form Automation"}
                </h2>
                <p className="text-xs text-gray-500">
                  {locale === "hi"
                    ? "सत्यापित प्रोफाइल से पोर्टल फॉर्म को सुरक्षित रूप से भरें। प्रत्येक चरण पर मानव-सत्यापन और स्पष्ट सहमति अनिवार्य है।"
                    : "Fills the PM-KISAN portal form with verified citizen data, enforces before/after diff review, pauses at OTP, and requires explicit consent."}
                </p>
              </div>
            </div>

            <span className="hidden sm:inline-block px-3 py-1 bg-green-50 text-green-800 text-xs font-bold rounded-full border border-green-200">
              {locale === "hi" ? "सत्यापित प्रोफाइल तैयार" : "Verified Profile Ready"}
            </span>
          </div>

          {/* Profile Details Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-4 bg-slate-50 border border-slate-200 rounded-xl text-xs">
            <div>
              <span className="text-gray-400 block font-semibold">Farmer Name:</span>
              <span className="font-bold text-gray-900">{profile.farmer_name}</span>
            </div>
            <div>
              <span className="text-gray-400 block font-semibold">Aadhaar (Masked):</span>
              <span className="font-mono font-bold text-gray-900">XXXX-XXXX-1098</span>
            </div>
            <div>
              <span className="text-gray-400 block font-semibold">Mobile:</span>
              <span className="font-bold text-gray-900">{profile.mobile_number}</span>
            </div>
            <div>
              <span className="text-gray-400 block font-semibold">State / District:</span>
              <span className="font-bold text-gray-900">
                {profile.state}, {profile.district}
              </span>
            </div>
            <div>
              <span className="text-gray-400 block font-semibold">Village / Khasra:</span>
              <span className="font-bold text-gray-900">
                {profile.village} (Plot: {profile.khasra_number})
              </span>
            </div>
            <div>
              <span className="text-gray-400 block font-semibold">Cultivable Area:</span>
              <span className="font-bold text-gray-900">{profile.land_area_ha} Hectares</span>
            </div>
            <div>
              <span className="text-gray-400 block font-semibold">Bank Name:</span>
              <span className="font-bold text-gray-900">{profile.bank_name}</span>
            </div>
            <div>
              <span className="text-gray-400 block font-semibold">IFSC Code:</span>
              <span className="font-mono font-bold text-gray-900">{profile.ifsc_code}</span>
            </div>
            <div>
              <span className="text-gray-400 block font-semibold">Account Number:</span>
              <span className="font-mono font-bold text-gray-900">{profile.account_number}</span>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <div className="text-xs text-gray-500">
              Target Portal:{" "}
              <a
                href="http://localhost:4000"
                target="_blank"
                rel="noreferrer"
                className="text-blue-600 hover:underline font-semibold"
              >
                http://localhost:4000 (PM-KISAN Mirror Sandbox)
              </a>
            </div>

            <button
              type="button"
              onClick={handleStartFill}
              disabled={loading}
              className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-bold rounded-xl text-xs sm:text-sm transition shadow-sm flex items-center gap-2"
            >
              <span>🚀</span>
              <span>
                {locale === "hi"
                  ? "स्वचालित फॉर्म भरना शुरू करें"
                  : "Launch Agent & Fill Form"}
              </span>
            </button>
          </div>
        </div>
      )}

      {/* LOADING STATE */}
      {workflowState === "FILLING" && (
        <div className="bg-white rounded-2xl p-10 border border-gray-200 text-center space-y-4">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
          <h3 className="text-sm sm:text-base font-bold text-gray-900">
            {locale === "hi"
              ? "प्लेराइट एजेंट पोर्टल फॉर्म भर रहा है..."
              : "Playwright Agent Navigating & Populating PM-KISAN Form..."}
          </h3>
          <p className="text-xs text-gray-500 max-w-md mx-auto">
            {locale === "hi"
              ? "ब्राउज़र खोलकर फ़ील्ड्स भरे जा रहे हैं तथा पहले और बाद के स्क्रीनशॉट लिए जा रहे हैं..."
              : "Connecting to portal sandbox, taking blank baseline screenshot, entering 15 verified citizen fields, and computing live diffs..."}
          </p>
        </div>
      )}

      {/* STEP 2: DIFF INSPECTION & HUMAN-IN-THE-LOOP APPROVAL */}
      {workflowState === "DIFF_VIEW" && diffData && (
        <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-gray-100">
            <div>
              <h3 className="text-base font-bold text-gray-900">
                {locale === "hi"
                  ? "चरण 2: फ़ील्ड डिफ़ (Before / After) का निरीक्षण करें"
                  : "Step 2: Inspect Before / After Field Differences"}
              </h3>
              <p className="text-xs text-gray-500">
                {locale === "hi"
                  ? "एजेंट ने फॉर्म भर दिया है। कृपया मानों की पुष्टि करें और ओटीपी चरण पर जाने हेतु अनुमोदन दें।"
                  : "Agent populated 15 fields. Carefully review values before approving progression to the OTP gateway."}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-amber-700 bg-amber-50 px-3 py-1 rounded-full border border-amber-200">
                Pending Citizen Approval
              </span>
            </div>
          </div>

          {/* Screenshots Viewer */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-gray-700 flex items-center gap-1.5">
                <span>📸</span>
                <span>Portal Visual Screenshots:</span>
              </span>

              <div className="inline-flex p-1 bg-gray-100 rounded-lg text-xs font-bold">
                <button
                  type="button"
                  onClick={() => setActiveScreenshotTab("after")}
                  className={`px-3 py-1 rounded-md transition ${
                    activeScreenshotTab === "after"
                      ? "bg-white text-blue-700 shadow-2xs"
                      : "text-gray-500"
                  }`}
                >
                  After Fill (Populated)
                </button>
                <button
                  type="button"
                  onClick={() => setActiveScreenshotTab("before")}
                  className={`px-3 py-1 rounded-md transition ${
                    activeScreenshotTab === "before"
                      ? "bg-white text-blue-700 shadow-2xs"
                      : "text-gray-500"
                  }`}
                >
                  Before Fill (Blank)
                </button>
              </div>
            </div>

            <div className="border border-gray-200 rounded-xl overflow-hidden bg-slate-900 shadow-inner max-h-80 overflow-y-auto">
              <img
                src={
                  activeScreenshotTab === "after"
                    ? diffData.after_screenshot
                    : diffData.before_screenshot
                }
                alt="Portal screenshot diff"
                className="w-full object-cover"
              />
            </div>
          </div>

          {/* Diffs Table */}
          <div>
            <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">
              Field Comparison Table ({diffData.diffs.length} fields)
            </h4>
            <div className="border border-gray-200 rounded-xl overflow-hidden overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-gray-50 border-b border-gray-200 text-gray-600 font-bold uppercase text-[11px]">
                  <tr>
                    <th className="p-3">Field Label</th>
                    <th className="p-3">Baseline (Before)</th>
                    <th className="p-3">Populated by Agent (After)</th>
                    <th className="p-3 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {diffData.diffs.map((d, i) => (
                    <tr key={i} className="hover:bg-slate-50 transition">
                      <td className="p-3 font-semibold text-gray-900">{d.label}</td>
                      <td className="p-3 text-gray-400 font-mono italic">
                        {d.before_value || "(empty)"}
                      </td>
                      <td className="p-3 font-mono font-bold text-emerald-800 bg-emerald-50/40">
                        {d.after_value}
                      </td>
                      <td className="p-3 text-center">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                          POPULATED
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Approval Controls */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-gray-100">
            <button
              type="button"
              onClick={handleReset}
              className="text-xs text-gray-500 hover:text-gray-800 font-semibold"
            >
              ← Cancel & Edit Profile
            </button>

            <button
              type="button"
              onClick={handleApproveDiff}
              disabled={loading}
              className="w-full sm:w-auto px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300 text-white font-bold rounded-xl text-xs sm:text-sm transition shadow-sm flex items-center justify-center gap-2"
            >
              <span>✓</span>
              <span>
                {locale === "hi"
                  ? "विवरण सही हैं — ओटीपी चरण पर आगे बढ़ें ➔"
                  : "Approve Verified Details & Proceed to OTP ➔"}
              </span>
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: OTP GATEWAY & MANDATORY EXPLICIT CITIZEN CONSENT */}
      {workflowState === "OTP_PAUSED" && otpData && (
        <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm space-y-6">
          <div className="pb-3 border-b border-gray-100">
            <div className="flex items-center gap-2">
              <span className="text-xl">🔐</span>
              <h3 className="text-base font-bold text-gray-900">
                {locale === "hi"
                  ? "चरण 3: आधार ओटीपी सत्यापन व स्पष्ट सहमति"
                  : "Step 3: Aadhaar OTP Verification & Explicit Consent"}
              </h3>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {locale === "hi"
                ? "एजेंट ओटीपी स्क्रीन पर रुका हुआ है। आधार-लिंक्ड मोबाइल पर भेजा गया ओटीपी दर्ज करें और अपनी स्पष्ट सहमति दें।"
                : "The Playwright agent has paused execution at the portal's Aadhaar 2FA gateway. Enter OTP and sign explicit consent."}
            </p>
          </div>

          {/* OTP Screen Capture */}
          <div>
            <span className="text-xs font-bold text-gray-700 block mb-2">
              Live Portal Screen (Paused at OTP):
            </span>
            <div className="border border-gray-200 rounded-xl overflow-hidden bg-slate-900 shadow-inner max-h-72 overflow-y-auto">
              <img
                src={otpData.otp_screenshot}
                alt="OTP Screen"
                className="w-full object-cover"
              />
            </div>
          </div>

          {/* OTP Input Form */}
          <div className="max-w-md mx-auto p-5 bg-slate-50 border border-slate-200 rounded-2xl space-y-4">
            <div className="text-center">
              <label className="block text-xs font-bold text-gray-800 mb-1">
                {locale === "hi"
                  ? "आधार से जुड़े मोबाइल पर प्राप्त 6-अंकों का ओटीपी दर्ज करें:"
                  : "Enter 6-Digit OTP Dispatched to Linked Mobile (XXXX-XXXX-1098):"}
              </label>
              <input
                type="text"
                maxLength={6}
                value={otpInput}
                onChange={(e) => setOtpInput(e.target.value.replace(/\D/g, ""))}
                placeholder="123456"
                className="w-48 mx-auto text-center font-mono font-black text-2xl tracking-widest p-2 border-2 border-blue-500 rounded-xl bg-white shadow-xs focus:ring-4 focus:ring-blue-100 outline-none"
              />
              <span className="block text-[11px] text-gray-400 mt-1">
                (Default sandbox mock OTP: <strong>123456</strong>)
              </span>
            </div>

            {/* MANDATORY CITIZEN CONSENT CHECKBOX */}
            <div
              className={`p-4 rounded-xl border transition ${
                explicitConsent
                  ? "bg-emerald-50/70 border-emerald-300"
                  : "bg-red-50/40 border-red-200"
              }`}
            >
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={explicitConsent}
                  onChange={(e) => setExplicitConsent(e.target.checked)}
                  className="mt-1 w-4 h-4 text-emerald-600 rounded-md focus:ring-emerald-500 cursor-pointer"
                />
                <span className="text-xs text-gray-800 leading-relaxed">
                  <strong className="text-gray-900">
                    {locale === "hi" ? "स्पष्ट नागरिक सहमति (Mandatory):" : "Explicit Citizen Consent (Mandatory):"}
                  </strong>{" "}
                  {locale === "hi"
                    ? "मैं इसके द्वारा अपने सत्यापित विवरण के साथ मेरी ओर से यह पीएम-किसान पंजीकरण आवेदन जमा करने की स्पष्ट और सूचित सहमति देता/देती हूँ। मैं पुष्टि करता हूँ कि मेरे द्वारा दी गई भूमि और बैंक विवरण सत्य हैं।"
                    : "I hereby give my explicit and informed consent to submit this PM-KISAN registration application on my behalf with the verified details provided. I declare that all landholding and banking particulars are accurate."}
                </span>
              </label>

              {!explicitConsent && (
                <div className="mt-2 text-[11px] text-red-600 font-bold flex items-center gap-1.5">
                  <span>⛔</span>
                  <span>
                    {locale === "hi"
                      ? "सहमति अनिवार्य है। बिना सहमति के एजेंट फॉर्म कभी जमा नहीं करेगा।"
                      : "Strict safety control: Agent will never submit application without explicit consent."}
                  </span>
                </div>
              )}
            </div>

            <button
              type="button"
              onClick={handleSubmitWithConsent}
              disabled={loading || !explicitConsent || otpInput.length < 6}
              className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-bold rounded-xl text-sm transition shadow-sm flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <span className="animate-spin">⏳</span>
                  <span>
                    {locale === "hi" ? "आवेदन जमा हो रहा है..." : "Submitting Application..."}
                  </span>
                </>
              ) : (
                <>
                  <span>✓</span>
                  <span>
                    {locale === "hi"
                      ? "ओटीपी सत्यापित करें व आवेदन जमा करें"
                      : "Verify OTP & Submit Application ✓"}
                  </span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* STEP 4: SUBMITTED CONFIRMATION & AUDIT LOG */}
      {workflowState === "SUBMITTED" && submitData && (
        <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm space-y-6">
          <div className="text-center py-4 space-y-3">
            <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-3xl font-black mx-auto">
              ✓
            </div>
            <h2 className="text-xl font-black text-gray-900">
              {locale === "hi"
                ? "पीएम-किसान पंजीकरण सफलतापूर्वक जमा हुआ"
                : "PM-KISAN Registration Successfully Submitted"}
            </h2>
            <p className="text-xs text-gray-500">
              {locale === "hi"
                ? "आवेदन राज्य कृषि विभाग पोर्टल पर विधिवत दर्ज हो चुका है।"
                : "Application recorded on State Agriculture DBT database with cryptographic non-repudiation audit trail."}
            </p>

            <div className="inline-block p-3 bg-blue-50 border-2 border-blue-500 rounded-2xl">
              <span className="text-[11px] font-bold text-blue-700 uppercase tracking-widest block">
                Application Reference Number
              </span>
              <span className="text-lg sm:text-xl font-mono font-black text-blue-900">
                {submitData.registration_number}
              </span>
            </div>
          </div>

          {/* Official Acknowledgement Screenshot */}
          <div>
            <span className="text-xs font-bold text-gray-700 block mb-2">
              Official Portal Acknowledgement Screenshot:
            </span>
            <div className="border border-gray-200 rounded-xl overflow-hidden bg-slate-900 shadow-inner max-h-72 overflow-y-auto">
              <img
                src={submitData.submitted_screenshot}
                alt="Submission Acknowledgement"
                className="w-full object-cover"
              />
            </div>
          </div>

          {/* Audit Trail Summary Card */}
          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span>🛡️</span>
                <span className="text-xs font-bold text-gray-900 uppercase tracking-wider">
                  Cryptographic Audit Log (JSON)
                </span>
              </div>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-100 text-emerald-800">
                SHA-256 Verified
              </span>
            </div>

            <div className="text-xs text-gray-600 space-y-1">
              <div>
                <strong>Session ID:</strong>{" "}
                <span className="font-mono">{submitData.session_id}</span>
              </div>
              <div>
                <strong>Timestamp:</strong>{" "}
                <span className="font-mono">
                  {submitData.audit_log?.timestamps?.application_submitted}
                </span>
              </div>
              <div>
                <strong>Explicit Consent Granted:</strong>{" "}
                <span className="text-emerald-700 font-bold">YES (Recorded in audit trail)</span>
              </div>
              <div>
                <strong>Tamper-Evident SHA-256:</strong>{" "}
                <span className="font-mono text-[10px] text-gray-500 block truncate">
                  {submitData.audit_log?.tamper_evident_sha256}
                </span>
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowFullAuditLog(!showFullAuditLog)}
                className="px-3 py-1.5 bg-gray-200 hover:bg-gray-300 text-gray-800 rounded-lg text-xs font-bold transition"
              >
                {showFullAuditLog ? "Hide Full JSON" : "View Full JSON"}
              </button>

              <button
                type="button"
                onClick={downloadAuditLog}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition flex items-center gap-1.5 shadow-2xs"
              >
                <span>💾</span>
                <span>Download Audit Receipt</span>
              </button>
            </div>

            {showFullAuditLog && (
              <pre className="mt-3 p-3 bg-slate-900 text-emerald-400 font-mono text-[11px] rounded-xl overflow-x-auto max-h-60">
                {JSON.stringify(submitData.audit_log, null, 2)}
              </pre>
            )}
          </div>

          <div className="text-center pt-2">
            <button
              type="button"
              onClick={handleReset}
              className="px-6 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold rounded-xl text-xs transition"
            >
              Start New Registration
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
