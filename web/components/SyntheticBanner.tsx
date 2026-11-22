"use client";

import React, { useState } from "react";
import { Locale } from "@/lib/i18n";
import { AlertTriangleIcon } from "./icons";

export default function SyntheticBanner({ locale }: { locale: Locale }) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div className="bg-gradient-to-r from-amber-600 via-emerald-800 to-teal-900 text-amber-100 text-xs font-medium px-4 py-1.5 border-b border-amber-400/20 shadow-xs transition flex items-center justify-between">
      <div className="max-w-6xl mx-auto flex items-center gap-2 flex-1 justify-center sm:justify-start">
        <AlertTriangleIcon className="w-4 h-4 text-amber-300 shrink-0" />
        <span className="text-[11px] sm:text-xs">
          {locale === "hi"
            ? "डेमो सैंडबॉक्स — केवल कृत्रिम डेटा (Synthetic Data Only): सभी नागरिक विवरण, आधार नंबर और बैंक लेन-देन सिमुलेटेड हैं। वास्तविक व्यक्तिगत डेटा दर्ज न करें।"
            : "DEMO SANDBOX — SYNTHETIC DATA ONLY: All citizen records, portal mirrors, Aadhaar numbers, and bank transactions are simulated for demonstration. Do not enter real PII."}
        </span>
      </div>

      <button
        type="button"
        onClick={() => setDismissed(true)}
        className="ml-3 text-amber-200/80 hover:text-white font-bold text-xs px-2 py-0.5 hover:bg-white/10 rounded-lg transition"
        title="Dismiss warning"
      >
        Dismiss
      </button>
    </div>
  );
}
