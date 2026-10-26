import React, { useState } from 'react';
import { 
  Sparkles, 
  Send, 
  AlertCircle, 
  CheckCircle2, 
  Bot, 
  ShieldAlert, 
  Play, 
  Layers, 
  RefreshCw,
  FolderGit2
} from 'lucide-react';
import { WorkflowPlan, WorkflowStep } from '../../types';

interface WorkflowPlannerProps {
  onPlanWorkflow: (objective: string, projectId?: string) => Promise<WorkflowPlan | null>;
  onExecuteWorkflow: (workflowId: string) => Promise<void>;
  activePlan: WorkflowPlan | null;
  isPlanning: boolean;
  isExecuting: boolean;
}

export const WorkflowPlanner: React.FC<WorkflowPlannerProps> = ({
  onPlanWorkflow,
  onExecuteWorkflow,
  activePlan,
  isPlanning,
  isExecuting
}) => {
  const [objective, setObjective] = useState('');
  const [projectId, setProjectId] = useState('NOVA-v0.6');

  const presetObjectives = [
    "Inspect my NOVA project, run its tests, and tell me what needs improvement.",
    "Analyze the error on my screen and explain how to resolve it.",
    "Inspect system health and find high resource usage processes.",
    "Review memory and summarize active project workflows."
  ];

  const handlePlanSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!objective.trim() || isPlanning) return;
    await onPlanWorkflow(objective.trim(), projectId.trim() || undefined);
  };

  const handlePresetClick = (preset: string) => {
    setObjective(preset);
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Input Form */}
      <div className="hud-panel p-4 rounded-lg border border-cyan-800/40 bg-slate-900/60">
        <div className="flex items-center justify-between mb-2">
          <label className="text-xs font-mono font-semibold text-cyan-300 flex items-center gap-1.5 uppercase">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            High-Level Objective Decomposition
          </label>
          <div className="flex items-center gap-2">
            <FolderGit2 className="w-3.5 h-3.5 text-slate-400" />
            <input
              type="text"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              placeholder="Project ID..."
              className="px-2 py-0.5 text-xs font-mono rounded bg-slate-950 border border-slate-700 text-slate-200 focus:outline-none focus:border-cyan-500 w-32"
            />
          </div>
        </div>

        <form onSubmit={handlePlanSubmit} className="space-y-3">
          <div className="relative">
            <textarea
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              placeholder="Enter complex multi-agent objective (e.g. 'Inspect my NOVA project, run its tests, and tell me what needs improvement')..."
              rows={3}
              className="w-full px-3 py-2 text-xs font-sans rounded-md bg-slate-950/80 border border-slate-700/80 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-400 transition-colors custom-scrollbar"
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap gap-1.5 items-center">
              <span className="text-[10px] font-mono text-slate-500 uppercase">Presets:</span>
              {presetObjectives.map((p, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => handlePresetClick(p)}
                  className="text-[10px] px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
                >
                  {p.slice(0, 32)}...
                </button>
              ))}
            </div>

            <button
              type="submit"
              disabled={isPlanning || !objective.trim()}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-md font-mono text-xs font-semibold uppercase bg-cyan-600 hover:bg-cyan-500 text-slate-950 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_10px_rgba(6,182,212,0.3)]"
            >
              {isPlanning ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Decomposing Objective...
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  Generate Multi-Agent Plan
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Plan Preview */}
      {activePlan && (
        <div className="hud-panel p-4 rounded-lg border border-cyan-800/40 bg-slate-900/60 flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div>
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-cyan-400" />
                <h3 className="text-xs font-mono font-semibold text-slate-200 uppercase">
                  Structured Workflow Plan: {activePlan.workflow_id}
                </h3>
              </div>
              <p className="text-xs text-slate-400 mt-0.5 italic">
                "{activePlan.objective}"
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-cyan-300 border border-slate-700">
                {activePlan.steps.length} Steps Planned
              </span>
              {activePlan.status === 'planned' && (
                <button
                  onClick={() => onExecuteWorkflow(activePlan.workflow_id)}
                  disabled={isExecuting}
                  className="flex items-center gap-1.5 px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-mono text-xs font-bold uppercase transition-colors shadow-[0_0_10px_rgba(16,185,129,0.3)]"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  {isExecuting ? 'Executing...' : 'Execute Workflow'}
                </button>
              )}
            </div>
          </div>

          {/* Steps List Preview */}
          <div className="space-y-2 max-h-96 overflow-y-auto custom-scrollbar pr-1">
            {activePlan.steps.map((step) => {
              const isConfirmationRequired = step.permission_level === 'CONFIRMATION_REQUIRED';
              
              return (
                <div
                  key={step.step_id}
                  className="p-2.5 rounded border border-slate-800 bg-slate-950/60 flex items-start justify-between gap-3"
                >
                  <div className="flex items-start gap-2.5">
                    <span className="font-mono text-xs font-bold text-cyan-400 px-1.5 py-0.5 rounded bg-slate-800">
                      #{step.step_id}
                    </span>
                    <div>
                      <div className="text-xs font-semibold text-slate-200">
                        {step.description}
                      </div>
                      <div className="flex flex-wrap items-center gap-2 mt-1 text-[11px] font-mono text-slate-400">
                        <span className="text-cyan-400 flex items-center gap-1">
                          <Bot className="w-3 h-3" />
                          {step.assigned_agent}
                        </span>
                        {step.required_tool && (
                          <span className="text-emerald-400">
                            tool: {step.required_tool}
                          </span>
                        )}
                        {step.dependencies.length > 0 && (
                          <span className="text-slate-500">
                            depends on: [{step.dependencies.join(', ')}]
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {isConfirmationRequired && (
                      <span className="flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
                        <ShieldAlert className="w-3 h-3 text-amber-400" />
                        CONFIRMATION REQUIRED
                      </span>
                    )}
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      {step.status}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
