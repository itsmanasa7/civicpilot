"use client";

import { useState } from "react";
import { Locale, t } from "@/lib/i18n";
import VoiceRecorder, { playSpokenResponse } from "./VoiceRecorder";
import {
  HelpCircleIcon,
  Volume2Icon,
  AlertTriangleIcon,
  CheckCircle2Icon,
  ChevronDownIcon,
  SearchIcon,
  SparklesIcon,
} from "./icons";

interface Citation {
  id: string;
  text: string;
}

interface AskResponse {
  answer: string;
  citations: Citation[];
  confidence: number;
  needs_escalation: boolean;
}

interface Props {
  locale: Locale;
}

export default function SchemeQA({ locale }: Props) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedCitations, setExpandedCitations] = useState<Record<string, boolean>>({});

  const sampleQuestions = [
    locale === "hi"
      ? "खंड 4.2 के तहत कौन से किसान पात्र हैं?"
      : "Who is eligible for PM-KISAN benefits under clause 4.2?",
    locale === "hi"
      ? "क्या ई-केवाईसी और आधार सीडिंग अनिवार्य है?"
      : "Is biometric or OTP e-KYC mandatory under amendment 1.1?",
    locale === "hi"
      ? "प्रति वर्ष कितनी किस्तें और कितनी राशि मिलती है?"
      : "What is the financial benefit amount and installment schedule?",
  ];

  const handleAsk = async (qText?: string) => {
    const q = (qText ?? question).trim();
    if (!q) return;

    if (qText) setQuestion(qText);
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const res = await fetch(`${API_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, lang: locale }),
      });

      if (!res.ok) {
        throw new Error(`API returned status ${res.status}`);
      }

      const data: AskResponse = await res.json();
      setResult(data);
      if (data.citations && data.citations.length > 0) {
        setExpandedCitations({ [data.citations[0].id]: true });
      }
    } catch (err: any) {
      setError(err?.message || "Failed to reach API server.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto space-y-6">
      {/* Search & Query Glass Panel */}
      <div className="glass-panel rounded-3xl p-6 sm:p-8 border border-emerald-500/20 shadow-lg">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-500 text-white shadow-md shadow-emerald-900/20 mb-3">
            <HelpCircleIcon className="w-6 h-6" />
          </div>
          <h2 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
            {t(locale, "ask_title")}
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-md mx-auto">
            {t(locale, "ask_subtitle")}
          </p>
        </div>

        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAsk()}
                placeholder={t(locale, "ask_placeholder")}
                className="w-full pl-4 pr-10 py-3 rounded-2xl border border-slate-200 bg-white/80 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 text-xs sm:text-sm text-slate-800 shadow-inner"
              />
              <SearchIcon className="absolute right-3.5 top-3.5 w-4 h-4 text-slate-400 pointer-events-none" />
            </div>

            <div className="flex items-center gap-2">
              <VoiceRecorder
                locale={locale}
                onTranscription={(text) => handleAsk(text)}
                disabled={loading}
              />
              <button
                onClick={() => handleAsk()}
                disabled={loading || !question.trim()}
                className="px-5 py-3 bg-gradient-to-r from-emerald-600 via-emerald-700 to-teal-700 hover:from-emerald-700 hover:to-teal-800 disabled:opacity-50 text-white font-bold text-xs sm:text-sm rounded-2xl transition shadow-md shadow-emerald-900/20 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <span>{t(locale, "ask_button")}</span>
                )}
              </button>
            </div>
          </div>

          {/* Quick Questions Presets */}
          <div className="flex flex-wrap items-center gap-1.5 pt-1">
            <span className="text-[11px] font-bold text-emerald-800/70 mr-1 flex items-center gap-1">
              <SparklesIcon className="w-3 h-3 text-emerald-600" /> Try:
            </span>
            {sampleQuestions.map((sq, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleAsk(sq)}
                className="text-[11px] font-medium bg-emerald-50/80 hover:bg-emerald-100 text-emerald-900 px-3 py-1 rounded-full border border-emerald-200/70 transition truncate max-w-xs shadow-2xs"
              >
                {sq}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="mt-4 p-4 rounded-2xl bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-center gap-2">
            <AlertTriangleIcon className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Answer & Grounded Citations Result */}
      {result && (
        <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-200">
          <div className="glass-panel rounded-3xl p-6 sm:p-7 border border-emerald-500/20 shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-emerald-500/10 pb-3 flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-black text-slate-800 uppercase tracking-wider">
                  Grounded Answer
                </span>
                <button
                  type="button"
                  onClick={() => playSpokenResponse(result.answer, locale)}
                  className="px-2.5 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 font-bold rounded-xl border border-emerald-200 text-xs transition shadow-2xs flex items-center gap-1.5"
                  title="Listen to response (TTS)"
                >
                  <Volume2Icon className="w-3.5 h-3.5 text-emerald-700" />
                  <span>{locale === "hi" ? "सुनें" : "Listen"}</span>
                </button>
              </div>

              <div className="flex items-center gap-2">
                {result.needs_escalation && (
                  <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800 border border-amber-200 flex items-center gap-1">
                    <AlertTriangleIcon className="w-3 h-3 text-amber-700" />
                    <span>{t(locale, "needs_escalation_badge")}</span>
                  </span>
                )}
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                  {Math.round(result.confidence * 100)}% {t(locale, "confidence_score")}
                </span>
              </div>
            </div>

            <p className="text-slate-800 leading-relaxed text-xs sm:text-sm font-medium whitespace-pre-line">
              {result.answer}
            </p>

            {/* Citations Accordion */}
            {result.citations && result.citations.length > 0 && (
              <div className="pt-4 border-t border-emerald-500/10 space-y-2.5">
                <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                  <span>Official Scheme Citations</span>
                </h4>
                {result.citations.map((c) => {
                  const isExpanded = !!expandedCitations[c.id];
                  return (
                    <div
                      key={c.id}
                      className="border border-emerald-500/20 rounded-2xl overflow-hidden bg-white/70 shadow-2xs"
                    >
                      <button
                        onClick={() =>
                          setExpandedCitations((prev) => ({
                            ...prev,
                            [c.id]: !prev[c.id],
                          }))
                        }
                        className="w-full px-3.5 py-2.5 bg-emerald-50/50 hover:bg-emerald-50 flex items-center justify-between text-left text-xs transition"
                      >
                        <span className="font-bold text-emerald-800">[{c.id}]</span>
                        <ChevronDownIcon
                          className={`w-4 h-4 text-emerald-700 transition-transform ${
                            isExpanded ? "rotate-180" : ""
                          }`}
                        />
                      </button>
                      {isExpanded && (
                        <div className="p-3.5 bg-white text-xs text-slate-700 border-t border-emerald-500/10 leading-relaxed font-mono">
                          {c.text}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
