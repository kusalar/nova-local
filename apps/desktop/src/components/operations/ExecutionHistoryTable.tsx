import React, { useState } from 'react';
import { 
  History, 
  RotateCcw, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  RefreshCw, 
  ShieldCheck, 
  ShieldAlert,
  ChevronDown,
  ChevronRight,
  Filter
} from 'lucide-react';
import { ExecutionRecord } from '../../types';

interface ExecutionHistoryTableProps {
  executions: ExecutionRecord[];
  isLoading?: boolean;
  onRefresh: () => void;
  onRollback: (executionId: string) => Promise<void>;
}

export const ExecutionHistoryTable: React.FC<ExecutionHistoryTableProps> = ({
  executions,
  isLoading = false,
  onRefresh,
  onRollback
}) => {
  const [rollingBackId, setRollingBackId] = useState<string | null>(null);
  const [expandedRowId, setExpandedRowId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const handleRollbackClick = async (executionId: string) => {
    try {
      setRollingBackId(executionId);
      await onRollback(executionId);
    } finally {
      setRollingBackId(null);
    }
  };

  const filtered = executions.filter(e => {
    if (statusFilter === 'ALL') return true;
    if (statusFilter === 'REVERSIBLE') return e.is_reversible;
    return e.status === statusFilter;
  });

  return (
    <div className="flex flex-col h-full space-y-3 font-sans">
      {/* Controls */}
      <div className="flex items-center justify-between p-3 bg-nova-surface/60 rounded-xl border border-nova-border/60">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-nova-cyan" />
          <span className="text-xs font-bold text-slate-100 font-display tracking-wide">
            OPERATIONAL AUDIT LEDGER ({executions.length} Events)
          </span>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-nova-dark/80 border border-nova-border/70 rounded-lg px-2.5 py-1 text-xs text-slate-300 focus:outline-none focus:border-nova-cyan/60"
          >
            <option value="ALL">All Records</option>
            <option value="COMPLETED">Completed</option>
            <option value="FAILED">Failed</option>
            <option value="REVERSIBLE">Reversible Only</option>
          </select>

          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="p-1.5 rounded-lg bg-nova-dark/80 hover:bg-nova-dark text-slate-400 hover:text-nova-cyan border border-nova-border/70 transition-all"
            title="Refresh History"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-nova-cyan' : ''}`} />
          </button>
        </div>
      </div>

      {/* Table / List */}
      <div className="flex-1 overflow-y-auto pr-1 custom-scrollbar space-y-2">
        {isLoading && executions.length === 0 ? (
          <div className="flex items-center justify-center p-12 text-xs font-mono text-slate-400">
            Loading execution records...
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-12 text-slate-500 border border-dashed border-nova-border/50 rounded-xl font-mono text-xs">
            No execution records found matching filter.
          </div>
        ) : (
          filtered.map((item) => {
            const isExpanded = expandedRowId === item.execution_id;
            const canRollback = item.is_reversible && !item.is_rolled_back && item.status === 'COMPLETED';
            const isRolling = rollingBackId === item.execution_id;

            return (
              <div
                key={item.execution_id}
                className="bg-nova-surface/40 hover:bg-nova-surface/60 border border-nova-border/60 rounded-xl p-3 transition-all text-xs"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5 flex-1 min-w-0">
                    <button
                      onClick={() => setExpandedRowId(isExpanded ? null : item.execution_id)}
                      className="text-slate-400 hover:text-slate-200 transition-colors p-0.5"
                    >
                      {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                    </button>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-bold font-mono text-slate-100">
                          {item.tool_id}
                        </span>
                        <span className="text-[10px] font-mono text-slate-500">
                          {item.execution_id}
                        </span>
                        <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${
                          item.status === 'COMPLETED' ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-500/30' :
                          'bg-rose-950/40 text-rose-400 border border-rose-500/30'
                        }`}>
                          {item.status}
                        </span>
                        {item.is_rolled_back && (
                          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-purple-950/40 text-purple-300 border border-purple-500/30">
                            ROLLED BACK
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-3 mt-1 text-[11px] text-slate-400 font-mono">
                        <span>{item.category}</span>
                        <span>•</span>
                        <span>{item.duration_ms ? `${item.duration_ms}ms` : '< 1s'}</span>
                        <span>•</span>
                        <span>{new Date(item.started_at).toLocaleTimeString()}</span>
                      </div>
                    </div>
                  </div>

                  {/* Rollback Trigger */}
                  {canRollback && (
                    <button
                      onClick={() => handleRollbackClick(item.execution_id)}
                      disabled={isRolling}
                      className="px-3 py-1.5 rounded-lg text-[11px] font-mono font-semibold bg-purple-950/40 hover:bg-purple-900/60 text-purple-300 border border-purple-500/40 transition-all flex items-center gap-1.5 shadow-[0_0_10px_rgba(168,85,247,0.2)] disabled:opacity-50"
                      title="Undo this file operation safely"
                    >
                      {isRolling ? (
                        <RefreshCw className="w-3 h-3 animate-spin" />
                      ) : (
                        <RotateCcw className="w-3 h-3" />
                      )}
                      Rollback
                    </button>
                  )}
                </div>

                {/* Expanded Details Drawer */}
                {isExpanded && (
                  <div className="mt-3 pt-2.5 border-t border-nova-border/40 font-mono text-[11px] space-y-2">
                    <div>
                      <span className="text-slate-400 text-[10px] uppercase font-bold block mb-1">
                        Redacted Parameters:
                      </span>
                      <pre className="p-2 bg-nova-dark/80 rounded border border-nova-border/50 text-slate-300 overflow-x-auto text-[10px]">
                        {JSON.stringify(item.arguments, null, 2)}
                      </pre>
                    </div>

                    {item.result && (
                      <div>
                        <span className="text-emerald-400 text-[10px] uppercase font-bold block mb-1">
                          Execution Result:
                        </span>
                        <pre className="p-2 bg-nova-dark/80 rounded border border-nova-border/50 text-emerald-300 overflow-x-auto text-[10px]">
                          {JSON.stringify(item.result, null, 2)}
                        </pre>
                      </div>
                    )}

                    {item.error_message && (
                      <div>
                        <span className="text-rose-400 text-[10px] uppercase font-bold block mb-1">
                          Failure Diagnostics:
                        </span>
                        <pre className="p-2 bg-rose-950/30 rounded border border-rose-500/40 text-rose-300 overflow-x-auto text-[10px]">
                          {item.error_message}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
