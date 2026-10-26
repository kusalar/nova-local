import React from 'react';
import { 
  GitFork, 
  CheckCircle2, 
  Clock, 
  AlertTriangle, 
  XCircle, 
  Play, 
  RotateCcw, 
  ShieldAlert, 
  StopCircle,
  CornerDownRight,
  Bot
} from 'lucide-react';
import { WorkflowPlan, WorkflowStep, WorkflowStepStatus } from '../../types';

interface WorkflowExecutionGraphProps {
  plan: WorkflowPlan | null;
  onApproveStep: (stepId: number) => void;
  onCancelWorkflow: () => void;
  onResumeWorkflow: () => void;
  isExecuting: boolean;
}

export const WorkflowExecutionGraph: React.FC<WorkflowExecutionGraphProps> = ({
  plan,
  onApproveStep,
  onCancelWorkflow,
  onResumeWorkflow,
  isExecuting
}) => {
  if (!plan) {
    return (
      <div className="hud-panel p-8 rounded-lg border border-slate-800 bg-slate-900/40 text-center">
        <GitFork className="w-8 h-8 text-slate-600 mx-auto mb-2" />
        <div className="text-sm font-mono text-slate-400">NO ACTIVE WORKFLOW GRAPH</div>
        <div className="text-xs text-slate-500 mt-1">
          Decompose an objective in the Workflow Planner to generate an execution graph.
        </div>
      </div>
    );
  }

  const getStepStatusIcon = (status: WorkflowStepStatus) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
      case 'in_progress':
        return <Clock className="w-4 h-4 text-cyan-400 animate-spin" />;
      case 'waiting_approval':
        return <ShieldAlert className="w-4 h-4 text-purple-400 animate-bounce" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-rose-400" />;
      case 'cancelled':
      case 'skipped':
        return <StopCircle className="w-4 h-4 text-slate-500" />;
      case 'ready':
        return <Play className="w-4 h-4 text-amber-400" />;
      default:
        return <Clock className="w-4 h-4 text-slate-600" />;
    }
  };

  const getStatusBorder = (status: WorkflowStepStatus) => {
    switch (status) {
      case 'completed':
        return 'border-emerald-600/50 bg-emerald-950/20';
      case 'in_progress':
        return 'border-cyan-400 bg-cyan-950/30 shadow-[0_0_12px_rgba(6,182,212,0.2)]';
      case 'waiting_approval':
        return 'border-purple-400 bg-purple-950/40 shadow-[0_0_12px_rgba(168,85,247,0.25)]';
      case 'failed':
        return 'border-rose-500/60 bg-rose-950/30';
      default:
        return 'border-slate-800 bg-slate-950/50';
    }
  };

  const isWorkflowActive = plan.status === 'running' || plan.status === 'waiting_approval';

  return (
    <div className="hud-panel p-4 rounded-lg border border-cyan-800/40 bg-slate-900/60 flex flex-col gap-4">
      {/* Header controls */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <GitFork className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-mono font-semibold text-slate-200 uppercase">
              Workflow Execution Graph: {plan.workflow_id}
            </h3>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
              plan.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' :
              plan.status === 'failed' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40' :
              plan.status === 'waiting_approval' ? 'bg-purple-500/20 text-purple-400 border border-purple-500/40' :
              plan.status === 'running' ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40' :
              'bg-slate-800 text-slate-400'
            }`}>
              {plan.status}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {plan.objective}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {isWorkflowActive && (
            <button
              onClick={onCancelWorkflow}
              className="flex items-center gap-1.5 px-3 py-1 rounded bg-rose-600/80 hover:bg-rose-600 text-slate-100 font-mono text-xs transition-colors"
            >
              <StopCircle className="w-3.5 h-3.5" />
              Cancel Workflow
            </button>
          )}

          {plan.status === 'cancelled' && (
            <button
              onClick={onResumeWorkflow}
              className="flex items-center gap-1.5 px-3 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-mono text-xs font-semibold transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Resume Workflow
            </button>
          )}
        </div>
      </div>

      {/* Graph Timeline Nodes */}
      <div className="relative pl-6 space-y-3 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-800">
        {plan.steps.map((step) => {
          const isWaitingApproval = step.status === 'waiting_approval';
          const hasError = !!step.error;

          return (
            <div
              key={step.step_id}
              className={`relative p-3 rounded-lg border transition-all ${getStatusBorder(step.status)}`}
            >
              {/* Timeline marker */}
              <div className="absolute -left-[27px] top-3.5 p-0.5 rounded-full bg-slate-950 border border-slate-700">
                {getStepStatusIcon(step.status)}
              </div>

              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-cyan-400">
                      Step #{step.step_id}
                    </span>
                    <span className="text-xs font-semibold text-slate-200">
                      {step.description}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono text-slate-400">
                    <span className="text-cyan-400 flex items-center gap-1">
                      <Bot className="w-3 h-3" />
                      {step.assigned_agent}
                    </span>
                    {step.required_tool && (
                      <span className="text-emerald-400">
                        tool: {step.required_tool}
                      </span>
                    )}
                    {step.execution_time_ms !== undefined && (
                      <span className="text-slate-400">
                        {step.execution_time_ms} ms
                      </span>
                    )}
                    {step.retry_count > 0 && (
                      <span className="text-amber-400">
                        retries: {step.retry_count}/{step.max_retries}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {isWaitingApproval && (
                    <button
                      onClick={() => onApproveStep(step.step_id)}
                      className="flex items-center gap-1.5 px-3 py-1 rounded bg-purple-600 hover:bg-purple-500 text-white font-mono text-xs font-bold transition-colors shadow-[0_0_10px_rgba(168,85,247,0.3)] animate-pulse"
                    >
                      <ShieldAlert className="w-3.5 h-3.5" />
                      Review & Approve
                    </button>
                  )}
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 uppercase">
                    {step.status}
                  </span>
                </div>
              </div>

              {/* Error diagnostic display */}
              {hasError && (
                <div className="mt-2 p-2 rounded bg-rose-950/40 border border-rose-800/40 text-xs text-rose-300 font-mono">
                  <span className="font-bold text-rose-400">Error: </span>
                  {step.error}
                </div>
              )}

              {/* Result preview */}
              {step.result && (
                <div className="mt-2 p-2 rounded bg-slate-950/60 border border-slate-800/80 text-[11px] font-mono text-slate-300 max-h-24 overflow-y-auto custom-scrollbar">
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-0.5">
                    Step Output:
                  </div>
                  <pre className="whitespace-pre-wrap">
                    {typeof step.result === 'string' ? step.result : JSON.stringify(step.result, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
