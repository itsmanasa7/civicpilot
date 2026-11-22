"use client";

import { useEffect, useState } from "react";
import { Locale, t } from "@/lib/i18n";
import { API_BASE_URL } from "@/lib/api";

interface Props {
  locale: Locale;
}

export default function HealthCheck({ locale }: Props) {
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE_URL}/health`)
      .then((r) => r.json())
      .then((d) => {
        setStatus(d.status);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, []);

  return (
    <div
      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 text-xs font-bold text-white backdrop-blur-md shadow-xs transition"
      title="FastAPI Backend Live Health Status"
    >
      {loading ? (
        <>
          <span className="w-2 h-2 rounded-full bg-amber-300 animate-ping" />
          <span className="text-[10px] text-emerald-200 hidden md:inline">API...</span>
        </>
      ) : error ? (
        <>
          <span className="w-2 h-2 rounded-full bg-rose-400" />
          <span className="text-[10px] text-rose-200 hidden md:inline">API Offline</span>
        </>
      ) : (
        <>
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-xs shadow-emerald-400/80" />
          <span className="text-[10px] text-emerald-200 font-mono hidden md:inline">API :8000</span>
        </>
      )}
    </div>
  );
}
