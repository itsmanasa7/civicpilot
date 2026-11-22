"use client";

import React, { useState, useEffect } from "react";
import { Locale } from "@/lib/i18n";
import { SparklesIcon, ClockIcon } from "./icons";

interface Nudge {
  id: string;
  timestamp: string;
  user_name: string;
  nudge_type: string;
  clause_cited?: string;
  message: string;
  sent: boolean;
}

export default function RuleChangeNotifier({ locale }: { locale: Locale }) {
  const [nudges, setNudges] = useState<Nudge[]>([]);
  const [loadingSim, setLoadingSim] = useState(false);
  const [loadingCron, setLoadingCron] = useState(false);
  const [showDrawer, setShowDrawer] = useState(false);
  const [alertBanner, setAlertBanner] = useState<string | null>(null);

  const fetchNudges = () => {
    fetch("http://localhost:8000/nudges")
      .then((res) => (res.ok ? res.json() : []))
      .then((data: Nudge[]) => setNudges(data))
      .catch(() => {});
  };

  useEffect(() => {
    fetchNudges();
  }, []);

  const handleSimulateRuleChange = async () => {
    setLoadingSim(true);
    setAlertBanner(null);
    try {
      const resp = await fetch("http://localhost:8000/simulate-rule-change", {
        method: "POST",
      });
      if (resp.ok) {
        const data = await resp.json();
        const affectedNames = (data.affected_users || []).map((u: any) => u.name).join(", ");
        setAlertBanner(
          locale === "hi"
            ? `⚡ नियम संशोधन 2026.2 लागू! केवल प्रभावित उपयोगकर्ता (${affectedNames}) को टेलीग्राम और एसएमएस से सूचित किया गया।`
            : `⚡ Rule Amendment 2026.2 Enacted! Only affected citizen (${affectedNames}) was notified.`
        );
        fetchNudges();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingSim(false);
    }
  };

  const handleDispatchCronNudges = async () => {
    setLoadingCron(true);
    setAlertBanner(null);
    try {
      const resp = await fetch("http://localhost:8000/cron/dispatch-nudges", {
        method: "POST",
      });
      if (resp.ok) {
        const data = await resp.json();
        setAlertBanner(
          locale === "hi"
            ? `⏰ क्रॉन सम्पन्न: ${data.dispatched_count} नागरिकों को समय-सीमा व लंबित दस्तावेज़ अलर्ट भेजे गए।`
            : `⏰ Cron Executed: ${data.dispatched_count} proactive reminders dispatched for 3-day deadline & missing land records.`
        );
        fetchNudges();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingCron(false);
    }
  };

  return (
    <div className="relative">
      <div className="flex flex-wrap items-center gap-2">
        {/* Simulate Rule Change Button */}
        <button
          type="button"
          onClick={handleSimulateRuleChange}
          disabled={loadingSim}
          className="px-2.5 py-1.5 bg-white/10 hover:bg-white/20 text-white font-bold rounded-xl text-xs border border-white/20 backdrop-blur-md transition shadow-xs flex items-center gap-1.5"
          title="Versions the scheme corpus and notifies ONLY affected beneficiaries"
        >
          {loadingSim ? (
            <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <SparklesIcon className="w-3.5 h-3.5 text-amber-300" />
          )}
          <span className="hidden sm:inline">
            {locale === "hi" ? "नियम संशोधन" : "Simulate Rule"}
          </span>
          <span className="text-[10px] bg-amber-400/20 text-amber-200 px-1 py-0.2 rounded font-mono">2026.2</span>
        </button>

        {/* Cron Job Nudge Trigger */}
        <button
          type="button"
          onClick={handleDispatchCronNudges}
          disabled={loadingCron}
          className="px-2.5 py-1.5 bg-white/10 hover:bg-white/20 text-white font-bold rounded-xl text-xs border border-white/20 backdrop-blur-md transition shadow-xs flex items-center gap-1.5"
          title="Runs periodic background cron job for pending deadlines"
        >
          {loadingCron ? (
            <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <ClockIcon className="w-3.5 h-3.5 text-emerald-300" />
          )}
          <span className="hidden sm:inline">
            {locale === "hi" ? "क्रॉन नड्ज" : "Cron"}
          </span>
        </button>

        {/* Notifications Bell */}
        <button
          type="button"
          onClick={() => setShowDrawer(!showDrawer)}
          className="relative p-2 text-white/90 hover:text-white bg-white/10 hover:bg-white/20 rounded-xl border border-white/20 backdrop-blur-md transition shadow-xs"
          title="View Citizen Nudges & Alerts"
        >
          <svg className="w-3.5 h-3.5 text-emerald-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          {nudges.length > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-amber-500 text-slate-950 rounded-full text-[9px] font-black flex items-center justify-center shadow-xs">
              {nudges.length}
            </span>
          )}
        </button>
      </div>

      {/* Alert Toast */}
      {alertBanner && (
        <div className="fixed bottom-4 right-4 z-50 p-4 bg-emerald-950/90 backdrop-blur-xl border border-emerald-400/40 text-emerald-100 rounded-2xl text-xs font-semibold flex items-center justify-between shadow-2xl max-w-md animate-in fade-in slide-in-from-bottom-2">
          <span>{alertBanner}</span>
          <button
            type="button"
            onClick={() => setAlertBanner(null)}
            className="ml-3 text-emerald-300 hover:text-white font-bold text-xs"
          >
            ✕
          </button>
        </div>
      )}

      {/* Notifications Drawer */}
      {showDrawer && (
        <div className="absolute right-0 mt-3 w-80 sm:w-96 rounded-3xl glass-panel border border-emerald-500/20 shadow-2xl p-4 z-50 animate-in fade-in zoom-in-95 duration-100">
          <div className="flex items-center justify-between pb-3 border-b border-emerald-500/10">
            <div className="flex items-center gap-2">
              <span className="text-xs font-black text-slate-900 uppercase tracking-wide">
                Dispatched Nudges
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                {nudges.length} total
              </span>
            </div>
            <button
              onClick={() => setShowDrawer(false)}
              className="text-slate-400 hover:text-slate-700 text-xs font-bold"
            >
              ✕
            </button>
          </div>

          <div className="max-h-80 overflow-y-auto space-y-2 mt-3 pr-1">
            {nudges.length === 0 ? (
              <p className="text-xs text-slate-400 text-center py-6">
                No nudges sent yet. Click &apos;Simulate Rule&apos; or &apos;Cron&apos; to trigger.
              </p>
            ) : (
              nudges.map((n) => (
                <div
                  key={n.id}
                  className="p-3 rounded-2xl bg-white/80 border border-slate-200/80 text-xs space-y-1 shadow-2xs hover:border-emerald-300 transition"
                >
                  <div className="flex items-center justify-between text-[10px] text-slate-400">
                    <span className="font-bold text-emerald-800">{n.user_name}</span>
                    <span>{n.timestamp}</span>
                  </div>
                  <p className="text-slate-800 font-medium leading-relaxed">{n.message}</p>
                  {n.clause_cited && (
                    <span className="inline-block px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 font-mono text-[9px] font-bold">
                      [{n.clause_cited}]
                    </span>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
