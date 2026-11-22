"use client";

import { useState } from "react";
import Link from "next/link";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import HealthCheck from "@/components/HealthCheck";
import SyntheticBanner from "@/components/SyntheticBanner";
import DemoUserSwitcher from "@/components/DemoUserSwitcher";
import RuleChangeNotifier from "@/components/RuleChangeNotifier";
import InterviewChat from "@/components/InterviewChat";
import DocumentReconciliation from "@/components/DocumentReconciliation";
import StatusDecoder from "@/components/StatusDecoder";
import RegistrationAgent from "@/components/RegistrationAgent";
import NoticeExplainer from "@/components/NoticeExplainer";
import SchemeQA from "@/components/SchemeQA";
import HelpdeskSupport from "@/components/HelpdeskSupport";
import { Locale, t } from "@/lib/i18n";
import {
  SproutIcon,
  MessageSquareIcon,
  FileSearchIcon,
  ActivitySquareIcon,
  BotIcon,
  FileTextIcon,
  HelpCircleIcon,
  HeadphonesIcon,
  BarChart3Icon,
  SparklesIcon,
} from "@/components/icons";

type ActiveTab = "interview" | "reconcile" | "status" | "agent" | "notice" | "ask" | "helpdesk";

export default function Home() {
  const [locale, setLocale] = useState<Locale>("en");
  const [activeTab, setActiveTab] = useState<ActiveTab>("interview");
  const [selectedDemoUser, setSelectedDemoUser] = useState<any>(null);

  const tabs: { id: ActiveTab; labelKey: string; icon: React.ReactNode }[] = [
    { id: "interview", labelKey: "tab_interview", icon: <MessageSquareIcon className="w-4 h-4" /> },
    { id: "reconcile", labelKey: "tab_reconcile", icon: <FileSearchIcon className="w-4 h-4" /> },
    { id: "status", labelKey: "tab_status", icon: <ActivitySquareIcon className="w-4 h-4" /> },
    { id: "agent", labelKey: "tab_agent", icon: <BotIcon className="w-4 h-4" /> },
    { id: "notice", labelKey: "tab_notice", icon: <FileTextIcon className="w-4 h-4" /> },
    { id: "ask", labelKey: "tab_ask", icon: <HelpCircleIcon className="w-4 h-4" /> },
    { id: "helpdesk", labelKey: "tab_helpdesk", icon: <HeadphonesIcon className="w-4 h-4 text-emerald-300" /> },
  ];

  return (
    <main className="min-h-screen mesh-bg flex flex-col font-sans text-slate-800">
      {/* 1. Synthetic Data Banner */}
      <SyntheticBanner locale={locale} />

      {/* 2. Modern Glassmorphic Header */}
      <header className="sticky top-0 z-40 glass-header">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-3">
          {/* Logo & Scheme Branding */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-300 flex items-center justify-center text-emerald-950 font-black text-sm shadow-md shadow-emerald-950/40 border border-emerald-300/40 shrink-0">
              <SproutIcon className="w-5 h-5 text-emerald-950" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-base sm:text-lg font-black text-white tracking-tight">
                  {t(locale, "title")}
                </span>
                <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-200 bg-white/10 px-2 py-0.5 rounded-full border border-emerald-400/30 uppercase tracking-wide backdrop-blur-md">
                  <SparklesIcon className="w-2.5 h-2.5 text-amber-300" />
                  <span>PM-KISAN AI</span>
                </span>
              </div>
              <p className="text-[10px] text-emerald-200/80 hidden sm:block">
                Grounded Rules • Gemini Multimodal Vision/Voice • Playwright Consent Agent
              </p>
            </div>
          </div>

          {/* Quick Demo Switcher & Rule Simulation Controls */}
          <div className="flex items-center gap-2 flex-wrap">
            <DemoUserSwitcher
              locale={locale}
              onSelectUser={(u) => setSelectedDemoUser(u)}
            />
            <RuleChangeNotifier locale={locale} />
          </div>

          {/* Metrics link, Health and Language Switcher */}
          <div className="flex items-center gap-2 sm:gap-2.5">
            <Link
              href="/metrics"
              className="px-3 py-1.5 bg-white/10 hover:bg-white/20 text-white rounded-xl text-xs font-bold border border-white/20 backdrop-blur-md transition shadow-xs flex items-center gap-1.5"
              title="Open Evaluation & Benchmark Metrics (/metrics)"
            >
              <BarChart3Icon className="w-3.5 h-3.5 text-emerald-300" />
              <span className="hidden sm:inline">Metrics</span>
            </Link>

            <HealthCheck locale={locale} />
            <LanguageSwitcher locale={locale} onChange={setLocale} />
          </div>
        </div>
      </header>

      {/* 3. Main Navigation & Content Container */}
      <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">
        {/* Navigation Tabs Bar */}
        <div className="flex justify-center overflow-x-auto pb-1 pt-1">
          <div className="inline-flex p-1.5 glass-panel rounded-2xl shadow-sm border border-emerald-500/20 gap-1.5 max-w-full">
            {tabs.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-3.5 py-2.5 rounded-xl text-xs sm:text-sm font-bold transition whitespace-nowrap ${
                    isActive
                      ? "bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-md shadow-emerald-900/20"
                      : "text-slate-600 hover:text-emerald-900 hover:bg-emerald-50/70"
                  }`}
                >
                  <span className={isActive ? "text-white" : "text-emerald-700"}>
                    {tab.icon}
                  </span>
                  <span>{t(locale, tab.labelKey)}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Active Tab View */}
        <div className="animate-in fade-in-50 duration-200">
          {activeTab === "interview" && <InterviewChat locale={locale} />}
          {activeTab === "reconcile" && <DocumentReconciliation locale={locale} />}
          {activeTab === "status" && <StatusDecoder locale={locale} />}
          {activeTab === "agent" && <RegistrationAgent locale={locale} />}
          {activeTab === "notice" && <NoticeExplainer locale={locale} />}
          {activeTab === "ask" && <SchemeQA locale={locale} />}
          {activeTab === "helpdesk" && <HelpdeskSupport locale={locale} />}
        </div>
      </div>

      {/* 4. Footer */}
      <footer className="mt-auto py-6 border-t border-emerald-500/10 bg-white/60 backdrop-blur-md text-center text-xs text-slate-400">
        <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <SproutIcon className="w-4 h-4 text-emerald-600" />
            <span className="font-semibold text-slate-700">CivicPilot PM-KISAN Ecosystem</span>
          </div>
          <p className="text-slate-500 text-[11px]">
            Deterministic Rule Engine • Gemini Multimodal RAG • Safe Consent Gate • 22 Indic Languages Ready
          </p>
        </div>
      </footer>
    </main>
  );
}
