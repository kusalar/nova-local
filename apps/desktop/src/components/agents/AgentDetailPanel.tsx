import React from 'react';
import { 
  Bot, 
  ShieldCheck, 
  Wrench, 
  CheckCircle, 
  Terminal, 
  X,
  FileCode,
  Lock
} from 'lucide-react';
import { AgentMetadata } from '../../types';

interface AgentDetailPanelProps {
  agent: AgentMetadata | null;
  onClose: () => void;
}

export const AgentDetailPanel: React.FC<AgentDetailPanelProps> = ({
  agent,
  onClose
}) => {
  if (!agent) return null;

  return (
    <div className="hud-panel p-4 rounded-lg border border-cyan-800/50 bg-slate-900/90 flex flex-col gap-3">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-cyan-400" />
          <h4 className="text-sm font-semibold font-mono text-slate-100">
            {agent.name.toUpperCase()} SPECIFICATION
          </h4>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="text-xs text-slate-300 leading-relaxed">
        {agent.description}
      </div>

      <div className="grid grid-cols-2 gap-3 mt-1">
        <div className="p-2.5 rounded bg-slate-950/60 border border-slate-800">
          <div className="text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-1">
            Assigned Role
          </div>
          <div className="text-xs font-mono text-cyan-300 font-bold uppercase">
            {agent.role}
          </div>
        </div>

        <div className="p-2.5 rounded bg-slate-950/60 border border-slate-800">
          <div className="text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-1">
            Status
          </div>
          <div className="text-xs font-mono text-emerald-400 uppercase font-semibold">
            {agent.status}
          </div>
        </div>
      </div>

      <div className="space-y-1.5 mt-1">
        <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
          <CheckCircle className="w-3.5 h-3.5 text-cyan-400" />
          Core Capabilities
        </div>
        <ul className="text-xs text-slate-300 space-y-1 pl-4 list-disc marker:text-cyan-400">
          {agent.capabilities.map((cap, i) => (
            <li key={i}>{cap}</li>
          ))}
        </ul>
      </div>

      <div className="space-y-1.5 mt-2">
        <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          Authorized Tool Access ({agent.allowed_tools.length})
        </div>
        <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto custom-scrollbar p-2 rounded bg-slate-950/40 border border-slate-800">
          {agent.allowed_tools.map((tool, i) => (
            <span
              key={i}
              className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-emerald-300 border border-emerald-900/50 flex items-center gap-1"
            >
              <Wrench className="w-3 h-3 text-emerald-400" />
              {tool}
            </span>
          ))}
        </div>
      </div>

      <div className="mt-2 p-2 rounded bg-cyan-950/30 border border-cyan-800/40 text-[11px] text-cyan-300/80 flex items-center gap-1.5">
        <Lock className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
        Strict v0.4 Permission Isolation: No unpermitted shell or filesystem mutations allowed.
      </div>
    </div>
  );
};
