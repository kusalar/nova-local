import React from 'react';
import { Clock, CheckCircle2, XCircle, AlertTriangle, ArrowLeft } from 'lucide-react';
import { AutomationHistoryRecord } from '../../types';

interface AutomationHistoryProps {
  automationId?: string;
  history: AutomationHistoryRecord[];
  onBack?: () => void;
}

export const AutomationHistory: React.FC<AutomationHistoryProps> = ({
  automationId,
  history,
  onBack,
}) => {
  const getStatusBadge = (status: string) => {
    switch (status.toUpperCase()) {
      case 'SUCCESS':
        return (
          <span className="flex items-center text-[10px] font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-500/30 px-2 py-0.5 rounded">
            <CheckCircle2 className="w-3 h-3 mr-1" /> SUCCESS
          </span>
        );
      case 'FAILED':
        return (
          <span className="flex items-center text-[10px] font-mono text-rose-400 bg-rose-950/40 border border-rose-500/30 px-2 py-0.5 rounded">
            <XCircle className="w-3 h-3 mr-1" /> FAILED
          </span>
        );
      case 'REQUIRES_APPROVAL':
        return (
          <span className="flex items-center text-[10px] font-mono text-purple-400 bg-purple-950/40 border border-purple-500/30 px-2 py-0.5 rounded">
            <AlertTriangle className="w-3 h-3 mr-1" /> APPROVAL REQ
          </span>
        );
      case 'SKIPPED':
        return (
          <span className="flex items-center text-[10px] font-mono text-amber-400 bg-amber-950/40 border border-amber-500/30 px-2 py-0.5 rounded">
            <Clock className="w-3 h-3 mr-1" /> SKIPPED
          </span>
        );
      default:
        return (
          <span className="text-[10px] font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-4 p-5 bg-slate-900/60 rounded-xl border border-cyan-500/20 shadow-lg shadow-cyan-950/20">
      <div className="flex items-center justify-between pb-3 border-b border-cyan-500/20">
        <div className="flex items-center space-x-3">
          {onBack && (
            <button
              onClick={onBack}
              className="p-1 rounded text-slate-400 hover:text-cyan-400 hover:bg-slate-800 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
          )}
          <div>
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <Clock className="w-4 h-4 text-cyan-400" />
              Automation Execution Audit Trail
            </h3>
            <p className="text-xs text-slate-400 font-mono">
              {automationId ? `Viewing execution logs for routine: ${automationId}` : 'Recent execution audit logs'}
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-2 max-h-96 overflow-y-auto pr-1 custom-scrollbar">
        {history.length === 0 ? (
          <div className="text-center py-10 text-slate-500 font-mono text-xs border border-dashed border-slate-800 rounded-lg">
            No execution history records found.
          </div>
        ) : (
          history.map(record => (
            <div
              key={record.id}
              className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 flex flex-col space-y-1.5"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  {getStatusBadge(record.status)}
                  <span className="text-[11px] font-mono text-cyan-300">
                    {record.automation_id}
                  </span>
                  <span className="text-[10px] font-mono text-slate-500">
                    [{record.action_type}]
                  </span>
                </div>
                <span className="text-[10px] font-mono text-slate-400">
                  {new Date(record.started_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                </span>
              </div>

              {record.result_summary && (
                <p className="text-xs text-slate-300 font-mono whitespace-pre-wrap">
                  {record.result_summary}
                </p>
              )}

              {record.error_message && (
                <p className="text-xs text-rose-400 font-mono whitespace-pre-wrap">
                  Error: {record.error_message}
                </p>
              )}

              {record.workflow_id && (
                <span className="text-[10px] text-cyan-400/80 font-mono">
                  Linked Workflow: {record.workflow_id}
                </span>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
