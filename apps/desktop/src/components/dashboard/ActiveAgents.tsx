import React from 'react';
import { Code, Search, Database, Globe, CheckSquare, ShieldCheck, ArrowRight } from 'lucide-react';
import { WaveformVisualizer } from '../common/WaveformVisualizer';

export const ActiveAgents: React.FC = () => {
  const agents = [
    {
      name: 'Coding Agent',
      status: 'Active',
      statusColor: 'text-emerald-400',
      icon: Code,
      accent: '#00f0ff',
      isWaveform: true,
    },
    {
      name: 'Research Agent',
      status: 'Active',
      statusColor: 'text-emerald-400',
      icon: Search,
      accent: '#00ffd5',
      isWaveform: true,
    },
    {
      name: 'Memory Agent',
      status: 'Standby',
      statusColor: 'text-slate-400',
      icon: Database,
      accent: '#9d4edd',
      isWaveform: true,
    },
    {
      name: 'Browser Agent',
      status: 'Standby',
      statusColor: 'text-slate-400',
      icon: Globe,
      accent: '#f59e0b',
      isWaveform: true,
    },
    {
      name: 'Task Agent',
      status: 'Standby',
      statusColor: 'text-slate-400',
      icon: CheckSquare,
      accent: '#0077ff',
      isWaveform: false,
    },
    {
      name: 'System Agent',
      status: 'Standby',
      statusColor: 'text-emerald-400',
      icon: ShieldCheck,
      accent: '#10b981',
      isWaveform: false,
    },
  ];

  return (
    <div className="hud-panel p-3.5 flex flex-col justify-between h-full">
      <div className="flex items-center justify-between mb-2">
        <span className="font-display font-bold text-xs tracking-widest text-nova-cyan uppercase">
          ACTIVE AGENTS
        </span>
        <button className="text-[11px] font-mono text-nova-cyanDim hover:text-nova-cyan transition-colors flex items-center gap-1">
          <span>View All</span>
          <ArrowRight className="w-3 h-3" />
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {agents.map((agent, i) => {
          const Icon = agent.icon;
          const isActive = agent.status === 'Active';

          return (
            <div
              key={i}
              className="p-2 rounded bg-nova-surface/70 border border-nova-border/50 hover:border-nova-cyan/60 transition-all flex flex-col justify-between"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <div 
                    className="p-1 rounded bg-nova-dark/80 border"
                    style={{ borderColor: `${agent.accent}40`, color: agent.accent }}
                  >
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                  <span className="font-display font-semibold text-xs text-slate-200">
                    {agent.name}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between mt-2 pt-1 border-t border-nova-border/30">
                <div className="flex items-center gap-1 text-[10px] font-mono">
                  <span 
                    className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}`} 
                  />
                  <span className={agent.statusColor}>{agent.status}</span>
                </div>

                {agent.isWaveform ? (
                  <WaveformVisualizer active={isActive} color={agent.accent} barsCount={8} height={12} />
                ) : (
                  <span className="text-[10px] font-mono text-emerald-400">✓ Ready</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
