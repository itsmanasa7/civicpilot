"use client";

import { useState, useEffect, useRef } from "react";
import { Locale, t } from "@/lib/i18n";
import VoiceRecorder, { playSpokenResponse } from "./VoiceRecorder";
import {
  MessageSquareIcon,
  SlidersIcon,
  SendIcon,
  Volume2Icon,
  CheckCircle2Icon,
  XCircleIcon,
  AlertTriangleIcon,
  RefreshCwIcon,
  SparklesIcon,
} from "./icons";

interface ChatMessage {
  sender: "assistant" | "user";
  text: string;
}

interface RuleResult {
  rule_id: string;
  name: string;
  clause_id: string;
  rule_version: string;
  reason?: string;
  citation?: string;
}

interface CitationItem {
  id: string;
  text: string;
}

interface VerdictResult {
  verdict: "ELIGIBLE" | "INELIGIBLE" | "INCOMPLETE";
  failed_rules: RuleResult[];
  passed_rules: RuleResult[];
  missing_inputs: string[];
  citations: CitationItem[];
}

interface WhatIfDiff {
  original_verdict: string;
  new_verdict: string;
  verdict_changed: boolean;
  fixed_rules: string[];
  newly_failed_rules: string[];
}

interface Props {
  locale: Locale;
}

export default function InterviewChat({ locale }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [profile, setProfile] = useState<Record<string, any>>({});
  const [currentField, setCurrentField] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [verdict, setVerdict] = useState<VerdictResult | null>(null);

  // What-If state
  const [whatifProfile, setWhatifProfile] = useState<Record<string, any>>({});
  const [whatifDiff, setWhatifDiff] = useState<WhatIfDiff | null>(null);
  const [whatifLoading, setWhatifLoading] = useState(false);
  const [expandedCitations, setExpandedCitations] = useState<Record<string, boolean>>({});

  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Start interview on mount or language switch
  useEffect(() => {
    startInterview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locale]);

  const startInterview = async () => {
    setLoading(true);
    setProfile({});
    setCurrentField(null);
    setIsComplete(false);
    setVerdict(null);
    setWhatifDiff(null);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const res = await fetch(`${API_URL}/interview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: "", profile: {}, current_field: null, lang: locale }),
      });

      if (res.ok) {
        const data = await res.json();
        setMessages([{ sender: "assistant", text: data.assistant_message }]);
        setCurrentField(data.current_field);
        setProfile(data.extracted_profile);
      }
    } catch {
      const welcomeByLang: Record<string, string> = {
        en: "Welcome! Does your family own cultivable agricultural land in your name?",
        hi: "नमस्ते! क्या आप या आपके परिवार के नाम पर खेती योग्य कृषि भूमि है?",
        pa: "ਜੀ ਆਇਆਂ ਨੂੰ! ਕੀ ਤੁਹਾਡੇ ਜਾਂ ਤੁਹਾਡੇ ਪਰਿਵਾਰ ਦੇ ਨਾਮ 'ਤੇ ਖੇਤੀ ਯੋਗ ਜ਼ਮੀਨ ਹੈ?",
        mr: "नमस्कार! तुमच्या किंवा तुमच्या कुटुंबाच्या नावावर शेतीयोग्य जमीन आहे का?",
        te: "నమస్కారం! మీ లేదా మీ కుటుంబం పేరు మీద సాగు చేయదగిన వ్యవసాయ భూమి ఉందా?",
        ta: "வணக்கம்! உங்கள் அல்லது உங்கள் குடும்பத்தின் பெயரில் சாகுபடி நிலம் உள்ளதா?",
        bn: "নমস্কার! আপনার বা আপনার পরিবারের নামে কি চাষযোগ্য কৃষিজমি আছে?",
        gu: "નમસ્તે! શું તમારા અથવા તમારા પરિવારના નામે ખેતીલાયક જમીન છે?",
        kn: "ನಮಸ್ಕಾರ! ನಿಮ್ಮ ಅಥವಾ ನಿಮ್ಮ ಕುಟುಂಬದ ಹೆಸರಿನಲ್ಲಿ ಕೃಷಿ ಯೋಗ್ಯ ಜಮೀನು ಇದೆಯೇ?",
      };
      setMessages([
        {
          sender: "assistant",
          text: welcomeByLang[locale] || welcomeByLang["en"],
        },
      ]);
      setCurrentField("owns_cultivable_land");
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend ?? inputText).trim();
    if (!text || loading) return;

    // Add user message to UI
    const newMessages: ChatMessage[] = [...messages, { sender: "user", text }];
    setMessages(newMessages);
    setInputText("");
    setLoading(true);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const res = await fetch(`${API_URL}/interview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          profile,
          current_field: currentField,
          lang: locale,
        }),
      });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }

      const data = await res.json();
      setProfile(data.extracted_profile);
      setCurrentField(data.current_field);

      setMessages((prev) => [...prev, { sender: "assistant", text: data.assistant_message }]);

      if (data.is_complete && data.verdict_result) {
        setIsComplete(true);
        setVerdict(data.verdict_result);
        setWhatifProfile(data.extracted_profile);
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          sender: "assistant",
          text: "Error connecting to interview engine. Please retry.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Run What-If simulation
  const handleWhatIfChange = async (key: string, value: any) => {
    const updated = { ...whatifProfile, [key]: value };
    setWhatifProfile(updated);
    setWhatifLoading(true);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const res = await fetch(`${API_URL}/whatif`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profile: profile,
          changes: { [key]: value },
        }),
      });

      if (res.ok) {
        const diff: WhatIfDiff = await res.json();
        setWhatifDiff(diff);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setWhatifLoading(false);
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="glass-panel rounded-3xl p-6 sm:p-7 border border-emerald-500/20 shadow-md text-center">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-500 text-white shadow-md shadow-emerald-900/20 mb-3">
          <MessageSquareIcon className="w-6 h-6" />
        </div>
        <h2 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">{t(locale, "interview_title")}</h2>
        <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-lg mx-auto">{t(locale, "interview_subtitle")}</p>
      </div>

      {/* Conversational Chat Window */}
      <div className="glass-panel rounded-3xl border border-emerald-500/20 overflow-hidden flex flex-col h-[500px] shadow-lg">
        {/* Chat Feed */}
        <div className="flex-1 p-4 sm:p-6 overflow-y-auto space-y-4 bg-emerald-50/20">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex items-start gap-3 ${
                m.sender === "user" ? "flex-row-reverse" : "flex-row"
              }`}
            >
              <div
                className={`w-8 h-8 rounded-2xl flex items-center justify-center text-[11px] font-black shrink-0 shadow-xs ${
                  m.sender === "user"
                    ? "bg-slate-800 text-white"
                    : "bg-gradient-to-tr from-emerald-600 to-teal-500 text-white border border-emerald-400/40"
                }`}
              >
                {m.sender === "user" ? "YOU" : "AGY"}
              </div>

              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 text-xs sm:text-sm leading-relaxed shadow-xs ${
                  m.sender === "user"
                    ? "bg-gradient-to-r from-emerald-600 to-teal-700 text-white rounded-tr-xs"
                    : "glass-card text-slate-800 border border-emerald-500/15 rounded-tl-xs"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <span>{m.text}</span>
                  {m.sender === "assistant" && (
                    <button
                      type="button"
                      onClick={() => playSpokenResponse(m.text, locale)}
                      className="p-1 rounded-lg hover:bg-emerald-100 text-emerald-700 shrink-0 transition"
                      title={locale === "hi" ? "उत्तर सुनें" : "Listen to response"}
                    >
                      <Volume2Icon className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex items-center gap-2 text-emerald-600 text-xs py-2 px-2">
              <div className="w-2 h-2 rounded-full bg-emerald-600 animate-bounce"></div>
              <div className="w-2 h-2 rounded-full bg-emerald-600 animate-bounce delay-100"></div>
              <div className="w-2 h-2 rounded-full bg-emerald-600 animate-bounce delay-200"></div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Quick Answer Chips (Yes / No / 1.5 ha) */}
        {!isComplete && (
          <div className="px-4 py-2 border-t border-emerald-500/10 bg-white/70 backdrop-blur-md flex flex-wrap gap-2">
            <span className="text-[11px] font-bold text-slate-400 self-center">Quick:</span>
            <button
              type="button"
              onClick={() => handleSendMessage(
                {
                  en: "Yes",
                  hi: "हाँ",
                  pa: "ਹਾਂ",
                  mr: "होय",
                  te: "అవును",
                  ta: "ஆம்",
                  bn: "হ্যাঁ",
                  gu: "હા",
                  kn: "ಹೌದು",
                }[locale] || "Yes"
              )}
              className="text-xs font-semibold px-3 py-1 bg-emerald-100 text-emerald-800 hover:bg-emerald-200 rounded-full transition shadow-2xs"
            >
              {{
                en: "Yes",
                hi: "हाँ (Yes)",
                pa: "ਹਾਂ (Yes)",
                mr: "होय (Yes)",
                te: "అవును (Yes)",
                ta: "ஆம் (Yes)",
                bn: "হ্যাঁ (Yes)",
                gu: "હા (Yes)",
                kn: "ಹೌದು (Yes)",
              }[locale] || "Yes"}
            </button>
            <button
              type="button"
              onClick={() => handleSendMessage(
                {
                  en: "No",
                  hi: "नहीं",
                  pa: "ਨਹੀਂ",
                  mr: "नाही",
                  te: "కాదు",
                  ta: "இல்லை",
                  bn: "না",
                  gu: "ના",
                  kn: "ಇಲ್ಲ",
                }[locale] || "No"
              )}
              className="text-xs font-semibold px-3 py-1 bg-rose-100 text-rose-800 hover:bg-rose-200 rounded-full transition shadow-2xs"
            >
              {{
                en: "No",
                hi: "नहीं (No)",
                pa: "ਨਹੀਂ (No)",
                mr: "नाही (No)",
                te: "కాదు (No)",
                ta: "இல்லை (No)",
                bn: "না (No)",
                gu: "ના (No)",
                kn: "ಇಲ್ಲ (No)",
              }[locale] || "No"}
            </button>
            <button
              type="button"
              onClick={() => handleSendMessage("1.5 hectares")}
              className="text-xs font-semibold px-3 py-1 bg-slate-100 text-slate-700 hover:bg-slate-200 rounded-full transition shadow-2xs"
            >
              1.5 ha
            </button>
            <button
              type="button"
              onClick={() => handleSendMessage("0")}
              className="text-xs font-semibold px-3 py-1 bg-slate-100 text-slate-700 hover:bg-slate-200 rounded-full transition shadow-2xs"
            >
              0 (None)
            </button>
          </div>
        )}

        {/* Input Bar */}
        <div className="p-3 bg-white/90 backdrop-blur-md border-t border-emerald-500/10 flex items-center gap-2">
          <VoiceRecorder
            locale={locale}
            onTranscription={(text) => handleSendMessage(text)}
            disabled={isComplete || loading}
          />
          <input
            type="text"
            value={inputText}
            disabled={isComplete || loading}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
            placeholder={
              isComplete
                ? "Interview completed! See verdict card below."
                : t(locale, "interview_input_placeholder")
            }
            className="flex-1 px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white transition"
          />
          <button
            onClick={() => handleSendMessage()}
            disabled={isComplete || loading || !inputText.trim()}
            className="px-5 py-2.5 bg-gradient-to-r from-emerald-600 via-emerald-700 to-teal-700 hover:from-emerald-700 hover:to-teal-800 disabled:opacity-40 text-white font-bold text-xs sm:text-sm rounded-xl transition flex items-center gap-1.5 shadow-sm"
          >
            <SendIcon className="w-3.5 h-3.5" />
            <span>{t(locale, "interview_send")}</span>
          </button>
        </div>
      </div>

      {/* VERDICT CARD (Deterministic Rule Engine Output) */}
      {verdict && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-200">
          <div className="glass-panel rounded-3xl p-6 sm:p-7 border border-emerald-500/20 shadow-lg space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-emerald-500/10 pb-4">
              <div>
                <h3 className="text-lg font-black text-slate-900 tracking-tight">{t(locale, "verdict_title")}</h3>
                <p className="text-xs text-slate-500">Evaluated deterministically from YAML scheme rules (No LLM bias)</p>
              </div>

              <div>
                <span
                  className={`inline-flex items-center px-4 py-1.5 rounded-full text-xs sm:text-sm font-black tracking-wide ${
                    verdict.verdict === "ELIGIBLE"
                      ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                      : "bg-rose-100 text-rose-800 border border-rose-300"
                  }`}
                >
                  {verdict.verdict === "ELIGIBLE" ? (
                    <>
                      <CheckCircle2Icon className="w-4 h-4 mr-1.5 text-emerald-700" />
                      <span>{t(locale, "verdict_eligible")}</span>
                    </>
                  ) : (
                    <>
                      <XCircleIcon className="w-4 h-4 mr-1.5 text-rose-700" />
                      <span>{t(locale, "verdict_ineligible")}</span>
                    </>
                  )}
                </span>
              </div>
            </div>

            {/* Disqualifying Failed Rules */}
            {verdict.failed_rules && verdict.failed_rules.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-rose-600 uppercase tracking-wider flex items-center gap-1.5">
                  <AlertTriangleIcon className="w-4 h-4 text-rose-600" />
                  <span>{t(locale, "failed_rules_title")} ({verdict.failed_rules.length})</span>
                </h4>

                <div className="space-y-2.5">
                  {verdict.failed_rules.map((rule) => (
                    <div
                      key={rule.rule_id}
                      className="p-4 rounded-2xl bg-rose-50/80 border border-rose-200 space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-bold text-rose-950">{rule.name}</span>
                        <span className="px-2 py-0.5 rounded-lg bg-rose-200 text-rose-900 text-xs font-mono font-extrabold">
                          {rule.clause_id}
                        </span>
                      </div>
                      <p className="text-xs text-rose-700 font-medium">{rule.reason}</p>
                      {rule.citation && (
                        <p className="text-[11px] text-slate-500 italic border-t border-rose-100 pt-1 mt-1">
                          Official Citation: &quot;{rule.citation}&quot;
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Passed Rules */}
            {verdict.passed_rules && verdict.passed_rules.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-emerald-800 uppercase tracking-wider flex items-center gap-1.5">
                  <CheckCircle2Icon className="w-4 h-4 text-emerald-600" />
                  <span>{t(locale, "passed_rules_title")} ({verdict.passed_rules.length})</span>
                </h4>
                <div className="flex flex-wrap gap-2">
                  {verdict.passed_rules.map((r) => (
                    <span
                      key={r.rule_id}
                      className="px-2.5 py-1 rounded-xl bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-semibold"
                    >
                      {r.name} ({r.clause_id})
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Reset Interview Button */}
            <div className="pt-2 text-center">
              <button
                onClick={startInterview}
                className="text-xs text-emerald-700 hover:text-emerald-900 font-bold underline flex items-center justify-center gap-1 mx-auto"
              >
                <RefreshCwIcon className="w-3.5 h-3.5" />
                <span>Restart Interview</span>
              </button>
            </div>
          </div>

          {/* WHAT-IF SIMULATION PANEL */}
          <div className="glass-panel rounded-3xl p-6 sm:p-7 border border-emerald-500/20 shadow-lg space-y-6">
            <div className="border-b border-emerald-500/10 pb-3 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <SlidersIcon className="w-4 h-4 text-emerald-600" />
                  <span>{t(locale, "whatif_title")}</span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">{t(locale, "whatif_subtitle")}</p>
              </div>

              {whatifDiff && (
                <div>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-bold ${
                      whatifDiff.new_verdict === "ELIGIBLE"
                        ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                        : "bg-rose-100 text-rose-800 border border-rose-300"
                    }`}
                  >
                    Simulated: {whatifDiff.new_verdict}
                  </span>
                </div>
              )}
            </div>

            {/* What-If Verdict Diff Banner */}
            {whatifDiff && whatifDiff.verdict_changed && (
              <div className="p-4 rounded-2xl bg-amber-50 border border-amber-300 flex items-center justify-between">
                <div>
                  <span className="px-2 py-0.5 rounded-md bg-amber-600 text-white text-xs font-bold mr-2">
                    {t(locale, "verdict_changed_badge")}
                  </span>
                  <span className="text-xs font-semibold text-amber-950">
                    Changed from {whatifDiff.original_verdict} ➔ {whatifDiff.new_verdict}
                  </span>
                </div>
              </div>
            )}

            {whatifDiff && whatifDiff.fixed_rules.length > 0 && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-2xl text-xs text-emerald-800 flex items-center gap-1.5">
                <CheckCircle2Icon className="w-4 h-4 text-emerald-600 shrink-0" />
                <span><strong>{t(locale, "fixed_rules_title")}:</strong> {whatifDiff.fixed_rules.join(", ")}</span>
              </div>
            )}

            {whatifDiff && whatifDiff.newly_failed_rules.length > 0 && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-2xl text-xs text-rose-800 flex items-center gap-1.5">
                <AlertTriangleIcon className="w-4 h-4 text-rose-600 shrink-0" />
                <span><strong>{t(locale, "newly_failed_title")}:</strong> {whatifDiff.newly_failed_rules.join(", ")}</span>
              </div>
            )}

            {/* Sliders & Toggles Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-2">
              {/* Slider 1: Land Area */}
              <div className="space-y-2 p-4 bg-white/70 rounded-2xl border border-slate-200 shadow-2xs">
                <div className="flex justify-between text-xs font-bold text-slate-800">
                  <span>Cultivable Land Area (Hectares)</span>
                  <span className="text-emerald-700 font-mono">{whatifProfile.land_area_hectares ?? 1.0} ha</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="10.0"
                  step="0.1"
                  value={whatifProfile.land_area_hectares ?? 1.0}
                  onChange={(e) => handleWhatIfChange("land_area_hectares", parseFloat(e.target.value))}
                  className="w-full accent-emerald-600 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                  <span>0 ha (Landless)</span>
                  <span>5 ha</span>
                  <span>10 ha</span>
                </div>
              </div>

              {/* Slider 2: Monthly Pension */}
              <div className="space-y-2 p-4 bg-white/70 rounded-2xl border border-slate-200 shadow-2xs">
                <div className="flex justify-between text-xs font-bold text-slate-800">
                  <span>Monthly Pension (Rs.)</span>
                  <span className="text-emerald-700 font-mono">₹{whatifProfile.monthly_pension ?? 0}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="30000"
                  step="1000"
                  value={whatifProfile.monthly_pension ?? 0}
                  onChange={(e) => handleWhatIfChange("monthly_pension", parseFloat(e.target.value))}
                  className="w-full accent-emerald-600 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                  <span>₹0</span>
                  <span className="text-red-500 font-semibold">₹10,000 (Cutoff)</span>
                  <span>₹30,000</span>
                </div>
              </div>

              {/* Toggle 1: Land Record Seeded */}
              <label className="flex items-center justify-between p-3.5 bg-gray-50 rounded-xl border border-gray-200 cursor-pointer hover:bg-gray-100 transition">
                <span className="text-xs font-medium text-gray-800">Land Record Seeded (Bhulekh)</span>
                <input
                  type="checkbox"
                  checked={!!whatifProfile.land_record_seeded}
                  onChange={(e) => handleWhatIfChange("land_record_seeded", e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded-sm cursor-pointer"
                />
              </label>

              {/* Toggle 2: Aadhaar Seeded */}
              <label className="flex items-center justify-between p-3.5 bg-gray-50 rounded-xl border border-gray-200 cursor-pointer hover:bg-gray-100 transition">
                <span className="text-xs font-medium text-gray-800">Aadhaar Linked with Bank</span>
                <input
                  type="checkbox"
                  checked={!!whatifProfile.aadhaar_seeded}
                  onChange={(e) => handleWhatIfChange("aadhaar_seeded", e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded-sm cursor-pointer"
                />
              </label>

              {/* Toggle 3: e-KYC Done */}
              <label className="flex items-center justify-between p-3.5 bg-gray-50 rounded-xl border border-gray-200 cursor-pointer hover:bg-gray-100 transition">
                <span className="text-xs font-medium text-gray-800">Biometric/OTP e-KYC Done</span>
                <input
                  type="checkbox"
                  checked={!!whatifProfile.ekyc_completed}
                  onChange={(e) => handleWhatIfChange("ekyc_completed", e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded-sm cursor-pointer"
                />
              </label>

              {/* Toggle 4: Bank Account DBT Active */}
              <label className="flex items-center justify-between p-3.5 bg-gray-50 rounded-xl border border-gray-200 cursor-pointer hover:bg-gray-100 transition">
                <span className="text-xs font-medium text-gray-800">Bank Account DBT Active</span>
                <input
                  type="checkbox"
                  checked={!!whatifProfile.bank_account_dbt_active}
                  onChange={(e) => handleWhatIfChange("bank_account_dbt_active", e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded-sm cursor-pointer"
                />
              </label>

              {/* Toggle 5: Paid Income Tax */}
              <label className="flex items-center justify-between p-3.5 bg-gray-50 rounded-xl border border-gray-200 cursor-pointer hover:bg-gray-100 transition">
                <span className="text-xs font-medium text-gray-800">Paid Income Tax in Last AY</span>
                <input
                  type="checkbox"
                  checked={!!whatifProfile.paid_income_tax_last_ay}
                  onChange={(e) => handleWhatIfChange("paid_income_tax_last_ay", e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded-sm cursor-pointer"
                />
              </label>

              {/* Toggle 6: Group D / Class IV Employee Exception */}
              <label className="flex items-center justify-between p-3.5 bg-gray-50 rounded-xl border border-gray-200 cursor-pointer hover:bg-gray-100 transition">
                <span className="text-xs font-medium text-gray-800">Class IV / Group D / MTS Exemption</span>
                <input
                  type="checkbox"
                  checked={!!whatifProfile.is_class_iv_or_group_d}
                  onChange={(e) => handleWhatIfChange("is_class_iv_or_group_d", e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded-sm cursor-pointer"
                />
              </label>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
