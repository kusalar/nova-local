import React from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  Clock, 
  RefreshCw, 
  Ban, 
  ChevronRight, 
  Terminal,
  AlertTriangle,
  RotateCcw
} from 'lucide-react';
import { TaskPlan, TaskStep, StepStatus } from '../../types';

interface ExecutionTimelineProps {
  task: TaskPlan | null;
  onCancelTask?: (taskId: string) => void;
  onRollback?: (executionId: string) => void;
}

export const ExecutionTimeline: React.FC<ExecutionTimelineProps> = ({
  task,
  onCancelTask,
  onRollback
}) => {
  if (!task) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-slate-500 border border-dashed border-nova-border/60 rounded-xl font-mono text-xs">
        Select a planned or executed task to view the execution timeline.
      </div>
    );
  }

  const getStatusIcon = (status: StepStatus) => {
    switch (status) {
      case 'COMPLETED':
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
      case 'RUNNING':
        return <RefreshCw className="w-4 h-4 text-nova-cyan animate-spin" />;
      case 'FAILED':
        return <XCircle className="w-4 h-4 text-rose-400" />;
      case 'CANCELLED':
      case 'SKIPPED':
        return <Ban className="w-4 h-4 text-slate-500" />;
      default:
        return <Clock className="w-4 h-4 text-slate-500" />;
    }
  };

  const completedSteps = task.steps.filter(s => s.status === 'COMPLETED').length;
  const progressPercent = task.steps.length > 0 ? (completedSteps / task.steps.length) * 100 : 0;

  return (
    <div className="flex flex-col h-full space-y-3 font-sans">
      {/* Header with Progress Bar */}
      <div className="p-3.5 bg-nova-surface/60 rounded-xl border border-nova-border/60 space-y-2.5">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-slate-100 font-display">
                Execution Timeline
              </span>
              <span className="text-[10px] font-mono text-nova-cyan bg-nova-cyan/10 px-1.5 py-0.5 rounded border border-nova-cyan/30">
                {task.task_id}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5 font-sans">
              {task.description}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
              task.status === 'COMPLETED' ? 'bg-emerald-950/40 text-emerald-400 border-emerald-500/30' :
              task.status === 'PENDING_APPROVAL' ? 'bg-amber-950/40 text-amber-400 border-amber-500/30' :
              task.status === 'FAILED' ? 'bg-rose-950/40 text-rose-400 border-rose-500/30' :
              task.status === 'EXECUTING' ? 'bg-cyan-950/40 text-cyan-400 border-cyan-500/30' :
              'bg-slate-800 text-slate-400 border-slate-700'
            }`}>
              {task.status}
            </span>

            {onCancelTask && (task.status === 'EXECUTING' || task.status === 'PENDING_APPROVAL') && (
              <button
                onClick={() => onCancelTask(task.task_id)}
                className="px-2.5 py-1 rounded text-[11px] font-mono text-rose-400 hover:text-rose-300 hover:bg-rose-950/30 border border-rose-500/30 transition-all flex items-center gap-1"
              >
                <Ban className="w-3 h-3" />
                Cancel
              </button>
            )}
          </div>
        </div>

        {/* Progress Bar */}
        <div>
          <div className="flex justify-between text-[10px] font-mono text-slate-400 mb-1">
            <span>Progress: {completedSteps} of {task.steps.length} steps</span>
            <span>{Math.round(progressPercent)}%</span>
          </div>
          <div className="w-full h-1.5 bg-nova-dark/80 rounded-full overflow-hidden border border-nova-border/50">
            <div
              className="h-full bg-nova-cyan transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* Steps List */}
      <div className="flex-1 overflow-y-auto space-y-2.5 pr-1 custom-scrollbar">
        {task.steps.map((step, idx) => (
          <div
            key={step.step_id}
            className={`p-3 rounded-xl border text-xs transition-all ${
              step.status === 'RUNNING'
                ? 'bg-nova-cyan/5 border-nova-cyan/40 shadow-[0_0_15px_rgba(0,240,255,0.1)]'
                : step.status === 'COMPLETED'
                ? 'bg-emerald-950/10 border-emerald-500/30'
                : step.status === 'FAILED'
                ? 'bg-rose-950/20 border-rose-500/40'
                : 'bg-nova-surface/40 border-nova-border/50 opacity-80'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                {getStatusIcon(step.status)}
                <span className="font-bold font-mono text-slate-100">
                  Step {step.step_id}: {step.tool_id}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-slate-400">
                  {step.status}
                </span>
                {step.execution_id && (
                  <span className="text-[9px] font-mono text-slate-500">
                    {step.execution_id}
                  </span>
                )}
              </div>
            </div>

            <p className="text-[11px] text-slate-300 font-sans ml-6">
              {step.description}
            </p>

            {/* Error Message if Failed */}
            {step.error && (
              <div className="mt-2 ml-6 p-2 rounded bg-rose-950/30 border border-rose-500/30 text-[11px] font-mono text-rose-300 flex items-start gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-rose-400" />
                <span>{step.error}</span>
              </div>
            )}

            {/* Result Payload Preview */}
            {step.result && (
              <div className="mt-2 ml-6 p-2 rounded bg-nova-dark/80 border border-nova-border/50 text-[10px] font-mono text-emerald-400 overflow-x-auto">
                <pre>{JSON.stringify(step.result, null, 2)}</pre>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
