"use client";

import { useState } from "react";
import { Locale, t } from "@/lib/i18n";
import {
  HeadphonesIcon,
  PhoneCallIcon,
  TicketIcon,
  Building2Icon,
  MapPinIcon,
  ClockIcon,
  ShieldCheckIcon,
  CheckCircle2Icon,
  AlertTriangleIcon,
  SparklesIcon,
} from "./icons";

interface Props {
  locale: Locale;
}

export default function HelpdeskSupport({ locale }: Props) {
  // Grievance Form State
  const [aadhaarOrReg, setAadhaarOrReg] = useState("");
  const [category, setCategory] = useState("INSTALLMENT_STOPPED");
  const [phone, setPhone] = useState("");
  const [notes, setNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [generatedTicket, setGeneratedTicket] = useState<{
    ticketId: string;
    date: string;
    category: string;
    sla: string;
    assignedTo: string;
  } | null>(null);

  const hotlines = [
    {
      name: locale === "hi" ? "किसान कॉल सेंटर (अखिल भारतीय)" : "Kisan Call Center (All India)",
      number: "155261",
      timing: "6:00 AM - 10:00 PM (Daily)",
      languages: "All 22 Indian Languages",
      badge: "Toll Free",
      desc: "Agricultural experts & central scheme dispute redressal.",
    },
    {
      name: locale === "hi" ? "पीएम-किसान केंद्रीय हेल्पलाइन" : "PM-KISAN Central Helpline",
      number: "1800-115-526",
      timing: "9:30 AM - 6:00 PM (Mon-Sat)",
      languages: "Hindi & English",
      badge: "Toll Free",
      desc: "Ministry of Agriculture & Farmers Welfare DBT helpdesk.",
    },
    {
      name: locale === "hi" ? "डीबीटी व फंड समाधान हेल्पडेस्क" : "DBT Settlement & Grievance Desk",
      number: "011-24300606",
      timing: "10:00 AM - 5:00 PM (Weekdays)",
      languages: "Hindi & English",
      badge: "Direct Line",
      desc: "PFMS bank rejection, account unfreezing & installment trace.",
    },
  ];

  const categories = [
    { id: "INSTALLMENT_STOPPED", label: "Installment Stopped / Payment Failure" },
    { id: "EKYC_PENDING", label: "e-KYC Pending / CSC Biometric Failure" },
    { id: "LAND_SEEDING_NO", label: "Land Seeding Marked 'No' on Portal (Bhulekh)" },
    { id: "AADHAAR_BANK_MISMATCH", label: "Aadhaar Not Seeded with Bank / NPCI Pending" },
    { id: "NAME_SPELLING_MISMATCH", label: "Name Spelling Mismatch in Portal Record" },
    { id: "INCORRECT_EXCLUSION", label: "Erroneously Flagged under Tax / Exclusion Clause" },
  ];

  const handleLodgeGrievance = (e: React.FormEvent) => {
    e.preventDefault();
    if (!aadhaarOrReg.trim()) return;

    setIsSubmitting(true);
    setTimeout(() => {
      const randomNum = Math.floor(1000 + Math.random() * 9000);
      const catLabel = categories.find((c) => c.id === category)?.label || category;
      setGeneratedTicket({
        ticketId: `CP-GRV-2026-${randomNum}`,
        date: new Date().toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }),
        category: catLabel,
        sla: "7 Working Days",
        assignedTo: "District Grievance Redressal Committee (Chaired by District Collector)",
      });
      setIsSubmitting(false);
    }, 700);
  };

  return (
    <div className="space-y-6">
      {/* 1. Header Banner */}
      <div className="glass-panel rounded-3xl p-6 sm:p-8 border border-emerald-500/20 shadow-lg relative overflow-hidden">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 relative z-10">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-emerald-700 to-teal-500 flex items-center justify-center text-white shadow-md shadow-emerald-900/20 shrink-0">
              <HeadphonesIcon className="w-7 h-7" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
                  {locale === "hi" ? "किसान हेल्पडेस्क व शिकायत निवारण" : "Kisan Helpdesk & Grievance Redressal"}
                </h2>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200 uppercase tracking-wide">
                  24x7 Support
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-xl">
                {locale === "hi"
                  ? "आधिकारिक सरकारी किसान हेल्पलाइन, ऑनलाइन शिकायत टिकट पंजीकरण, और तहसील नोडल अधिकारियों की संपर्क सूची।"
                  : "Direct access to official central hotlines, instant tracked grievance tokens, and designated local administrative offices."}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Official Toll-Free Hotlines */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {hotlines.map((hl, idx) => (
          <div
            key={idx}
            className="glass-card rounded-2xl p-5 border border-emerald-500/15 shadow-sm hover:border-emerald-500/40 hover:shadow-md transition group flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between gap-2 mb-2">
                <span className="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {hl.badge}
                </span>
                <span className="text-[10px] text-slate-400 flex items-center gap-1">
                  <ClockIcon className="w-3 h-3 text-slate-400" /> {hl.timing}
                </span>
              </div>
              <h3 className="text-sm font-bold text-slate-900 group-hover:text-emerald-800 transition">
                {hl.name}
              </h3>
              <div className="text-xl sm:text-2xl font-black text-emerald-700 tracking-tight my-2 font-mono">
                {hl.number}
              </div>
              <p className="text-xs text-slate-500 leading-relaxed mb-3">{hl.desc}</p>
            </div>

            <a
              href={`tel:${hl.number.replace(/-/g, "")}`}
              className="w-full inline-flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white text-xs font-bold shadow-xs transition"
            >
              <PhoneCallIcon className="w-3.5 h-3.5" />
              <span>{locale === "hi" ? "कॉल करें (Toll Free)" : "Tap to Call"}</span>
            </a>
          </div>
        ))}
      </div>

      {/* 3. Interactive Grievance Form & SLA Tracker */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Register Grievance Ticket */}
        <div className="lg:col-span-7 glass-panel rounded-3xl p-6 border border-emerald-500/20 shadow-md">
          <div className="flex items-center gap-2 mb-4">
            <TicketIcon className="w-5 h-5 text-emerald-600" />
            <h3 className="text-base font-bold text-slate-900">
              {locale === "hi" ? "आधिकारिक शिकायत दर्ज करें (Lodge Grievance)" : "Lodge Official Scheme Grievance"}
            </h3>
          </div>
          <p className="text-xs text-slate-500 mb-5">
            {locale === "hi"
              ? "यदि आपकी किस्त रोकी गई है या सीएससी पर समाधान नहीं हुआ, तो सीधे जिला शिकायत निवारण समिति को शिकायत भेजें।"
              : "Generate an official digital grievance token escalated directly to the District Agriculture Nodal Officer."}
          </p>

          <form onSubmit={handleLodgeGrievance} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                {locale === "hi" ? "आधार नंबर / पंजीकरण संख्या *" : "Aadhaar Number or Registration No *"}
              </label>
              <input
                type="text"
                required
                value={aadhaarOrReg}
                onChange={(e) => setAadhaarOrReg(e.target.value)}
                placeholder="e.g. 9876 5432 1098 or UP1098273"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-white/80 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 text-xs sm:text-sm font-medium"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  {locale === "hi" ? "शिकायत की श्रेणी *" : "Category of Issue *"}
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl border border-slate-200 bg-white/80 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 text-xs font-medium"
                >
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  {locale === "hi" ? "मोबाइल नंबर (SMS अपडेट हेतु)" : "Mobile Number (for SMS updates)"}
                </label>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="e.g. 9876543210"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-white/80 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 text-xs font-medium"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                {locale === "hi" ? "समस्या का विवरण (वैकल्पिक)" : "Brief Description / Context"}
              </label>
              <textarea
                rows={3}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Details of bank visit, CSC error receipt, or Tehsil remarks..."
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-white/80 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 text-xs font-medium"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-emerald-600 via-emerald-700 to-teal-700 hover:from-emerald-700 hover:to-teal-800 text-white font-bold text-xs sm:text-sm shadow-md shadow-emerald-900/20 transition flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Generating Official Ticket...</span>
                </>
              ) : (
                <>
                  <TicketIcon className="w-4 h-4" />
                  <span>{locale === "hi" ? "शिकायत टिकट दर्ज करें" : "Generate Tracked Grievance Ticket"}</span>
                </>
              )}
            </button>
          </form>

          {/* Generated Ticket Result */}
          {generatedTicket && (
            <div className="mt-5 p-4 rounded-2xl bg-emerald-50 border border-emerald-300 text-emerald-900 animate-in fade-in slide-in-from-top-2">
              <div className="flex items-center justify-between pb-3 border-b border-emerald-200/60">
                <div className="flex items-center gap-2">
                  <CheckCircle2Icon className="w-5 h-5 text-emerald-600" />
                  <span className="text-xs font-black uppercase tracking-wide">
                    {locale === "hi" ? "शिकायत टिकट सफलतापूर्वक जनरेट हुआ" : "Grievance Ticket Generated"}
                  </span>
                </div>
                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-emerald-200/60 text-emerald-900">
                  {generatedTicket.ticketId}
                </span>
              </div>

              <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-emerald-700/80 font-medium block">Issue Category:</span>
                  <span className="font-bold text-emerald-950">{generatedTicket.category}</span>
                </div>
                <div>
                  <span className="text-emerald-700/80 font-medium block">Mandatory SLA:</span>
                  <span className="font-bold text-emerald-950">{generatedTicket.sla}</span>
                </div>
                <div className="col-span-2">
                  <span className="text-emerald-700/80 font-medium block">Escalated To:</span>
                  <span className="font-semibold text-emerald-900">{generatedTicket.assignedTo}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Designated Local Office Directory */}
        <div className="lg:col-span-5 space-y-4">
          <div className="glass-panel rounded-3xl p-6 border border-emerald-500/20 shadow-md">
            <div className="flex items-center gap-2 mb-3">
              <Building2Icon className="w-5 h-5 text-emerald-600" />
              <h3 className="text-base font-bold text-slate-900">
                {locale === "hi" ? "स्थानीय प्रशासनिक कार्यालय गाइड" : "Designated Office Directory"}
              </h3>
            </div>
            <p className="text-xs text-slate-500 mb-4">
              Where to submit physical documents depending on your rejection flag:
            </p>

            <div className="space-y-3">
              <div className="p-3 rounded-2xl bg-white/70 border border-slate-200/80 hover:border-emerald-300 transition">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-900">Tehsil / Lekhpal (Patwari)</span>
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-100 text-amber-800">
                    Land Seeding
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Submit updated Khatauni/Khasra to mark &apos;Land Seeding: Yes&apos; on the state revenue portal.
                </p>
              </div>

              <div className="p-3 rounded-2xl bg-white/70 border border-slate-200/80 hover:border-emerald-300 transition">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-900">Common Service Centre (CSC)</span>
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-100 text-blue-800">
                    Biometric e-KYC
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Walk in with your Aadhaar card for thumb-scan or facial biometric authentication.
                </p>
              </div>

              <div className="p-3 rounded-2xl bg-white/70 border border-slate-200/80 hover:border-emerald-300 transition">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-900">Bank Branch or Post Office (IPPB)</span>
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800">
                    NPCI DBT Link
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Submit Aadhaar NPCI Seeding Mandate or open an instant DBT-enabled IPPB savings account.
                </p>
              </div>

              <div className="p-3 rounded-2xl bg-white/70 border border-slate-200/80 hover:border-emerald-300 transition">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-900">District Agriculture Officer (DAO)</span>
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-purple-100 text-purple-800">
                    Appeals & Tax Flag
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  File formal appeals with ITR non-filing declaration or Group-D pension proof (Clause PMK-A-2.0).
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
