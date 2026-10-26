import React from 'react';
import { Cpu, Database, Mic, Bot, Sparkles, ShieldCheck } from 'lucide-react';
import { AiStatusResponse, SystemStatusResponse } from '../../types';

interface AiCoreOverviewProps {
  aiStatus: AiStatusResponse;
  systemStats: SystemStatusResponse;
  onOpenLlmModal?: () => void;
}

export const AiCoreOverview: React.FC<AiCoreOverviewProps> = ({
  aiStatus,
  systemStats,
  onOpenLlmModal
}) => {
  const items = [
    {
      title: 'AI Core',
      status: aiStatus.online ? 'Active' : 'Standby',
      color: '#00f0ff',
      bgColor: 'rgba(0, 240, 255, 0.12)',
      icon: Cpu,
    },
    {
      title: 'Memory',
      status: `${systemStats.memory?.total_messages || 3380} Stored`,
      color: '#0077ff',
      bgColor: 'rgba(0, 119, 255, 0.12)',
      icon: Database,
    },
    {
      title: 'Voice',
      status: 'Online',
      color: '#00ffd5',
      bgColor: 'rgba(0, 255, 213, 0.12)',
      icon: Mic,
    },
    {
      title: 'Agents',
      status: '2 Running',
      color: '#9d4edd',
      bgColor: 'rgba(157, 78, 221, 0.12)',
      icon: Bot,
    },
    {
      title: 'LLMs',
      status: aiStatus.online ? `${aiStatus.active_model} Ready` : 'Ollama Offline',
      color: aiStatus.online ? '#f59e0b' : '#ff3366',
      bgColor: 'rgba(245, 158, 11, 0.12)',
      icon: Sparkles,
      onClick: onOpenLlmModal
    },
    {
      title: 'System',
      status: systemStats.status === 'optimal' ? 'Optimal' : 'Nominal',
      color: '#10b981',
      bgColor: 'rgba(16, 185, 129, 0.12)',
      icon: ShieldCheck,
    },
  ];

  return (
    <div className="hud-panel p-3.5 flex flex-col justify-between h-full">
      <div className="flex items-center justify-between mb-2">
        <span className="font-display font-bold text-xs tracking-widest text-nova-cyan uppercase">
          AI CORE OVERVIEW
        </span>
        <span className="w-1.5 h-1.5 rounded-full bg-nova-cyan animate-pulse" />
      </div>

      <div className="space-y-1.5 flex-1 flex flex-col justify-between">
        {items.map((item, idx) => {
          const Icon = item.icon;
          return (
            <div
              key={idx}
              onClick={item.onClick}
              className={`flex items-center justify-between p-2 rounded bg-nova-surface/60 border border-nova-border/50 transition-all ${
                item.onClick ? 'cursor-pointer hover:border-nova-cyan/60' : ''
              }`}
            >
              <div className="flex items-center gap-2.5">
                <div 
                  className="w-7 h-7 rounded flex items-center justify-center border"
                  style={{
                    backgroundColor: item.bgColor,
                    borderColor: `${item.color}40`,
                    color: item.color
                  }}
                >
                  <Icon className="w-4 h-4" />
                </div>
                <div className="flex flex-col">
                  <span className="font-display font-semibold text-xs text-slate-200">
                    {item.title}
                  </span>
                  <span className="text-[10px] font-mono text-nova-textDim">
                    {item.status}
                  </span>
                </div>
              </div>

              <div 
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: item.color, boxShadow: `0 0 6px ${item.color}` }}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
};
