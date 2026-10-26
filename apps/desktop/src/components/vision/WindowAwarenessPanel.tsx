import React from 'react';
import { 
  AppWindow, 
  Layers, 
  ShieldAlert, 
  ShieldCheck, 
  RefreshCw, 
  ExternalLink,
  Minimize2,
  Maximize2
} from 'lucide-react';
import { WindowInfo } from '../../types';

interface WindowAwarenessPanelProps {
  activeWindow: WindowInfo | null;
  windows: WindowInfo[];
  isLoading: boolean;
  onRefresh: () => void;
  onSelectWindowForCapture?: (win: WindowInfo) => void;
}

export const WindowAwarenessPanel: React.FC<WindowAwarenessPanelProps> = ({
  activeWindow,
  windows,
  isLoading,
  onRefresh,
  onSelectWindowForCapture
}) => {
  return (
    <div className="bg-nova-surface/70 border border-nova-border/70 rounded-lg p-4 flex flex-col h-full shadow-[0_4px_20px_rgba(0,0,0,0.3)]">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-nova-border/50">
        <div className="flex items-center gap-2">
          <AppWindow className="w-4 h-4 text-nova-cyan" />
          <span className="text-xs font-semibold font-display tracking-wider text-slate-200">
            WINDOW CONTEXT & AWARENESS
          </span>
        </div>
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="p-1 hover:bg-nova-dark/60 rounded text-slate-400 hover:text-nova-cyan transition-colors"
          title="Refresh Windows List"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Active Window Focus Card */}
      <div className="mt-3 p-3 bg-nova-dark/80 border border-nova-border/60 rounded-md">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] font-mono tracking-wider text-nova-cyan uppercase">
            Currently Focused Window
          </span>
          {activeWindow?.is_sensitive ? (
            <span className="flex items-center gap-1 text-[10px] font-mono bg-rose-500/20 text-rose-300 border border-rose-500/40 px-1.5 py-0.5 rounded">
              <ShieldAlert className="w-3 h-3" /> SENSITIVE PRIVACY SHIELD
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[10px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-1.5 py-0.5 rounded">
              <ShieldCheck className="w-3 h-3" /> CAPTURE PERMITTED
            </span>
          )}
        </div>

        {activeWindow ? (
          <div>
            <h4 className="text-xs font-semibold text-slate-100 truncate" title={activeWindow.title}>
              {activeWindow.title || '[Untitled Window]'}
            </h4>
            <div className="grid grid-cols-2 gap-2 mt-2 text-[11px] font-mono text-slate-400">
              <div>
                Process: <strong className="text-slate-200">{activeWindow.process_name}</strong>
              </div>
              <div>
                App: <strong className="text-slate-200">{activeWindow.app_name}</strong>
              </div>
              <div>
                Bounds: {activeWindow.width} x {activeWindow.height}
              </div>
              <div>
                Position: ({activeWindow.left}, {activeWindow.top})
              </div>
            </div>
          </div>
        ) : (
          <p className="text-xs text-slate-500 italic">No foreground window detected.</p>
        )}
      </div>

      {/* All Visible Windows List */}
      <div className="mt-3 flex-1 flex flex-col min-h-0">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-mono text-slate-400">
            Visible Desktop Applications ({windows.length})
          </span>
        </div>

        <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 custom-scrollbar">
          {windows.map((w, idx) => (
            <div
              key={`${w.handle}-${idx}`}
              className={`p-2 rounded border text-xs font-mono transition-all flex items-center justify-between ${
                w.is_active 
                  ? 'bg-nova-cyan/10 border-nova-cyan/40 text-slate-200' 
                  : 'bg-nova-dark/50 border-nova-border/40 text-slate-400 hover:border-nova-border/80'
              }`}
            >
              <div className="truncate max-w-[260px]">
                <div className="text-slate-200 truncate font-sans text-xs">
                  {w.title}
                </div>
                <div className="text-[10px] text-slate-500 flex items-center gap-2 mt-0.5">
                  <span>{w.process_name}</span>
                  <span>•</span>
                  <span>{w.width}x{w.height}</span>
                  {w.is_sensitive && (
                    <span className="text-rose-400 font-semibold">• SENSITIVE</span>
                  )}
                </div>
              </div>

              {w.is_active && (
                <span className="text-[9px] font-bold tracking-wider text-nova-cyan uppercase px-1.5 py-0.5 bg-nova-cyan/20 rounded">
                  Active
                </span>
              )}
            </div>
          ))}

          {windows.length === 0 && !isLoading && (
            <div className="text-center py-6 text-slate-500 text-xs">
              No top-level windows enumerated.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
