"use client";

import { useState, useRef, useEffect } from "react";
import { Locale, SUPPORTED_LANGUAGES } from "@/lib/i18n";
import { Globe2Icon, ChevronDownIcon, CheckIcon } from "./icons";

interface Props {
  locale: Locale;
  onChange: (locale: Locale) => void;
}

export default function LanguageSwitcher({ locale, onChange }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const activeLang = SUPPORTED_LANGUAGES.find((l) => l.code === locale) || SUPPORTED_LANGUAGES[0];

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-white/95 bg-white/10 hover:bg-white/20 border border-white/20 backdrop-blur-md transition shadow-xs"
        title="Change Language / भाषा बदलें"
      >
        <Globe2Icon className="w-4 h-4 text-emerald-300" />
        <span className="font-bold tracking-tight">{activeLang.nativeLabel}</span>
        <span className="text-[10px] text-emerald-200 uppercase font-mono">({activeLang.code})</span>
        <ChevronDownIcon className={`w-3.5 h-3.5 text-emerald-200 transition-transform ${isOpen ? "rotate-180" : ""}`} />
      </button>

      {/* Glassmorphic Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-64 rounded-2xl glass-panel border border-emerald-500/20 shadow-2xl p-1.5 z-50 animate-in fade-in zoom-in-95 duration-100">
          <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-emerald-800 border-b border-emerald-500/10 mb-1 flex items-center justify-between">
            <span>Select Indian Language</span>
            <span className="text-emerald-600 font-mono text-[9px] bg-emerald-100/60 px-1.5 py-0.5 rounded">
              9 Languages
            </span>
          </div>

          <div className="max-h-72 overflow-y-auto space-y-0.5">
            {SUPPORTED_LANGUAGES.map((lang) => {
              const isSelected = lang.code === locale;
              return (
                <button
                  key={lang.code}
                  onClick={() => {
                    onChange(lang.code);
                    setIsOpen(false);
                  }}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-left text-xs transition ${
                    isSelected
                      ? "bg-emerald-600 text-white font-bold shadow-xs"
                      : "text-slate-800 hover:bg-emerald-50 hover:text-emerald-900"
                  }`}
                >
                  <div className="flex flex-col">
                    <span className="text-sm font-semibold">{lang.nativeLabel}</span>
                    <span className={`text-[10px] ${isSelected ? "text-emerald-100" : "text-slate-400"}`}>
                      {lang.label} • {lang.region}
                    </span>
                  </div>
                  {isSelected && <CheckIcon className="w-4 h-4 text-white shrink-0" />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
