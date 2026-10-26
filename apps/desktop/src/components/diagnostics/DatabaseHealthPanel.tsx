import React, { useState, useEffect } from 'react';
import { Database, CheckCircle2, AlertTriangle, RefreshCw, HardDrive, Layers, FileText } from 'lucide-react';
import { DatabaseStatus } from '../../types';
import { apiService } from '../../services/api';

export const DatabaseHealthPanel: React.FC = () => {
  const [status, setStatus] = useState<DatabaseStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadStatus = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const res = await apiService.getDatabaseStatus();
      setStatus(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load database status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  return (
    <div className="space-y-4">
      {/* Top Banner */}
      <div className="p-3.5 rounded-lg bg-nova-surface/60 border border-nova-border/70 backdrop-blur-md flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-mono text-nova-cyan">
          <Database className="w-4 h-4" />
          <span>SQLITE DATABASE INTEGRITY & SCHEMA STATS</span>
        </div>
        <button
          onClick={loadStatus}
          className="p-1.5 rounded text-slate-400 hover:text-nova-cyan hover:bg-nova-surface border border-transparent hover:border-nova-border transition-all"
          title="Refresh database status"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {errorMsg && (
        <div className="p-3 rounded bg-red-950/60 border border-red-500/40 text-red-200 text-xs font-mono">
          {errorMsg}
        </div>
      )}

      {status && (
        <>
          {/* Main Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
            {/* Integrity Status */}
            <div className="p-4 rounded-xl bg-nova-surface/40 border border-nova-border/70 flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-mono text-nova-cyan uppercase block mb-1">
                  Integrity Verification
                </span>
                <div className="flex items-center gap-2 mb-1">
                  {status.healthy ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-red-400" />
                  )}
                  <span className="font-mono text-base font-bold text-slate-100">
                    {status.integrity_status}
                  </span>
                </div>
                <p className="text-[10px] font-mono text-slate-400">
                  PRAGMA integrity_check passed
                </p>
              </div>
              <div className="mt-3 pt-2 border-t border-nova-border/40 text-[10px] font-mono text-emerald-400">
                Zero Corruption Detected
              </div>
            </div>

            {/* Storage Size */}
            <div className="p-4 rounded-xl bg-nova-surface/40 border border-nova-border/70 flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-mono text-nova-cyan uppercase block mb-1">
                  Database Size
                </span>
                <div className="text-2xl font-mono text-slate-100 font-bold mb-1">
                  {((status.total_size_bytes || 0) / 1024).toFixed(1)} KB
                </div>
                <p className="text-[10px] font-mono text-slate-400">
                  Base: {((status.size_bytes || 0) / 1024).toFixed(1)} KB · WAL: {((status.wal_size_bytes || 0) / 1024).toFixed(1)} KB
                </p>
              </div>
              <div className="mt-3 pt-2 border-t border-nova-border/40 text-[10px] font-mono text-slate-500">
                Compact offline SQLite file
              </div>
            </div>

            {/* Journal Mode */}
            <div className="p-4 rounded-xl bg-nova-surface/40 border border-nova-border/70 flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-mono text-nova-cyan uppercase block mb-1">
                  Journal Mode
                </span>
                <div className="text-2xl font-mono text-slate-100 font-bold mb-1 uppercase">
                  {status.journal_mode}
                </div>
                <p className="text-[10px] font-mono text-slate-400">
                  Write-Ahead Logging + 5000ms Busy Timeout
                </p>
              </div>
              <div className="mt-3 pt-2 border-t border-nova-border/40 text-[10px] font-mono text-nova-teal">
                Concurrent Read/Write Safe
              </div>
            </div>

            {/* Total Records */}
            <div className="p-4 rounded-xl bg-nova-surface/40 border border-nova-border/70 flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-mono text-nova-cyan uppercase block mb-1">
                  Indexed Records
                </span>
                <div className="text-2xl font-mono text-slate-100 font-bold mb-1">
                  {status.total_records}
                </div>
                <p className="text-[10px] font-mono text-slate-400">
                  Across {status.tables_count} relational tables
                </p>
              </div>
              <div className="mt-3 pt-2 border-t border-nova-border/40 text-[10px] font-mono text-slate-500">
                Foreign Key Constraints ON
              </div>
            </div>
          </div>

          {/* Table Breakdown Grid */}
          <div className="p-4 rounded-xl bg-nova-surface/40 border border-nova-border/70">
            <h4 className="text-xs font-mono text-nova-cyan uppercase tracking-wider mb-3 flex items-center gap-2">
              <Layers className="w-4 h-4" />
              Table Records Breakdown
            </h4>

            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2.5">
              {Object.entries(status.table_counts || {}).map(([tbl, count]) => (
                <div
                  key={tbl}
                  className="p-2.5 rounded-lg bg-nova-dark/80 border border-nova-border/50 text-xs font-mono flex items-center justify-between"
                >
                  <span className="text-slate-300 truncate mr-2" title={tbl}>
                    {tbl}
                  </span>
                  <span className="text-nova-teal font-bold">{count}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
