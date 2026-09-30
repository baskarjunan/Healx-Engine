"use client";

import { useEffect, useState } from "react";

// Python FastAPI Backend JSON structure-க்கு ஏற்ப அமைக்கப்பட்ட TypeScript Interface
interface BackendMetrics {
  total_processed: number;
  auto_healed: number;
  fines_prevented_usd: number;
  unresolved_count: number;
}

export default function Home() {
  const [metrics, setMetrics] = useState<BackendMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchMetrics = async () => {
    try {
      // Direct Python FastAPI Backend Endpoint Call
      const res = await fetch("http://127.0.0.1:8000/api/v1/dashboard/metrics", {
        cache: "no-store",
      });
      if (res.ok) {
        const data: BackendMetrics = await res.json();
        setMetrics(data);
      }
    } catch (err) {
      console.error("HealX Metrics Fetch Error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // 1. Initial Load
    fetchMetrics();

    // 2. Real-time Auto Refresh (ஒவ்வொரு 3 வினாடிக்கும் தானாக API-ஐ அழைத்து Data Update செய்யும்)
    const interval = setInterval(() => {
      fetchMetrics();
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  // Calculated Metrics
  const activeMessages = metrics?.total_processed || 0;
  const selfHealed = metrics?.auto_healed || 0;
  const healRate = activeMessages > 0 ? ((selfHealed / activeMessages) * 100).toFixed(1) : "0.0";
  const totalSavedUsd = metrics?.fines_prevented_usd || 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-950 text-slate-200">
        <p className="text-lg font-medium animate-pulse">
          Connecting to HealX Engine Gateway...
        </p>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Header Section */}
        <div className="border-b border-slate-800 pb-5 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-emerald-400">
              HealX Engine Gateway
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              CargoWise Automated eDocs Reconciliation & Self-Healing Middleware
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
            <span className="px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded-full text-xs font-semibold">
              Live Engine Active
            </span>
          </div>
        </div>

        {/* Operational Metrics Section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Active Processed XMLs
            </h3>
            <p className="text-4xl font-extrabold text-white mt-3">
              {activeMessages.toLocaleString()}
            </p>
            <p className="text-xs text-slate-500 mt-2">
              Total CargoWise Payloads Intercepted
            </p>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Self-Healed Discrepancies
            </h3>
            <p className="text-4xl font-extrabold text-emerald-400 mt-3">
              {selfHealed.toLocaleString()}
            </p>
            <p className="text-xs text-slate-500 mt-2">
              Auto-corrected weight/container typos
            </p>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Heal Success Rate
            </h3>
            <p className="text-4xl font-extrabold text-blue-400 mt-3">
              {healRate}%
            </p>
            <p className="text-xs text-slate-500 mt-2">
              Automated pre-ingestion resolution
            </p>
          </div>
        </div>

        {/* Cost Savings Summary Section */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-bold text-white mb-4">
            Financial Fine Prevention & Audit Summary
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="bg-slate-950 p-5 rounded-lg border border-slate-800/80">
              <p className="text-xs font-medium text-slate-400 uppercase">
                Port & Demurrage Fines Saved
              </p>
              <p className="text-2xl font-bold text-emerald-400 mt-2">
                ${totalSavedUsd.toLocaleString("en-US", { minimumFractionDigits: 2 })} USD
              </p>
            </div>

            <div className="bg-slate-950 p-5 rounded-lg border border-slate-800/80">
              <p className="text-xs font-medium text-slate-400 uppercase">
                Critical Exceptions
              </p>
              <p className="text-2xl font-bold text-rose-500 mt-2">
                {metrics?.unresolved_count || 0} Alerts
              </p>
            </div>

            <div className="bg-slate-950 p-5 rounded-lg border border-slate-800/80">
              <p className="text-xs font-medium text-slate-400 uppercase">
                Target Gateway Status
              </p>
              <p className="text-2xl font-bold text-yellow-400 mt-2">
                eAdaptor Ingest Ready
              </p>
            </div>
          </div>
        </div>

      </div>
    </main>
  );
}