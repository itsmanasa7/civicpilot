"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { API_BASE_URL } from "@/lib/api";

interface DimensionMetrics {
  eligibility_accuracy_pct: number;
  eligibility_cases: string;
  citation_coverage_pct: number;
  citation_cases: string;
  escalation_correctness_pct: number;
  escalation_cases: string;
  reconciliation_recall_pct: number;
  reconciliation_cases: string;
}

interface BenchmarkCaseResult {
  id: string;
  category: string;
  name: string;
  passed: boolean;
  latency_ms: number;
  details: any;
}

interface BenchmarkResult {
  timestamp: string;
  total_cases: number;
  passed_cases: number;
  overall_accuracy_pct: number;
  execution_duration_sec: number;
  dimensions: DimensionMetrics;
  cases: BenchmarkCaseResult[];
}

export default function MetricsPage() {
  const [data, setData] = useState<BenchmarkResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeCategory, setActiveCategory] = useState<string>("all");
  const [error, setError] = useState<string | null>(null);

  const fetchLatest = async () => {
    try {
      const resp = await fetch(`${API_BASE_URL}/eval/latest`);
      if (resp.ok) {
        const json = await resp.json();
        setData(json);
      }
    } catch (e: any) {
      setError("Unable to load latest benchmark results.");
    }
  };

  useEffect(() => {
    fetchLatest();
  }, []);

  const handleRunBenchmark = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${API_BASE_URL}/eval/run`, {
        method: "POST",
      });
      if (resp.ok) {
        const json = await resp.json();
        setData(json);
      } else {
        throw new Error(`Evaluation failed with status ${resp.status}`);
      }
    } catch (e: any) {
      setError(e.message || "Failed running benchmark suite.");
    } finally {
      setLoading(false);
    }
  };

  const filteredCases = data?.cases.filter((c) =>
    activeCategory === "all" ? true : c.category === activeCategory
  ) || [];

  return (
    <main className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* Top Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-30 shadow-2xs">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="text-xs font-bold text-gray-500 hover:text-blue-600 transition flex items-center gap-1"
            >
              ← Back to CivicPilot
            </Link>
            <span className="text-gray-300">|</span>
            <h1 className="text-base sm:text-lg font-black text-gray-900 tracking-tight flex items-center gap-2">
              <span>📊</span>
              <span>CivicPilot Evaluation & Benchmark Metrics (/metrics)</span>
            </h1>
          </div>

          <button
            type="button"
            onClick={handleRunBenchmark}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-bold rounded-xl text-xs transition shadow-sm flex items-center gap-2"
          >
            {loading ? <span className="animate-spin text-xs">⏳</span> : <span>⚡</span>}
            <span>{loading ? "Running 30 Benchmark Cases..." : "Re-run Live Benchmark"}</span>
          </button>
        </div>
      </header>

      {/* Main Container */}
      <div className="max-w-6xl w-full mx-auto px-4 py-8 space-y-6 flex-1">
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl font-medium">
            {error}
          </div>
        )}

        {/* Summary Metric Cards */}
        {data && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              {/* Overall Accuracy */}
              <div className="col-span-2 sm:col-span-1 bg-white p-4 rounded-2xl border border-gray-200 shadow-2xs">
                <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider block">
                  Overall Accuracy
                </span>
                <div className="text-2xl sm:text-3xl font-black text-blue-700 mt-1">
                  {data.overall_accuracy_pct}%
                </div>
                <div className="text-[11px] font-semibold text-gray-500 mt-1">
                  {data.passed_cases} / {data.total_cases} Cases Passed
                </div>
              </div>

              {/* Eligibility Accuracy */}
              <div className="bg-white p-4 rounded-2xl border border-gray-200 shadow-2xs">
                <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider block">
                  Eligibility Engine
                </span>
                <div className="text-xl sm:text-2xl font-black text-emerald-600 mt-1">
                  {data.dimensions.eligibility_accuracy_pct}%
                </div>
                <div className="text-[11px] font-semibold text-gray-500 mt-1">
                  {data.dimensions.eligibility_cases} (Deterministic)
                </div>
              </div>

              {/* Citation Coverage */}
              <div className="bg-white p-4 rounded-2xl border border-gray-200 shadow-2xs">
                <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider block">
                  Citation Grounding
                </span>
                <div className="text-xl sm:text-2xl font-black text-purple-600 mt-1">
                  {data.dimensions.citation_coverage_pct}%
                </div>
                <div className="text-[11px] font-semibold text-gray-500 mt-1">
                  {data.dimensions.citation_cases} Verified
                </div>
              </div>

              {/* Escalation Correctness */}
              <div className="bg-white p-4 rounded-2xl border border-gray-200 shadow-2xs">
                <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider block">
                  Escalation Safety
                </span>
                <div className="text-xl sm:text-2xl font-black text-amber-600 mt-1">
                  {data.dimensions.escalation_correctness_pct}%
                </div>
                <div className="text-[11px] font-semibold text-gray-500 mt-1">
                  {data.dimensions.escalation_cases} Gated
                </div>
              </div>

              {/* Reconciliation Recall */}
              <div className="bg-white p-4 rounded-2xl border border-gray-200 shadow-2xs">
                <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider block">
                  Reconciliation Recall
                </span>
                <div className="text-xl sm:text-2xl font-black text-teal-600 mt-1">
                  {data.dimensions.reconciliation_recall_pct}%
                </div>
                <div className="text-[11px] font-semibold text-gray-500 mt-1">
                  {data.dimensions.reconciliation_cases} Discrepancies
                </div>
              </div>
            </div>

            {/* Test Cases Table Card */}
            <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-xs space-y-4">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-gray-100">
                <div>
                  <h3 className="text-base font-bold text-gray-900">
                    30 Synthetic Benchmark Cases
                  </h3>
                  <p className="text-xs text-gray-500">
                    Execution Time: {data.execution_duration_sec}s • Evaluated against PM-KISAN
                    Ground Truth
                  </p>
                </div>

                {/* Category Filters */}
                <div className="flex flex-wrap gap-1 bg-gray-100 p-1 rounded-xl text-xs font-bold">
                  {[
                    { id: "all", label: "All (30)" },
                    { id: "eligibility", label: "Eligibility (10)" },
                    { id: "citation", label: "Citations (8)" },
                    { id: "escalation", label: "Escalation (6)" },
                    { id: "reconciliation", label: "Reconciliation (6)" },
                  ].map((btn) => (
                    <button
                      key={btn.id}
                      type="button"
                      onClick={() => setActiveCategory(btn.id)}
                      className={`px-3 py-1 rounded-lg transition ${
                        activeCategory === btn.id
                          ? "bg-white text-blue-700 shadow-2xs"
                          : "text-gray-600 hover:text-gray-900"
                      }`}
                    >
                      {btn.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Table */}
              <div className="border border-gray-200 rounded-xl overflow-hidden overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-gray-50 border-b border-gray-200 text-gray-600 font-bold uppercase text-[10px]">
                    <tr>
                      <th className="p-3">Case ID</th>
                      <th className="p-3">Category</th>
                      <th className="p-3">Benchmark Test Scenario</th>
                      <th className="p-3">Latency</th>
                      <th className="p-3 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {filteredCases.map((c) => (
                      <tr key={c.id} className="hover:bg-slate-50 transition">
                        <td className="p-3 font-mono font-bold text-blue-700">{c.id}</td>
                        <td className="p-3">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                              c.category === "eligibility"
                                ? "bg-emerald-50 text-emerald-800"
                                : c.category === "citation"
                                ? "bg-purple-50 text-purple-800"
                                : c.category === "escalation"
                                ? "bg-amber-50 text-amber-800"
                                : "bg-teal-50 text-teal-800"
                            }`}
                          >
                            {c.category}
                          </span>
                        </td>
                        <td className="p-3 font-medium text-gray-800">{c.name}</td>
                        <td className="p-3 font-mono text-gray-500">{c.latency_ms} ms</td>
                        <td className="p-3 text-center">
                          <span
                            className={`px-2.5 py-0.5 rounded-full text-[10px] font-extrabold ${
                              c.passed
                                ? "bg-emerald-100 text-emerald-800"
                                : "bg-red-100 text-red-800"
                            }`}
                          >
                            {c.passed ? "PASSED" : "FAILED"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="mt-auto py-6 border-t border-gray-200 bg-white text-center text-xs text-gray-400">
        <p>CivicPilot Benchmark Evaluation Suite • 30 Ground-Truth Synthetic Test Cases</p>
      </footer>
    </main>
  );
}
