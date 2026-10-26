import React, { useState, useEffect } from 'react';
import { Cpu, HardDrive, Server, Activity, RefreshCw } from 'lucide-react';
import { apiService } from '../../services/api';

export const ResourceMonitor: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const loadMetrics = async () => {
    try {
      setLoading(true);
      const res = await apiService.getResourceMetrics();
      setData(res);
    } catch (err) {
      console.error('Failed to load resource metrics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMetrics();
    const interval = setInterval(loadMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  const cpu = data?.cpu || { percent: 0, core_count: 4 };
  const ram = data?.ram || { percent: 0, used_gb: 0, total_gb: 12 };
  const concurrency = data?.concurrency_limits || {
    active_inferences: 0,
    queued_inferences: 0,
    max_concurrent_inferences: 1,
    active_ocr: 0,
    max_concurrent_ocr: 1,
  };

  return (
    <div className="space-y-4">
      {/* Top Banner */}
      <div className="p-3.5 rounded-lg bg-nova-surface/60 border border-nova-border/70 backdrop-blur-md flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-mono text-nova-cyan">
          <Activity className="w-4 h-4" />
          <span>HARDWARE WORKLOAD & CONCURRENCY COORDINATOR</span>
        </div>
        <button
          onClick={loadMetrics}
          className="p-1.5 rounded text-slate-400 hover:text-nova-cyan hover:bg-nova-surface border border-transparent hover:border-nova-border transition-all"
          title="Refresh metrics"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {/* CPU Card */}
        <div className="p-4 rounded-xl bg-nova-surface/40 border border-nova-border/70 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-nova-cyan flex items-center gap-1.5">
              <Cpu className="w-4 h-4" />
              PROCESSOR LOAD
            </span>
            <span className="text-[10px] font-mono text-slate-400">{cpu.core_count} Cores</span>
          </div>
          <div className="text-2xl font-mono text-slate-100 font-bold mb-1">
            {cpu.percent}%
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 mt-2 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                cpu.percent > 85 ? 'bg-red-500' : cpu.percent > 60 ? 'bg-amber-400' : 'bg-nova-cyan'
              }`}
              style={{ width: `${Math.min(100, Math.max(0, cpu.percent))}%` }}
            />
          </div>
        </div>

        {/* RAM Card */}
        <div className="p-4 rounded-xl bg-nova-surface/40 border border-nova-border/70 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-nova-cyan flex items-center gap-1.5">
              <Server className="w-4 h-4" />
              SYSTEM MEMORY
            </span>
            <span className="text-[10px] font-mono text-slate-400">{ram.total_gb} GB</span>
          </div>
          <div className="text-2xl font-mono text-slate-100 font-bold mb-1">
            {ram.percent}%
          </div>
          <div className="text-[11px] font-mono text-slate-400">
            {ram.used_gb} GB used
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 mt-2 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                ram.percent > 85 ? 'bg-red-500' : ram.percent > 65 ? 'bg-amber-400' : 'bg-nova-teal'
              }`}
              style={{ width: `${Math.min(100, Math.max(0, ram.percent))}%` }}
            />
          </div>
        </div>

        {/* Ollama Concurrency Card */}
        <div className="p-4 rounded-xl bg-nova-surface/40 border border-nova-border/70 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-nova-cyan">LLM INFERENCE SLOTS</span>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-nova-dark border border-nova-border text-slate-300">
              Max {concurrency.max_concurrent_inferences}
            </span>
          </div>
          <div className="text-2xl font-mono text-slate-100 font-bold mb-1">
            {concurrency.active_inferences} Active
          </div>
          <p className="text-[11px] font-mono text-slate-400">
            Queued: {concurrency.queued_inferences} (Backpressure limit 5)
          </p>
          <div className="mt-2 text-[10px] font-mono text-emerald-400 flex items-center gap-1">
            <span>CPU Saturation Protection Active</span>
          </div>
        </div>

        {/* OCR Concurrency Card */}
        <div className="p-4 rounded-xl bg-nova-surface/40 border border-nova-border/70 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-nova-cyan">OCR PROCESS SLOTS</span>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-nova-dark border border-nova-border text-slate-300">
              Max {concurrency.max_concurrent_ocr}
            </span>
          </div>
          <div className="text-2xl font-mono text-slate-100 font-bold mb-1">
            {concurrency.active_ocr} Active
          </div>
          <p className="text-[11px] font-mono text-slate-400">
            Windows Media OCR engine
          </p>
          <div className="mt-2 text-[10px] font-mono text-nova-teal">
            <span>Isolated Screen Frame Capture</span>
          </div>
        </div>
      </div>
    </div>
  );
};
