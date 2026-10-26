import React, { useEffect } from 'react';
import { X, Play, Volume2, ShieldCheck, Cpu, HardDrive, Wifi } from 'lucide-react';
import { SystemStatusResponse, AiStatusResponse } from '../../types';

interface ExecutiveBriefingModalProps {
  isOpen: boolean;
  onClose: () => void;
  systemStats: SystemStatusResponse;
  aiStatus: AiStatusResponse;
  onSpeak: (text: string) => void;
}

export const ExecutiveBriefingModal: React.FC<ExecutiveBriefingModalProps> = ({
  isOpen,
  onClose,
  systemStats,
  aiStatus,
  onSpeak
}) => {
  if (!isOpen) return null;

  const telemetry = systemStats.telemetry;
  const cpu = telemetry?.cpu?.percent ?? 15;
  const ram = telemetry?.ram?.percent ?? 54;
  const os = telemetry?.system?.os || 'Windows';

  const briefingText = 
    `Good day, Commander. NOVA Neural Core v0.1 is online and functioning at optimal capacity. ` +
    `Hardware telemetry indicates CPU load is at ${Math.round(cpu)} percent, with memory consumption at ${Math.round(ram)} percent. ` +
    `Local AI inference engine is ${aiStatus.online ? 'active on ' + aiStatus.active_model : 'in standby mode'}. ` +
    `All core defense systems and neural nodes are synchronized. I am ready for your directives.`;

  const handlePlayVoice = () => {
    onSpeak(briefingText);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div 
        className="hud-panel w-full max-w-lg p-5 border-nova-cyan/50 shadow-nova-orb"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between pb-3 border-b border-nova-border">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-nova-cyan animate-ping" />
            <h2 className="font-display font-bold text-sm tracking-wider text-white uppercase">
              EXECUTIVE BRIEFING — NOVA CORE
            </h2>
          </div>
          <button onClick={onClose} className="p-1 rounded text-slate-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="my-4 p-4 rounded bg-nova-surface border border-nova-border/60 space-y-3">
          <p className="text-sm font-sans text-slate-200 leading-relaxed italic">
            "{briefingText}"
          </p>

          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-nova-border/40 text-xs font-mono">
            <div className="flex items-center gap-2 text-slate-300">
              <Cpu className="w-3.5 h-3.5 text-nova-cyan" />
              <span>CPU: {cpu}%</span>
            </div>
            <div className="flex items-center gap-2 text-slate-300">
              <HardDrive className="w-3.5 h-3.5 text-nova-teal" />
              <span>RAM: {ram}%</span>
            </div>
            <div className="flex items-center gap-2 text-slate-300">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>System: Optimal</span>
            </div>
            <div className="flex items-center gap-2 text-slate-300">
              <Wifi className="w-3.5 h-3.5 text-nova-cyan" />
              <span>Ollama: {aiStatus.online ? 'Online' : 'Standby'}</span>
            </div>
          </div>
        </div>

        <div className="flex justify-between items-center pt-2">
          <span className="text-[10px] font-mono text-nova-textDim">
            Transmitted via NOVA Audio Engine
          </span>
          <div className="flex gap-2">
            <button
              onClick={handlePlayVoice}
              className="px-4 py-1.5 rounded bg-nova-cyan text-nova-dark font-display font-bold text-xs uppercase tracking-wider hover:bg-white flex items-center gap-1.5 shadow-nova-cyan"
            >
              <Volume2 className="w-4 h-4" />
              <span>Broadcast Voice</span>
            </button>
            <button
              onClick={onClose}
              className="px-3 py-1.5 rounded bg-nova-surface border border-nova-border text-xs text-slate-300 hover:text-white"
            >
              Dismiss
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
