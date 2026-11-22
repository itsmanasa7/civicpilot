"use client";

import { useState } from "react";
import { Locale, t } from "@/lib/i18n";

interface DiscrepancyItem {
  field: string;
  field_label: string;
  values_per_document: Record<string, string>;
  severity: "CRITICAL" | "MODERATE" | "MINOR" | "MATCHED";
  similarity_score: number;
  description: string;
  fix_at_office: string;
  canonical_value?: string;
}

interface ReconcileResponse {
  documents_analyzed: string[];
  extracted_fields_by_doc: Record<string, Record<string, any>>;
  discrepancies: DiscrepancyItem[];
  overall_status: string;
  total_discrepancies: number;
  critical_count: number;
  moderate_count: number;
  minor_count: number;
}

interface Props {
  locale: Locale;
}

export default function DocumentReconciliation({ locale }: Props) {
  const [data, setData] = useState<ReconcileResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Manual editing state
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [saveLoading, setSaveLoading] = useState(false);

  const loadDemoData = async () => {
    setLoading(true);
    setError(null);
    setEditingField(null);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      // Calling POST /reconcile with no body loads the synthetic demo-data files
      const res = await fetch(`${API_URL}/reconcile`, {
        method: "POST",
      });

      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }

      const report: ReconcileResponse = await res.json();
      setData(report);
    } catch (err: any) {
      setError(err?.message || "Failed to load and reconcile documents.");
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;

    setLoading(true);
    setError(null);
    const formData = new FormData();
    for (let i = 0; i < e.target.files.length; i++) {
      formData.append("files", e.target.files[i]);
    }

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const res = await fetch(`${API_URL}/reconcile`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`Reconciliation failed: ${res.status}`);
      }

      const report: ReconcileResponse = await res.json();
      setData(report);
    } catch (err: any) {
      setError(err?.message || "Failed to upload and reconcile documents.");
    } finally {
      setLoading(false);
    }
  };

  const startEditField = (item: DiscrepancyItem) => {
    setEditingField(item.field);
    setEditValues({ ...item.values_per_document });
  };

  const saveCorrection = async (field: string) => {
    if (!data) return;
    setSaveLoading(true);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

      // Prepare updated extracted_fields_by_doc
      const updatedDocs = { ...data.extracted_fields_by_doc };
      for (const [docKey, newVal] of Object.entries(editValues)) {
        if (updatedDocs[docKey]) {
          updatedDocs[docKey] = {
            ...updatedDocs[docKey],
            [field]: newVal,
          };
        }
      }

      const res = await fetch(`${API_URL}/reconcile/correct`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          extracted_fields_by_doc: updatedDocs,
          corrections: {},
        }),
      });

      if (res.ok) {
        const updatedReport: ReconcileResponse = await res.json();
        setData(updatedReport);
        setEditingField(null);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to save correction.");
    } finally {
      setSaveLoading(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-emerald-50 text-emerald-600 rounded-xl mb-3">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-gray-900">{t(locale, "reconcile_title")}</h2>
          <p className="text-sm text-gray-500 mt-1 max-w-md mx-auto">{t(locale, "reconcile_subtitle")}</p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center justify-center gap-3">
          <button
            onClick={loadDemoData}
            disabled={loading}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-sm rounded-xl shadow-xs transition"
          >
            <span className="text-base">⚡</span>
            <span>{t(locale, "load_demo_button")}</span>
          </button>

          <label className="inline-flex items-center gap-2 px-5 py-2.5 bg-white hover:bg-gray-50 border border-gray-300 text-gray-700 font-semibold text-sm rounded-xl shadow-2xs cursor-pointer transition">
            <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            <span>Upload Your Documents</span>
            <input
              type="file"
              multiple
              accept="application/json,text/plain,image/*,application/pdf"
              className="hidden"
              onChange={handleFileUpload}
            />
          </label>
        </div>

        {loading && (
          <div className="mt-6 text-center text-sm text-gray-500 flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin"></div>
            <span>Cross-matching documents with RapidFuzz transliteration engine...</span>
          </div>
        )}

        {error && (
          <div className="mt-4 p-4 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700">
            ⚠️ {error}
          </div>
        )}
      </div>

      {/* RECONCILIATION REPORT */}
      {data && (
        <div className="space-y-6 animate-fade-in">
          {/* Summary Badges Bar */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5 flex flex-wrap items-center justify-between gap-4">
            <div>
              <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Overall Status</span>
              <div className="text-base font-extrabold text-gray-900 mt-0.5">
                {data.total_discrepancies > 0 ? (
                  <span className="text-amber-600 flex items-center gap-1.5">
                    <span>⚠️</span> {t(locale, "discrepancies_found")} ({data.total_discrepancies})
                  </span>
                ) : (
                  <span className="text-emerald-600 flex items-center gap-1.5">
                    <span>✓</span> {t(locale, "all_matched")}
                  </span>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-xs font-bold">
                {data.critical_count} Critical
              </span>
              <span className="px-3 py-1 bg-amber-100 text-amber-800 rounded-full text-xs font-bold">
                {data.moderate_count} Moderate
              </span>
              <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-bold">
                {data.minor_count} Minor
              </span>
            </div>
          </div>

          {/* Detailed Discrepancies Table */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wide">
                Document Field Comparison Matrix
              </h3>
              <span className="text-xs text-gray-500">
                {data.documents_analyzed.length} documents analyzed
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-gray-50 border-b border-gray-200 text-gray-600 font-bold uppercase tracking-wider">
                  <tr>
                    <th className="py-3.5 px-4">Field</th>
                    <th className="py-3.5 px-4">Aadhaar</th>
                    <th className="py-3.5 px-4">Land Record</th>
                    <th className="py-3.5 px-4">Bank Passbook</th>
                    <th className="py-3.5 px-4">Self-Declaration</th>
                    <th className="py-3.5 px-4">Severity</th>
                    <th className="py-3.5 px-4">{t(locale, "fix_at_office_label")}</th>
                    <th className="py-3.5 px-4 text-center">Action</th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-gray-100 font-medium">
                  {data.discrepancies.map((item) => {
                    const isEditing = editingField === item.field;

                    return (
                      <tr
                        key={item.field}
                        className={`hover:bg-gray-50/70 transition-colors ${
                          item.severity === "CRITICAL"
                            ? "bg-red-50/30"
                            : item.severity === "MODERATE"
                            ? "bg-amber-50/20"
                            : ""
                        }`}
                      >
                        {/* Field Label */}
                        <td className="py-4 px-4 font-bold text-gray-900 whitespace-nowrap">
                          {item.field_label}
                        </td>

                        {/* Aadhaar value */}
                        <td className="py-4 px-4 text-gray-700">
                          {isEditing ? (
                            <input
                              type="text"
                              value={editValues["aadhaar"] ?? item.values_per_document["aadhaar"] ?? ""}
                              onChange={(e) =>
                                setEditValues({ ...editValues, aadhaar: e.target.value })
                              }
                              className="w-full px-2 py-1 text-xs border rounded-md"
                            />
                          ) : (
                            item.values_per_document["aadhaar"] ?? "—"
                          )}
                        </td>

                        {/* Land Record value */}
                        <td className="py-4 px-4 text-gray-700">
                          {isEditing ? (
                            <input
                              type="text"
                              value={editValues["land_record"] ?? item.values_per_document["land_record"] ?? ""}
                              onChange={(e) =>
                                setEditValues({ ...editValues, land_record: e.target.value })
                              }
                              className="w-full px-2 py-1 text-xs border rounded-md"
                            />
                          ) : (
                            item.values_per_document["land_record"] ?? "—"
                          )}
                        </td>

                        {/* Bank Passbook value */}
                        <td className="py-4 px-4 text-gray-700">
                          {isEditing ? (
                            <input
                              type="text"
                              value={editValues["bank_passbook"] ?? item.values_per_document["bank_passbook"] ?? ""}
                              onChange={(e) =>
                                setEditValues({ ...editValues, bank_passbook: e.target.value })
                              }
                              className="w-full px-2 py-1 text-xs border rounded-md"
                            />
                          ) : (
                            item.values_per_document["bank_passbook"] ?? "—"
                          )}
                        </td>

                        {/* Self-Declaration value */}
                        <td className="py-4 px-4 text-gray-700">
                          {isEditing ? (
                            <input
                              type="text"
                              value={editValues["self_declaration"] ?? item.values_per_document["self_declaration"] ?? ""}
                              onChange={(e) =>
                                setEditValues({ ...editValues, self_declaration: e.target.value })
                              }
                              className="w-full px-2 py-1 text-xs border rounded-md"
                            />
                          ) : (
                            item.values_per_document["self_declaration"] ?? "—"
                          )}
                        </td>

                        {/* Severity Badge */}
                        <td className="py-4 px-4 whitespace-nowrap">
                          <span
                            className={`px-2.5 py-1 rounded-full text-2xs font-extrabold ${
                              item.severity === "CRITICAL"
                                ? "bg-red-100 text-red-800"
                                : item.severity === "MODERATE"
                                ? "bg-amber-100 text-amber-800"
                                : item.severity === "MINOR"
                                ? "bg-blue-100 text-blue-800"
                                : "bg-emerald-100 text-emerald-800"
                            }`}
                          >
                            {item.severity} ({Math.round(item.similarity_score * 100)}%)
                          </span>
                        </td>

                        {/* Fix at Office Badge */}
                        <td className="py-4 px-4 text-gray-600 text-2xs leading-snug min-w-[200px]">
                          <span className="font-semibold text-gray-800">{item.fix_at_office}</span>
                          <p className="text-gray-400 mt-0.5">{item.description}</p>
                        </td>

                        {/* Actions */}
                        <td className="py-4 px-4 text-center whitespace-nowrap">
                          {isEditing ? (
                            <div className="flex flex-col gap-1">
                              <button
                                onClick={() => saveCorrection(item.field)}
                                disabled={saveLoading}
                                className="px-2 py-1 bg-emerald-600 text-white rounded-md text-2xs font-bold hover:bg-emerald-700"
                              >
                                {saveLoading ? "..." : t(locale, "save_correction")}
                              </button>
                              <button
                                onClick={() => setEditingField(null)}
                                className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded-md text-2xs hover:bg-gray-200"
                              >
                                {t(locale, "cancel")}
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => startEditField(item)}
                              className="px-2.5 py-1 bg-white hover:bg-gray-100 text-blue-700 border border-blue-200 rounded-lg text-2xs font-bold shadow-2xs transition"
                            >
                              ✏️ {t(locale, "manual_correct_button")}
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
