import React, { useState } from 'react';
import { 
  Play, 
  Sparkles, 
  RefreshCw, 
  ShieldAlert, 
  ShieldCheck, 
  Layers, 
  Terminal, 
  ArrowRight,
  FolderTree,
  AppWindow,
  Cpu,
  Globe
} from 'lucide-react';
import { TaskPlan, TaskStep } from '../../types';

interface TaskPlannerPanelProps {
  onPlanTask: (prompt: string) => Promise<TaskPlan | null>;
  onExecutePlan: (plan: TaskPlan) => void;
  activePlan: TaskPlan | null;
  isPlanning?: boolean;
  isExecuting?: boolean;
}

export const TaskPlannerPanel: React.FC<TaskPlannerPanelProps> = ({
  onPlanTask,
  onExecutePlan,
  activePlan,
  isPlanning = false,
  isExecuting = false
}) => {
  const [prompt, setPrompt] = useState('');

  const quickDirectives = [
    "Open VS Code, open my NOVA project, and tell me whether the backend is running.",
    "Check my CPU and RAM usage",
    "Organize my Downloads folder",
    "Create a folder called Research in my Documents",
    "Find all python files in NOVA",
    "Search the web for Ollama local weights"
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isPlanning) return;
    await onPlanTask(prompt.trim());
  };

  const handleQuickClick = async (text: string) => {
    setPrompt(text);
    await onPlanTask(text);
  };

  const getToolCategoryIcon = (toolId: string) => {
    if (toolId.startsWith('app_') || toolId.startsWith('file_open') || toolId.startsWith('folder_open')) {
      return <AppWindow className="w-3.5 h-3.5 text-blue-400" />;
    }
    if (toolId.startsWith('folder_') || toolId.startsWith('file_')) {
      return <FolderTree className="w-3.5 h-3.5 text-emerald-400" />;
    }
    if (toolId.startsWith('system_')) {
      return <Cpu className="w-3.5 h-3.5 text-purple-400" />;
    }
    if (toolId.startsWith('browser_')) {
      return <Globe className="w-3.5 h-3.5 text-cyan-400" />;
    }
    return <Terminal className="w-3.5 h-3.5 text-slate-400" />;
  };

  return (
    <div className="flex flex-col h-full space-y-3.5 font-sans">
      {/* Directive Input Box */}
      <div className="bg-nova-surface/60 border border-nova-border/70 rounded-xl p-4 shadow-sm">
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-slate-200 font-display tracking-wider flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-nova-cyan" />
              AUTONOMOUS DIRECTIVE DECOMPILER
            </label>
            <span className="text-[10px] font-mono text-slate-400">
              Max 8 Steps • Strict Permission Bounds
            </span>
          </div>

          <div className="relative">
            <textarea
              rows={2}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g., 'Open VS Code, open my NOVA project, and check system status' or 'Organize my Downloads folder'"
              className="w-full bg-nova-dark/80 border border-nova-border/70 rounded-lg p-3 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-nova-cyan/70 resize-none font-sans"
            />
          </div>

          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 overflow-x-auto custom-scrollbar py-1">
              {quickDirectives.map((d, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => handleQuickClick(d)}
                  className="px-2 py-1 rounded bg-nova-dark/60 hover:bg-nova-dark text-[10px] text-slate-300 hover:text-nova-cyan border border-nova-border/50 whitespace-nowrap transition-all"
                >
                  {d.length > 35 ? d.substring(0, 35) + '...' : d}
                </button>
              ))}
            </div>

            <button
              type="submit"
              disabled={!prompt.trim() || isPlanning}
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-nova-cyan hover:bg-nova-cyan/80 text-slate-950 font-display tracking-wider flex items-center gap-1.5 transition-all shadow-[0_0_15px_rgba(0,240,255,0.2)] disabled:opacity-50 flex-shrink-0"
            >
              {isPlanning ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Decompiling...
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  Plan Directive
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Plan Preview / Stepper */}
      <div className="flex-1 overflow-y-auto bg-nova-surface/40 border border-nova-border/60 rounded-xl p-4 flex flex-col justify-between custom-scrollbar">
        {isPlanning ? (
          <div className="flex flex-col items-center justify-center p-12 text-slate-400 space-y-3 font-mono">
            <RefreshCw className="w-6 h-6 animate-spin text-nova-cyan" />
            <p className="text-xs">Deconstructing directive into verified tool sequence...</p>
          </div>
        ) : !activePlan ? (
          <div className="flex flex-col items-center justify-center p-12 text-slate-500 border border-dashed border-nova-border/50 rounded-xl my-auto">
            <Layers className="w-8 h-8 text-slate-600 mb-2" />
            <p className="text-xs font-medium">No active plan generated yet.</p>
            <p className="text-[11px] text-slate-500 mt-1">Enter a natural-language directive above to generate an execution plan.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Plan Header */}
            <div className="flex items-start justify-between gap-3 p-3 bg-nova-dark/70 rounded-lg border border-nova-border/60">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono text-nova-cyan bg-nova-cyan/10 px-1.5 py-0.5 rounded border border-nova-cyan/30">
                    {activePlan.task_id}
                  </span>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                    activePlan.status === 'COMPLETED' ? 'bg-emerald-950/40 text-emerald-400 border-emerald-500/30' :
                    activePlan.status === 'PENDING_APPROVAL' ? 'bg-amber-950/40 text-amber-400 border-amber-500/30' :
                    activePlan.status === 'FAILED' ? 'bg-rose-950/40 text-rose-400 border-rose-500/30' :
                    'bg-cyan-950/40 text-cyan-400 border-cyan-500/30'
                  }`}>
                    {activePlan.status}
                  </span>
                </div>
                <h4 className="text-xs font-bold text-slate-100 font-display mt-1.5">
                  {activePlan.description}
                </h4>
              </div>

              {activePlan.requires_confirmation && (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-500/10 border border-amber-500/30 text-[11px] text-amber-400 font-mono">
                  <ShieldAlert className="w-3.5 h-3.5" />
                  Requires Confirmation
                </div>
              )}
            </div>

            {/* Steps Breakdown */}
            <div className="space-y-2">
              <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                Execution Steps ({activePlan.steps.length} {activePlan.steps.length === 1 ? 'Step' : 'Steps'})
              </div>

              {activePlan.steps.map((step) => {
                const isConf = step.permission_level === 'CONFIRMATION_REQUIRED';
                return (
                  <div
                    key={step.step_id}
                    className={`p-3 rounded-lg border text-xs transition-all ${
                      step.status === 'COMPLETED'
                        ? 'bg-emerald-950/15 border-emerald-500/30 text-emerald-200'
                        : isConf
                        ? 'bg-amber-950/15 border-amber-500/30 text-amber-100'
                        : 'bg-nova-dark/60 border-nova-border/60 text-slate-200'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="w-5 h-5 rounded-full bg-slate-800 text-[11px] font-mono flex items-center justify-center font-bold text-slate-300">
                          {step.step_id}
                        </span>
                        {getToolCategoryIcon(step.tool_id)}
                        <span className="font-bold font-mono text-slate-100">
                          {step.tool_id}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                          isConf ? 'bg-amber-500/20 text-amber-300' : 'bg-slate-800 text-slate-400'
                        }`}>
                          {step.permission_level}
                        </span>
                        <span className="text-[10px] font-mono text-slate-400">
                          {step.status}
                        </span>
                      </div>
                    </div>

                    <p className="text-[11px] text-slate-300 font-sans ml-7">
                      {step.description}
                    </p>

                    {Object.keys(step.arguments).length > 0 && (
                      <div className="mt-1.5 ml-7 p-1.5 bg-black/40 rounded text-[10px] font-mono text-slate-400 overflow-x-auto">
                        {JSON.stringify(step.arguments)}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Execute Button */}
            <div className="pt-3 border-t border-nova-border/60 flex items-center justify-between">
              <span className="text-[11px] text-slate-400 font-mono">
                {activePlan.requires_confirmation 
                  ? '⚠️ Will prompt for explicit authorization modal before execution.'
                  : '✓ Safe to execute immediately.'}
              </span>

              <button
                onClick={() => onExecutePlan(activePlan)}
                disabled={isExecuting || activePlan.steps.length === 0}
                className="px-5 py-2 rounded-lg text-xs font-semibold bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-display tracking-wider flex items-center gap-1.5 transition-all shadow-[0_0_15px_rgba(16,185,129,0.3)] disabled:opacity-50"
              >
                {isExecuting ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    Executing Directive...
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 fill-current" />
                    Execute Plan
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
