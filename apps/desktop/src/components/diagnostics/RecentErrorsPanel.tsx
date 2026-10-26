import React, { useState } from 'react';
import { AlertTriangle, AlertCircle, RefreshCw, Filter, CheckCircle } from 'lucide-react';
import { RecentErrorItem } from '../../types';

interface RecentErrorsPanelProps {
  errors: RecentErrorItem[];
  isLoading: boolean;
  onRefresh: () => void;
}

export const RecentErrorsPanel: React.FC<RecentErrorsPanelProps> = ({
  errors,
  isLoading,
  onRefresh,
}) => {
  const [filterSubsystem, setFilterSubsystem] = useState<string>('all');
  const [filterSeverity, setFilterSeverity] = useState<string>('all');

  const subsystems = Array.from(new Set(errors.map((e) => e.subsystem)));

  const filtered = errors.filter((err) => {
    const sev = (err.severity || err.level || 'ERROR').toUpperCase();
    if (filterSubsystem !== 'all' && err.subsystem !== filterSubsystem) return false;
    if (filterSeverity !== 'all' && sev !== filterSeverity) return false;
    return true;
  });

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-sm">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
        <div>
          <h3 className="text-base font-semibold text-slate-100 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-400" />
            Recent Errors & Diagnostic Ring Buffer
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time memory buffer of anomalous events (capped at last 50 entries)
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors border border-slate-700"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2 mb-4 p-2.5 bg-slate-950/40 rounded-lg border border-slate-800/80">
        <Filter className="w-3.5 h-3.5 text-slate-400 ml-1" />
        <span className="text-xs text-slate-400 font-medium mr-1">Filter:</span>

        <select
          value={filterSubsystem}
          onChange={(e) => setFilterSubsystem(e.target.value)}
          className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
        >
          <option value="all">All Subsystems ({errors.length})</option>
          {subsystems.map((sub) => (
            <option key={sub} value={sub}>
              {sub}
            </option>
          ))}
        </select>

        <select
          value={filterSeverity}
          onChange={(e) => setFilterSeverity(e.target.value)}
          className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
        >
          <option value="all">All Severities</option>
          <option value="ERROR">ERROR</option>
          <option value="WARNING">WARNING</option>
          <option value="CRITICAL">CRITICAL</option>
        </select>

        {(filterSubsystem !== 'all' || filterSeverity !== 'all') && (
          <button
            onClick={() => {
              setFilterSubsystem('all');
              setFilterSeverity('all');
            }}
            className="text-xs text-cyan-400 hover:underline ml-auto"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Error List */}
      {filtered.length === 0 ? (
        <div className="text-center py-10 bg-slate-950/30 rounded-lg border border-dashed border-slate-800">
          <CheckCircle className="w-8 h-8 text-emerald-400/80 mx-auto mb-2" />
          <p className="text-sm font-medium text-slate-300">No anomalous events recorded</p>
          <p className="text-xs text-slate-500 mt-1">
            {errors.length > 0
              ? 'No events match the active filters.'
              : 'All subsystems are operating smoothly with clean execution buffers.'}
          </p>
        </div>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
          {filtered.map((item, idx) => {
            const sev = (item.severity || item.level || 'ERROR').toUpperCase();
            const isWarn = sev === 'WARNING';
            const isCrit = sev === 'CRITICAL';
            const traceback = item.traceback_summary || (item.details && item.details.traceback);
            return (
              <div
                key={idx}
                className={`p-3 rounded-lg border text-xs transition-colors ${
                  isCrit
                    ? 'bg-rose-950/30 border-rose-800/60 text-rose-200'
                    : isWarn
                    ? 'bg-amber-950/30 border-amber-800/60 text-amber-200'
                    : 'bg-red-950/20 border-red-900/50 text-red-200'
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold tracking-wider uppercase ${
                        isCrit
                          ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                          : isWarn
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                          : 'bg-red-500/20 text-red-300 border border-red-500/40'
                      }`}
                    >
                      {sev}
                    </span>
                    <span className="font-semibold text-slate-100">{item.subsystem}</span>
                  </div>
                  <span className="text-[11px] text-slate-400 font-mono">
                    {new Date(item.timestamp).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                    })}
                  </span>
                </div>

                <p className="text-slate-300 font-mono text-[11px] break-words my-1">{item.message}</p>

                {traceback && (
                  <details className="mt-2 text-[10px] font-mono text-slate-400 cursor-pointer">
                    <summary className="hover:text-slate-200">View safe exception context</summary>
                    <pre className="mt-1 p-2 bg-slate-950/80 rounded border border-slate-800 overflow-x-auto whitespace-pre-wrap text-slate-400">
                      {traceback}
                    </pre>
                  </details>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
