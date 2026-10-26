import React, { useState, useEffect } from 'react';
import { 
  Compass, 
  Layers, 
  FolderGit2, 
  AppWindow, 
  GitFork, 
  Clock, 
  AlertTriangle, 
  CheckCircle2, 
  RefreshCw,
  Search,
  Sliders
} from 'lucide-react';
import { ResolvedContext } from '../../types';
import { apiService } from '../../services/api';

export const ContextOverview: React.FC = () => {
  const [context, setContext] = useState<ResolvedContext | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [testQuery, setTestQuery] = useState<string>('');
  const [explicitProject, setExplicitProject] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchContext = async (query?: string, proj?: string) => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const data = await apiService.getPersonalizationContext(query || undefined, proj || undefined);
      setContext(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to resolve context');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchContext();
  }, []);

  const handleResolveTest = (e: React.FormEvent) => {
    e.preventDefault();
    fetchContext(testQuery, explicitProject);
  };

  const getSourceBadgeColor = (source: string) => {
    switch (source) {
      case 'explicit_instruction':
      case 'explicit_selection':
        return 'bg-emerald-950/80 text-emerald-300 border-emerald-500/40';
      case 'active_workflow':
        return 'bg-blue-950/80 text-blue-300 border-blue-500/40';
      case 'saved_project_memory':
        return 'bg-purple-950/80 text-purple-300 border-purple-500/40';
      case 'ambiguous':
        return 'bg-amber-950/80 text-amber-300 border-amber-500/40';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-600';
    }
  };

  return (
    <div className="space-y-4">
      {/* Simulation / Query Inspector */}
      <form onSubmit={handleResolveTest} className="p-3.5 rounded-lg bg-nova-surface/60 border border-nova-border/70 backdrop-blur-md flex flex-wrap items-center gap-3">
        <div className="flex-1 min-w-[240px]">
          <div className="flex items-center gap-2 mb-1 text-[11px] font-mono text-nova-cyan">
            <Search className="w-3 h-3" />
            <span>TEST CONVERSATION QUERY</span>
          </div>
          <input
            type="text"
            value={testQuery}
            onChange={(e) => setTestQuery(e.target.value)}
            placeholder="e.g. How does authentication work in Nova? or compare Nova and HireLens"
            className="w-full bg-nova-dark/80 border border-nova-border rounded px-3 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-nova-cyan"
          />
        </div>

        <div className="w-48">
          <div className="flex items-center gap-2 mb-1 text-[11px] font-mono text-slate-400">
            <FolderGit2 className="w-3 h-3" />
            <span>EXPLICIT PROJECT</span>
          </div>
          <input
            type="text"
            value={explicitProject}
            onChange={(e) => setExplicitProject(e.target.value)}
            placeholder="Optional project name"
            className="w-full bg-nova-dark/80 border border-nova-border rounded px-3 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-nova-cyan"
          />
        </div>

        <div className="flex items-end gap-2 pt-4">
          <button
            type="submit"
            className="px-3.5 py-1.5 rounded bg-nova-cyan/20 border border-nova-cyan/50 text-nova-cyan hover:bg-nova-cyan/30 text-xs font-mono tracking-wider transition-all"
          >
            RESOLVE CONTEXT
          </button>
          <button
            type="button"
            onClick={() => {
              setTestQuery('');
              setExplicitProject('');
              fetchContext();
            }}
            className="p-1.5 rounded text-slate-400 hover:text-nova-cyan hover:bg-nova-surface border border-transparent hover:border-nova-border transition-all"
            title="Reset to system context"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </form>

      {errorMsg && (
        <div className="p-3 rounded bg-red-950/60 border border-red-500/40 text-red-200 text-xs font-mono">
          {errorMsg}
        </div>
      )}

      {/* Ambiguity Alert Banner */}
      {context?.clarification_needed && (
        <div className="p-4 rounded-lg bg-amber-950/40 border border-amber-500/50 shadow-lg">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h4 className="text-xs font-mono font-semibold text-amber-300 uppercase tracking-wider">
                Ambiguous Context Detected — Clarification Prompt Triggered
              </h4>
              <p className="text-xs text-amber-200/90 font-mono">
                {context.clarification_prompt}
              </p>
              <div className="pt-2 flex items-center gap-2">
                <span className="text-[10px] font-mono text-amber-400">Candidate Projects:</span>
                {context.candidate_projects.map((proj) => (
                  <button
                    key={proj}
                    type="button"
                    onClick={() => {
                      setExplicitProject(proj);
                      fetchContext(testQuery, proj);
                    }}
                    className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-900/60 border border-amber-500/50 text-amber-200 hover:bg-amber-800/80 transition-colors"
                  >
                    Select {proj}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Context Pillars Grid */}
      {context && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
          {/* Active Project Card */}
          <div className="p-4 rounded-lg bg-nova-surface/40 border border-nova-border/70 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs font-mono text-nova-cyan mb-2">
                <span className="flex items-center gap-1.5">
                  <FolderGit2 className="w-4 h-4" />
                  ACTIVE PROJECT
                </span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded border font-mono ${getSourceBadgeColor(context.context_source)}`}>
                  {context.context_source.toUpperCase()}
                </span>
              </div>
              <div className="text-lg font-display tracking-wider text-slate-100 font-bold mb-1">
                {context.active_project || 'None (Global)'}
              </div>
              <p className="text-[11px] font-mono text-slate-400">
                Resolution Confidence: {(context.confidence * 100).toFixed(0)}%
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-nova-border/40 text-[10px] font-mono text-nova-teal flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" />
              <span>Project Isolation Enforced</span>
            </div>
          </div>

          {/* Project Memory Card */}
          <div className="p-4 rounded-lg bg-nova-surface/40 border border-nova-border/70 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs font-mono text-nova-cyan mb-2">
                <span className="flex items-center gap-1.5">
                  <Layers className="w-4 h-4" />
                  PROJECT MEMORY
                </span>
                <span className="text-[10px] font-mono text-slate-500">v0.3 SQLite</span>
              </div>
              <div className="text-2xl font-mono text-slate-100 font-bold mb-1">
                {context.project_memory_count}
              </div>
              <p className="text-[11px] font-mono text-slate-400">
                Persistent indexed memories available for context enrichment
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-nova-border/40 text-[10px] font-mono text-slate-500">
              Semantic embeddings ready
            </div>
          </div>

          {/* Active Window Card */}
          <div className="p-4 rounded-lg bg-nova-surface/40 border border-nova-border/70 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs font-mono text-nova-cyan mb-2">
                <span className="flex items-center gap-1.5">
                  <AppWindow className="w-4 h-4" />
                  ACTIVE WINDOW
                </span>
                <span className="text-[10px] font-mono text-slate-500">v0.5 OCR</span>
              </div>
              <div className="text-sm font-mono text-slate-100 font-semibold truncate mb-1" title={context.active_window_title || 'None'}>
                {context.active_window_title || 'No foreground window'}
              </div>
              <p className="text-[11px] font-mono text-slate-400">
                Process: {context.active_window_app || 'N/A'}
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-nova-border/40 text-[10px] font-mono text-slate-500">
              Visual awareness linked
            </div>
          </div>

          {/* Multi-Agent & Automation Card */}
          <div className="p-4 rounded-lg bg-nova-surface/40 border border-nova-border/70 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs font-mono text-nova-cyan mb-2">
                <span className="flex items-center gap-1.5">
                  <GitFork className="w-4 h-4" />
                  WORKFLOW & AUTOMATION
                </span>
                <span className="text-[10px] font-mono text-slate-500">v0.6/v0.7</span>
              </div>
              <div className="text-sm font-mono text-slate-100 font-semibold mb-1">
                Workflow: {context.active_workflow_state || 'Idle'}
              </div>
              <p className="text-[11px] font-mono text-slate-400">
                Pending Routines: {context.pending_routines_count}
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-nova-border/40 text-[10px] font-mono text-slate-500 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              <span>Routine scheduler synced</span>
            </div>
          </div>
        </div>
      )}

      {/* Active Preferences Applied to Current Context */}
      {context && (
        <div className="p-4 rounded-lg bg-nova-surface/40 border border-nova-border/70">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-xs font-mono text-nova-cyan uppercase tracking-wider flex items-center gap-2">
              <Sliders className="w-4 h-4" />
              Active Preferences Applied to Context
            </h4>
            <span className="text-[10px] font-mono text-slate-500">
              {Object.keys(context.active_preferences).length} active preferences
            </span>
          </div>

          {Object.keys(context.active_preferences).length === 0 ? (
            <p className="text-xs font-mono text-slate-500">
              No specific preferences active. System is operating with default balanced parameters.
            </p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
              {Object.entries(context.active_preferences).map(([k, v]) => (
                <div key={k} className="p-2.5 rounded bg-nova-dark/80 border border-nova-border/50 text-xs font-mono">
                  <span className="text-slate-400 block text-[10px] uppercase mb-0.5">{k.replace('_', ' ')}</span>
                  <span className="text-nova-teal break-words font-semibold">
                    {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
