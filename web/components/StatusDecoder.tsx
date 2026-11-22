"use client";

import React, { useState } from "react";
import { Locale, t } from "@/lib/i18n";
import {
  ActivitySquareIcon,
  CameraIcon,
  SearchIcon,
  CheckCircle2Icon,
  AlertTriangleIcon,
  Building2Icon,
  ChevronDownIcon,
  SparklesIcon,
} from "./icons";

interface DecodeStatusResult {
  matched_cause_id?: string;
  title: string;
  root_cause: string;
  fix_action: string[];
  clause_id?: string;
  clause_text?: string;
  designated_office: string;
  is_known_cause: boolean;
  needs_escalation: boolean;
  confidence: number;
  extracted_status_text: string;
}

interface StatusDecoderProps {
  locale: Locale;
}

export default function StatusDecoder({ locale }: StatusDecoderProps) {
  const [statusText, setStatusText] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [filePreview, setFilePreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DecodeStatusResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showClauseDetails, setShowClauseDetails] = useState(false);

  const presets = [
    {
      label: locale === "hi" ? "ई-केवाईसी लंबित" : "e-KYC Pending",
      text: "Beneficiary Status: e-KYC Pending. Please complete eKYC to receive installments.",
    },
    {
      label: locale === "hi" ? "भूमि सीडिंग लंबित" : "Land Seeding: No",
      text: "Land Seeding: No. Record not verified in State Bhulekh portal.",
    },
    {
      label: locale === "hi" ? "आधार बैंक लिंक नहीं" : "Aadhaar Not Seeded",
      text: "Payment Failed: Aadhaar not seeded with account / NPCI mapping pending in bank.",
    },
    {
      label: locale === "hi" ? "PFMS बैंक अस्वीकृत" : "PFMS Rejected",
      text: "PFMS Status: Account rejected by bank due to invalid IFSC or dormant account.",
    },
    {
      label: locale === "hi" ? "अज्ञात त्रुटि कोड" : "Unknown Error Code",
      text: "ERROR_SYSTEM_EXCEPTION_PAYMENT_NODE_59918_UNRESOLVED",
    },
  ];

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setError(null);
      if (file.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = () => setFilePreview(reader.result as string);
        reader.readAsDataURL(file);
      } else {
        setFilePreview(null);
      }
    }
  };

  const handleDecode = async () => {
    if (!statusText.trim() && !selectedFile) {
      setError(
        locale === "hi"
          ? "कृपया पोर्टल स्थिति संदेश दर्ज करें अथवा फोटो अपलोड करें।"
          : "Please enter portal status text or upload a screenshot."
      );
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

      if (selectedFile) {
        const formData = new FormData();
        formData.append("file", selectedFile);
        if (statusText.trim()) {
          formData.append("status_text", statusText.trim());
        }
        formData.append("lang", locale);

        const resp = await fetch(`${API_URL}/decode-status`, {
          method: "POST",
          body: formData,
        });

        if (!resp.ok) {
          throw new Error(`API error: ${resp.status}`);
        }
        const data = await resp.json();
        setResult(data);
      } else {
        const resp = await fetch(`${API_URL}/decode-status`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status_text: statusText.trim(), lang: locale }),
        });

        if (!resp.ok) {
          throw new Error(`API error: ${resp.status}`);
        }
        const data = await resp.json();
        setResult(data);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to decode status.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Glass Card */}
      <div className="glass-panel rounded-3xl p-6 sm:p-7 border border-emerald-500/20 shadow-md">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-500 text-white flex items-center justify-center shadow-md shadow-emerald-900/20 shrink-0">
            <ActivitySquareIcon className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight">
              {locale === "hi" ? "पोर्टल स्थिति व अस्वीकृति डिकोडर" : "Portal Status & Rejection Decoder"}
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              {locale === "hi"
                ? "पीएम-किसान पोर्टल पर दिखने वाले अस्वीकृति संदेश या स्टेटस को तुरंत डिकोड करें और समाधान जानें।"
                : "Paste or photograph any PM-KISAN portal status or rejection message to diagnose root causes and fixes."}
            </p>
          </div>
        </div>

        {/* Preset Quick Chips */}
        <div className="mt-5 pt-4 border-t border-emerald-500/10">
          <span className="text-[11px] font-bold text-slate-400 block mb-2">
            {locale === "hi" ? "त्वरित उदाहरण (Quick Presets):" : "Try Quick Presets:"}
          </span>
          <div className="flex flex-wrap gap-2">
            {presets.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setStatusText(p.text);
                  setSelectedFile(null);
                  setFilePreview(null);
                }}
                className="text-xs px-3 py-1.5 rounded-xl bg-white/80 hover:bg-emerald-50 text-slate-700 hover:text-emerald-900 font-semibold transition border border-slate-200/80 shadow-2xs"
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Input Area */}
        <div className="mt-5 space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">
              {locale === "hi"
                ? "पोर्टल स्थिति या अस्वीकृति संदेश पेस्ट करें:"
                : "Paste Portal Status or Rejection Message:"}
            </label>
            <textarea
              rows={3}
              value={statusText}
              onChange={(e) => setStatusText(e.target.value)}
              placeholder={
                locale === "hi"
                  ? "उदाहरण: Land Seeding: No अथवा e-KYC Pending..."
                  : "e.g. Beneficiary Status: e-KYC Pending, or Land Seeding: No..."
              }
              className="w-full text-xs sm:text-sm p-3.5 border border-slate-200 rounded-2xl bg-white/80 focus:bg-white focus:ring-2 focus:ring-emerald-500 focus:outline-none transition"
            />
          </div>

          {/* Upload / Camera Section */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
            <label className="flex items-center gap-2 px-4 py-2 bg-white hover:bg-emerald-50 text-slate-700 hover:text-emerald-900 rounded-xl border border-slate-200 text-xs font-bold cursor-pointer transition shadow-2xs">
              <CameraIcon className="w-4 h-4 text-emerald-700" />
              <span>
                {selectedFile
                  ? selectedFile.name
                  : locale === "hi"
                  ? "स्क्रीनशॉट या फोटो अपलोड करें"
                  : "Upload / Photograph Status Screen"}
              </span>
              <input
                type="file"
                accept="image/*,.pdf"
                capture="environment"
                onChange={handleFileChange}
                className="hidden"
              />
            </label>

            {selectedFile && (
              <button
                type="button"
                onClick={() => {
                  setSelectedFile(null);
                  setFilePreview(null);
                }}
                className="text-xs text-rose-600 hover:text-rose-700 font-bold"
              >
                {locale === "hi" ? "हटाएं" : "Clear File"}
              </button>
            )}
          </div>

          {filePreview && (
            <div className="mt-2 p-2 border border-slate-200 rounded-2xl max-w-xs bg-white/70">
              <img
                src={filePreview}
                alt="Status preview"
                className="max-h-40 rounded-xl object-contain mx-auto"
              />
            </div>
          )}

          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl flex items-center gap-2">
              <AlertTriangleIcon className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="pt-2">
            <button
              type="button"
              onClick={handleDecode}
              disabled={loading}
              className="w-full sm:w-auto px-6 py-2.5 bg-gradient-to-r from-emerald-600 via-emerald-700 to-teal-700 hover:from-emerald-700 hover:to-teal-800 disabled:opacity-50 text-white font-bold rounded-xl text-xs sm:text-sm transition shadow-md shadow-emerald-900/20 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>{locale === "hi" ? "विश्लेषण जारी..." : "Decoding Status..."}</span>
                </>
              ) : (
                <>
                  <SearchIcon className="w-4 h-4" />
                  <span>{locale === "hi" ? "डिकोड करें" : "Decode Status"}</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Result Card */}
      {result && (
        <div className="glass-panel rounded-3xl p-6 sm:p-7 border border-emerald-500/20 shadow-lg space-y-5 animate-in fade-in slide-in-from-bottom-2 duration-200">
          {/* Status Badge & Header */}
          <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-emerald-500/10">
            <div className="flex items-center gap-2">
              <span
                className={`px-3 py-1 rounded-full text-xs font-black flex items-center gap-1.5 ${
                  result.is_known_cause
                    ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                    : "bg-amber-100 text-amber-800 border border-amber-300"
                }`}
              >
                {result.is_known_cause ? (
                  <>
                    <CheckCircle2Icon className="w-3.5 h-3.5 text-emerald-700" />
                    <span>
                      {locale === "hi" ? "ज्ञात समस्या (Automated Match)" : "Standard Known Cause"}
                    </span>
                  </>
                ) : (
                  <>
                    <AlertTriangleIcon className="w-3.5 h-3.5 text-amber-700" />
                    <span>
                      {locale === "hi" ? "प्रशासनिक मार्गदर्शन आवश्यक" : "Official Escalation Recommended"}
                    </span>
                  </>
                )}
              </span>

              {result.needs_escalation && (
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-purple-100 text-purple-800 border border-purple-200">
                  {locale === "hi" ? "अधिकारी स्तर की कार्रवाई" : "Requires Official Action"}
                </span>
              )}
            </div>

            <div className="text-xs text-slate-500 font-semibold">
              {locale === "hi" ? "विश्वसनीयता:" : "Confidence:"}{" "}
              <span className="font-bold text-slate-800 font-mono">
                {Math.round(result.confidence * 100)}%
              </span>
            </div>
          </div>

          {/* Title & Root Cause */}
          <div>
            <h3 className="text-base sm:text-lg font-black text-slate-900 mb-1">{result.title}</h3>
            <div className="p-3.5 bg-white/80 border border-slate-200 rounded-2xl text-xs sm:text-sm text-slate-700 leading-relaxed shadow-2xs">
              <strong className="text-slate-900">{locale === "hi" ? "मुख्य कारण:" : "Root Cause:"}</strong>{" "}
              {result.root_cause}
            </div>
          </div>

          {/* Action Steps */}
          <div>
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <SparklesIcon className="w-3.5 h-3.5 text-emerald-600" />
              <span>{locale === "hi" ? "समाधान के चरण (Action Steps):" : "Recommended Resolution Steps:"}</span>
            </h4>
            <div className="space-y-2">
              {result.fix_action.map((step, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-2.5 p-3 bg-emerald-50/70 rounded-2xl border border-emerald-200/80 text-xs text-emerald-950 font-medium"
                >
                  <span className="w-5 h-5 rounded-full bg-emerald-700 text-white flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">
                    {idx + 1}
                  </span>
                  <span>{step}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Designated Office */}
          <div className="p-3.5 bg-amber-50/90 border border-amber-200 rounded-2xl flex items-center gap-3">
            <Building2Icon className="w-6 h-6 text-amber-700 shrink-0" />
            <div>
              <div className="text-[10px] font-bold text-amber-900 uppercase tracking-wide">
                {locale === "hi" ? "संबंधित कार्यालय / पोर्टल" : "Designated Office / Action Portal"}
              </div>
              <div className="text-xs font-bold text-amber-950">{result.designated_office}</div>
            </div>
          </div>

          {/* Clause Citation (Expandable) */}
          {result.clause_id && (
            <div className="pt-2 border-t border-emerald-500/10">
              <button
                type="button"
                onClick={() => setShowClauseDetails(!showClauseDetails)}
                className="w-full flex items-center justify-between p-3 bg-emerald-50/50 hover:bg-emerald-50 rounded-2xl text-xs font-bold text-emerald-900 transition border border-emerald-500/10"
              >
                <div className="flex items-center gap-2">
                  <span>
                    {locale === "hi" ? "आधिकारिक योजना नियम:" : "Official Scheme Guideline Clause:"}{" "}
                    <span className="text-emerald-700 font-mono font-bold">[{result.clause_id}]</span>
                  </span>
                </div>
                <ChevronDownIcon
                  className={`w-4 h-4 text-emerald-700 transition-transform ${
                    showClauseDetails ? "rotate-180" : ""
                  }`}
                />
              </button>

              {showClauseDetails && result.clause_text && (
                <div className="mt-2 p-3.5 bg-white border border-emerald-500/20 rounded-2xl text-xs text-slate-700 whitespace-pre-wrap leading-relaxed font-mono">
                  {result.clause_text}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
