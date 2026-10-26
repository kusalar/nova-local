import React from 'react';
import { ArrowRight, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import { AiStatusResponse } from '../../types';

interface LlmStatusProps {
  aiStatus: AiStatusResponse;
  onManageProviders?: () => void;
}

export const LlmStatus: React.FC<LlmStatusProps> = ({ aiStatus, onManageProviders }) => {
  const providers = [
    { 
      name: 'Ollama (Local)', 
      status: aiStatus.online ? 'Connected' : 'Offline', 
      model: aiStatus.active_model,
      connected: aiStatus.online,
      isLocal: true
    },
    { name: 'Claude', status: 'Not Linked', connected: false },
    { name: 'OpenAI', status: 'Not Linked', connected: false },
    { name: 'Gemini', status: 'Not Linked', connected: false },
    { name: 'Groq', status: 'Connected', connected: true },
    { name: 'OpenRouter', status: 'Not Linked', connected: false },
    { name: 'Claude Code', status: 'Connected', connected: true },
    { name: 'Cursor', status: 'Connected', connected: true },
  ];

  const connectedCount = providers.filter(p => p.connected).length;

  return (
    <div className="hud-panel p-3.5 flex flex-col justify-between h-full">
      <div className="flex items-center justify-between mb-2">
        <span className="font-display font-bold text-xs tracking-widest text-nova-cyan uppercase">
          LLM STATUS
        </span>
        <span className="text-[10px] font-mono text-nova-cyan">
          {connectedCount} Connected
        </span>
      </div>

      <div className="grid grid-cols-2 gap-1.5 flex-1">
        {providers.map((p, idx) => (
          <div
            key={idx}
            className={`p-1.5 rounded flex items-center justify-between border transition-all ${
              p.isLocal && p.connected
                ? 'bg-nova-surface border-nova-cyan/60 shadow-[0_0_8px_rgba(0,240,255,0.2)]'
                : p.connected
                ? 'bg-nova-surface/60 border-nova-border/50'
                : 'bg-nova-dark/40 border-slate-800/60 opacity-60'
            }`}
          >
            <div className="flex flex-col min-w-0">
              <span className="font-display font-semibold text-xs text-slate-200 truncate">
                {p.name}
              </span>
              <span className="text-[9px] font-mono text-nova-textDim">
                {p.status}
              </span>
            </div>

            {p.connected ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
            ) : p.isLocal ? (
              <AlertCircle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
            ) : (
              <XCircle className="w-3.5 h-3.5 text-slate-600 flex-shrink-0" />
            )}
          </div>
        ))}
      </div>

      <button
        onClick={onManageProviders}
        className="mt-2 w-full flex items-center justify-center gap-1.5 text-xs font-display font-semibold text-nova-cyanDim hover:text-nova-cyan transition-colors"
      >
        <span>Manage Providers</span>
        <ArrowRight className="w-3.5 h-3.5" />
      </button>
    </div>
  );
};
