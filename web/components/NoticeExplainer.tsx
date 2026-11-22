"use client";

import { useState, useRef, DragEvent, ChangeEvent } from "react";
import { Locale, t } from "@/lib/i18n";

interface Citation {
  id: string;
  text: string;
}

interface ExplainNoticeResponse {
  extracted_text: string;
  explanation: string;
  citations: Citation[];
  what_you_should_do_next: string[];
  confidence: number;
  is_low_confidence: boolean;
  needs_escalation: boolean;
}

interface Props {
  locale: Locale;
}

export default function NoticeExplainer({ locale }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ExplainNoticeResponse | null>(null);
  const [expandedCitations, setExpandedCitations] = useState<Record<string, boolean>>({});
  const [showRawText, setShowRawText] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);

  const cameraInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSelectFile = (selected: File) => {
    setFile(selected);
    setError(null);
    setResult(null);
    setExpandedCitations({});

    if (selected.type.startsWith("image/")) {
      const url = URL.createObjectURL(selected);
      setPreviewUrl(url);
    } else {
      setPreviewUrl(null);
    }
  };

  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleSelectFile(e.target.files[0]);
    }
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleSelectFile(e.dataTransfer.files[0]);
    }
  };

  const handleRetake = () => {
    setFile(null);
    setPreviewUrl(null);
    setResult(null);
    setError(null);
    if (cameraInputRef.current) {
      cameraInputRef.current.value = "";
      cameraInputRef.current.click();
    }
  };

  const handleSubmit = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setLoadingStep(t(locale, "analyzing"));

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const formData = new FormData();
      formData.append("file", file);
      formData.append("lang", locale);

      setTimeout(() => {
        setLoadingStep(t(locale, "matching_clauses"));
      }, 1500);

      const res = await fetch(`${API_URL}/explain-notice`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`Server returned error: ${res.status}`);
      }

      const data: ExplainNoticeResponse = await res.json();
      setResult(data);

      // Auto-expand first citation if present
      if (data.citations && data.citations.length > 0) {
        setExpandedCitations({ [data.citations[0].id]: true });
      }
    } catch (err: any) {
      setError(err?.message || "Failed to analyze notice. Please verify API is running.");
    } finally {
      setLoading(false);
      setLoadingStep("");
    }
  };

  const toggleCitation = (id: string) => {
    setExpandedCitations((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  return (
    <div className="w-full max-w-2xl mx-auto space-y-6">
      {/* Hidden Native File Inputs for Camera & File Picker */}
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleFileInputChange}
      />
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,application/pdf"
        className="hidden"
        onChange={handleFileInputChange}
      />

      {/* Upload Box / Action Card */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-50 text-blue-600 rounded-xl mb-3">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-gray-900">{t(locale, "notice_title")}</h2>
          <p className="text-sm text-gray-500 mt-1 max-w-md mx-auto">{t(locale, "notice_subtitle")}</p>
        </div>

        {/* Drag & Drop Surface */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors ${
            isDragOver
              ? "border-blue-500 bg-blue-50/50"
              : "border-gray-300 hover:border-gray-400 bg-gray-50/50"
          }`}
        >
          {file ? (
            <div className="flex flex-col items-center space-y-3">
              {previewUrl ? (
                <div className="relative w-36 h-36 rounded-lg overflow-hidden border border-gray-200 shadow-sm">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={previewUrl} alt="Notice Preview" className="w-full h-full object-cover" />
                </div>
              ) : (
                <div className="w-16 h-16 bg-red-50 text-red-600 rounded-xl flex items-center justify-center font-bold text-sm">
                  PDF
                </div>
              )}

              <div>
                <p className="text-sm font-semibold text-gray-800">{file.name}</p>
                <p className="text-xs text-gray-400">{(file.size / 1024).toFixed(1)} KB</p>
              </div>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="text-xs text-blue-600 hover:text-blue-800 font-medium px-2 py-1 bg-white border border-gray-200 rounded-md shadow-2xs"
                >
                  {t(locale, "change_file")}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setFile(null);
                    setPreviewUrl(null);
                    setResult(null);
                  }}
                  className="text-xs text-red-600 hover:text-red-800 font-medium px-2 py-1 bg-white border border-gray-200 rounded-md shadow-2xs"
                >
                  Remove
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex flex-wrap justify-center gap-3">
                {/* Mobile Camera Button */}
                <button
                  type="button"
                  onClick={() => cameraInputRef.current?.click()}
                  className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-xl shadow-xs transition"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
                    />
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"
                    />
                  </svg>
                  {t(locale, "take_photo")}
                </button>

                {/* Upload File Button */}
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="inline-flex items-center gap-2 px-4 py-2.5 bg-white hover:bg-gray-50 text-gray-700 border border-gray-300 text-sm font-medium rounded-xl shadow-2xs transition"
                >
                  <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
                    />
                  </svg>
                  {t(locale, "upload_file")}
                </button>
              </div>

              <p className="text-xs text-gray-400">{t(locale, "drag_drop")}</p>
              <p className="text-2xs text-gray-400">{t(locale, "supported_formats")}</p>
            </div>
          )}
        </div>

        {/* Submit Action Button */}
        {file && !loading && !result && (
          <div className="mt-5">
            <button
              onClick={handleSubmit}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm rounded-xl shadow-xs transition flex items-center justify-center gap-2"
            >
              <span>{t(locale, "explain_button")}</span>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </div>
        )}

        {/* Loading Progress State */}
        {loading && (
          <div className="mt-6 p-6 rounded-xl bg-blue-50 border border-blue-100 text-center space-y-3">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-600 border-t-transparent"></div>
            <p className="text-sm font-medium text-blue-900">{loadingStep || t(locale, "analyzing")}</p>
            <div className="w-48 h-1.5 bg-blue-200 rounded-full mx-auto overflow-hidden">
              <div className="h-full bg-blue-600 rounded-full animate-pulse"></div>
            </div>
          </div>
        )}

        {/* Error Notification */}
        {error && (
          <div className="mt-4 p-4 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700 flex items-start gap-2">
            <span className="text-red-500 font-bold">⚠️</span>
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* RESULT SECTION */}
      {result && (
        <div className="space-y-5 animate-fade-in">
          {/* Low-Confidence Retake Warning Banner */}
          {result.is_low_confidence && (
            <div className="rounded-2xl bg-amber-50 border border-amber-200 p-5 shadow-xs">
              <div className="flex items-start gap-3">
                <div className="text-amber-500 text-2xl">⚠️</div>
                <div className="flex-1">
                  <h3 className="text-base font-bold text-amber-900">
                    {t(locale, "retake_warning_title")}
                  </h3>
                  <p className="text-sm text-amber-800 mt-1">
                    {t(locale, "retake_warning_desc")}
                  </p>
                  <div className="mt-4">
                    <button
                      onClick={handleRetake}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-sm font-semibold rounded-xl shadow-xs transition"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
                        />
                      </svg>
                      {t(locale, "retake_button")}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Main Plain-Language Explanation Card */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-600"></span>
                {t(locale, "explanation_title")}
              </h3>

              <div className="flex items-center gap-2">
                {result.needs_escalation && (
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-100 text-purple-700">
                    {t(locale, "needs_escalation_badge")}
                  </span>
                )}
                <span
                  className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                    result.confidence >= 0.7
                      ? "bg-green-100 text-green-700"
                      : "bg-amber-100 text-amber-700"
                  }`}
                >
                  {Math.round(result.confidence * 100)}% {t(locale, "confidence_score")}
                </span>
              </div>
            </div>

            <p className="text-base text-gray-800 leading-relaxed whitespace-pre-line font-medium">
              {result.explanation}
            </p>
          </div>

          {/* "What You Should Do Next" Checklist */}
          {result.what_you_should_do_next && result.what_you_should_do_next.length > 0 && (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 space-y-4">
              <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-600"></span>
                {t(locale, "what_next_title")}
              </h3>

              <div className="space-y-3">
                {result.what_you_should_do_next.map((step, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-3 p-3.5 rounded-xl bg-emerald-50/60 border border-emerald-100"
                  >
                    <span className="w-6 h-6 rounded-full bg-emerald-600 text-white text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                      {idx + 1}
                    </span>
                    <p className="text-sm text-gray-800 font-medium leading-snug">{step}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Expandable Citations Accordion */}
          {result.citations && result.citations.length > 0 && (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 space-y-4">
              <div className="border-b border-gray-100 pb-3">
                <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-indigo-600"></span>
                  {t(locale, "citations_title")}
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">{t(locale, "citations_subtitle")}</p>
              </div>

              <div className="space-y-3">
                {result.citations.map((c) => {
                  const isExpanded = !!expandedCitations[c.id];
                  return (
                    <div
                      key={c.id}
                      className="border border-gray-200 rounded-xl overflow-hidden transition-colors"
                    >
                      <button
                        onClick={() => toggleCitation(c.id)}
                        className="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 flex items-center justify-between text-left transition"
                      >
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded-md bg-blue-100 text-blue-800 text-xs font-bold tracking-wide">
                            {c.id}
                          </span>
                          <span className="text-xs text-gray-500 font-medium">Official Clause</span>
                        </div>
                        <span className="text-gray-400 text-xs font-bold">
                          {isExpanded ? "▲" : "▼"}
                        </span>
                      </button>

                      {isExpanded && (
                        <div className="p-4 bg-white border-t border-gray-100 text-sm text-gray-700 leading-relaxed font-sans">
                          {c.text}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Extracted Text Collapsible Section */}
          {result.extracted_text && (
            <div className="border border-gray-200 rounded-xl bg-white overflow-hidden shadow-2xs">
              <button
                onClick={() => setShowRawText(!showRawText)}
                className="w-full px-4 py-3 text-left text-xs font-semibold text-gray-500 hover:text-gray-700 flex items-center justify-between bg-gray-50/70"
              >
                <span>{t(locale, "extracted_text_title")}</span>
                <span>{showRawText ? "▲" : "▼"}</span>
              </button>

              {showRawText && (
                <div className="p-4 bg-gray-900 text-gray-200 font-mono text-xs whitespace-pre-wrap max-h-60 overflow-y-auto">
                  {result.extracted_text}
                </div>
              )}
            </div>
          )}

          {/* Reset Action */}
          <div className="text-center pt-2">
            <button
              onClick={() => {
                setFile(null);
                setPreviewUrl(null);
                setResult(null);
              }}
              className="text-xs font-medium text-gray-500 hover:text-gray-700 underline"
            >
              Analyze another notice
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
