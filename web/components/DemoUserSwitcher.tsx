"use client";

import React, { useState, useEffect } from "react";
import { Locale } from "@/lib/i18n";

interface DemoUser {
  id: string;
  name: string;
  mobile: string;
  district: string;
  state: string;
  land_area_ha: number;
  initial_status: string;
  profile: any;
}

interface DemoUserSwitcherProps {
  locale: Locale;
  onSelectUser: (user: DemoUser) => void;
  selectedUserId?: string;
}

export default function DemoUserSwitcher({
  locale,
  onSelectUser,
  selectedUserId = "user_ram_prasad",
}: DemoUserSwitcherProps) {
  const [users, setUsers] = useState<DemoUser[]>([]);
  const [currentId, setCurrentId] = useState(selectedUserId);

  useEffect(() => {
    fetch("http://localhost:8000/demo-users")
      .then((res) => (res.ok ? res.json() : []))
      .then((data: DemoUser[]) => {
        setUsers(data);
      })
      .catch(() => {});
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    setCurrentId(val);
    const found = users.find((u) => u.id === val);
    if (found) {
      onSelectUser(found);
    }
  };

  if (!users || users.length === 0) return null;

  return (
    <div className="flex items-center gap-1.5 text-xs">
      <span className="hidden md:inline font-bold text-emerald-200/90">
        {locale === "hi" ? "डेमो किसान:" : "Demo Farmer:"}
      </span>
      <select
        value={currentId}
        onChange={handleChange}
        className="px-2.5 py-1.5 bg-white/10 hover:bg-white/20 text-white font-bold rounded-xl border border-white/20 text-xs outline-none cursor-pointer transition shadow-xs backdrop-blur-md [&>option]:bg-slate-900 [&>option]:text-white"
      >
        {users.map((u) => (
          <option key={u.id} value={u.id}>
            {u.name} ({u.land_area_ha} Ha • {u.initial_status})
          </option>
        ))}
      </select>
    </div>
  );
}
