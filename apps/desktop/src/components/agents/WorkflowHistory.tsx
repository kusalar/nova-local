import React from 'react';
import { 
  History, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  GitFork, 
  ChevronRight,
  RotateCcw
} from 'lucide-react';
import { WorkflowSummary, WorkflowStatus } from '../../types';

interface WorkflowHistoryProps {
  workflows: WorkflowSummary[];
  selectedWorkflowId: string | null;
  onSelectWorkflow: (workflowId: string) => void;
  isLoading: boolean;
  onRefresh: () => void;
}

export const WorkflowHistory: React.FC<WorkflowHistoryProps> = ({
  workflows,
  selectedWorkflowId,
  onSelectWorkflow,
  isLoading,
  onRefresh
}) => {
  const getStatusBadge = (status: WorkflowStatus) => {
    switch (status) {
      case 'completed':
        return (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            COMPLETED
          </span>
        );
      case 'failed':
        return (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/30">
            FAILED
          </span>
        );
      case 'waiting_approval':
        return (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/30">
            APPROVAL
          </span>
        );
      case 'running':
        return (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
            RUNNING
          </span>
        );
      default:
        return (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
            {status.toUpperCase()}
          </span>
        );
    }
  };

  return (
    <div className="h-full flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-semibold font-mono text-cyan-300 uppercase flex items-center gap-1.5">
            <History className="w-4 h-4 text-cyan-400" />
            Persistent Workflow Logs
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Audit history of multi-agent plans and execution outcomes in SQLite
          </p>
        </div>
        <button
          onClick={onRefresh}
          className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
          title="Refresh Workflows"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      </div>

      {isLoading ? (
        <div className="p-8 text-center text-xs font-mono text-slate-500">
          Loading workflow history...
        </div>
      ) : workflows.length === 0 ? (
        <div className="hud-panel p-8 rounded-lg border border-slate-800 text-center">
          <GitFork className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <div className="text-xs font-mono text-slate-400">NO PRIOR WORKFLOWS FOUND</div>
          <div className="text-[11px] text-slate-500 mt-1">
            Run an agentic objective to record execution logs.
          </div>
        </div>
      ) : (
        <div className="space-y-2 max-h-[500px] overflow-y-auto custom-scrollbar pr-1">
          {workflows.map((wf) => {
            const isSelected = selectedWorkflowId === wf.workflow_id;

            return (
              <div
                key={wf.workflow_id}
                onClick={() => onSelectWorkflow(wf.workflow_id)}
                className={`p-3 rounded-lg border transition-all cursor-pointer flex items-center justify-between gap-3 ${
                  isSelected
                    ? 'bg-cyan-950/40 border-cyan-400 shadow-[0_0_12px_rgba(6,182,212,0.15)]'
                    : 'bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-800/40'
                }`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-slate-200">
                      {wf.workflow_id}
                    </span>
                    {getStatusBadge(wf.status)}
                  </div>
                  <p className="text-xs text-slate-300 line-clamp-1">
                    {wf.objective}
                  </p>
                  <div className="flex items-center gap-3 text-[11px] font-mono text-slate-500">
                    <span>{wf.step_count} steps</span>
                    <span>{new Date(wf.created_at).toLocaleString()}</span>
                  </div>
                </div>

                <div className="flex items-center text-slate-500">
                  <ChevronRight className="w-4 h-4" />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
