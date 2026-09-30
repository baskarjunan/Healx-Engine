"use client";
import { useState, useEffect } from "react";

export default function Home() {
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/v1/dashboard/metrics")
      .then((res) => res.json())
      .then((data) => setMetrics(data))
      .catch((err) => console.error("Error fetching metrics:", err));
  }, []);

  if (!metrics) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-900 text-cyan-400 font-bold">
        HealX Engine Loading Metrics...
      </div>
    );
  }

  return (
    <div className="bg-slate-900 min-h-screen text-white p-8 font-sans">
      <div className="flex justify-between items-center border-b border-slate-700 pb-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-cyan-400">HEALX XML SELF-HEALING MIDDLEWARE</h1>
          <p className="text-xs text-slate-400">CARGOWISE INTEGRATION DASHBOARD | SYSTEM STATUS: <span className="text-green-400 font-semibold">OPERATIONAL</span></p>
        </div>
        <div className="bg-slate-800 px-4 py-2 rounded-lg border border-cyan-500/30">
          <span className="text-xs text-slate-400">DATA LEAKAGE SHIELD</span>
          <p className="text-green-400 font-bold text-sm">ACTIVE - 100% SECURE</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6 mb-8">
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
          <p className="text-xs text-slate-400 uppercase tracking-wider">Active Messages Processing</p>
          <p className="text-3xl font-bold text-cyan-400 mt-2">{metrics.active_messages}</p>
        </div>
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
          <p className="text-xs text-slate-400 uppercase tracking-wider">Messages Self-Healed</p>
          <p className="text-3xl font-bold text-yellow-400 mt-2">{metrics.self_healed} <span className="text-sm text-green-400">({metrics.heal_rate}%)</span></p>
        </div>
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
          <p className="text-xs text-slate-400 uppercase tracking-wider">Total Operational Cost Saved</p>
          <p className="text-3xl font-bold text-green-400 mt-2">${metrics.total_saved_usd} USD</p>
        </div>
      </div>
    </div>
  );
}