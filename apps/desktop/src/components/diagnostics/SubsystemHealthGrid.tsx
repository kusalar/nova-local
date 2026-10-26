import React from 'react';
import { 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  HelpCircle, 
  Clock, 
  Cpu, 
  Database, 
  Mic, 
  Layers, 
  Wrench, 
  Eye, 
  Bot, 
  Zap, 
  BrainCircuit, 
  Server
} from 'lucide-react';
import { SubsystemHealth, SubsystemState } from '../../types';

interface SubsystemHealthGridProps {
  subsystems: Record<string, SubsystemHealth>;
}

const SUBSYSTEM_ICONS: Record<string, React.ElementType> = {
  backend: Server,
  database: Database,
  ollama: Cpu,
  voice: Mic,
  memory: Layers,
  tools: Wrench,
  vision: Eye,
  agents: Bot,
  automation: Zap,
  personalization: BrainCircuit,
};

const STATE_BADGES: Record<SubsystemState, { label: string; bg: string; text: string; border: string; icon: React.ElementType }> = {
  HEALTHY: {
    label: 'HEALTHY',
    bg: 'bg-emerald-950/80',
    text: 'text-emerald-400',
    border: 'border-emerald-500/40',
    icon: CheckCircle2,
  },
  DEGRADED: {
    label: 'DEGRADED',
    bg: 'bg-amber-950/80',
    text: 'text-amber-300',
    border: 'border-amber-500/40',
    icon: AlertTriangle,
  },
  UNAVAILABLE: {
    label: 'UNAVAILABLE',
    bg: 'bg-slate-800/90',
    text: 'text-slate-400',
    border: 'border-slate-600',
    icon: HelpCircle,
  },
  RECOVERING: {
    label: 'RECOVERING',
    bg: 'bg-blue-950/80',
    text: 'text-blue-300',
    border: 'border-blue-500/40',
    icon: Clock,
  },
  ERROR: {
    label: 'ERROR',
    bg: 'bg-red-950/80',
    text: 'text-red-400',
    border: 'border-red-500/40',
    icon: XCircle,
  },
};

export const SubsystemHealthGrid: React.FC<SubsystemHealthGridProps> = ({ subsystems }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
      {Object.entries(subsystems).map(([key, sub]) => {
        const IconComponent = SUBSYSTEM_ICONS[key] || Server;
        const badgeConfig = STATE_BADGES[sub.state] || STATE_BADGES.HEALTHY;
        const StatusIcon = badgeConfig.icon;

        return (
          <div
            key={key}
            className="p-4 rounded-xl bg-nova-surface/40 hover:bg-nova-surface/70 border border-nova-border/70 hover:border-nova-cyan/40 transition-all flex flex-col justify-between"
          >
            <div>
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex items-center gap-2">
                  <span className="p-1.5 rounded-lg bg-nova-dark/80 border border-nova-border text-nova-cyan">
                    <IconComponent className="w-4 h-4" />
                  </span>
                  <span className="font-mono text-xs font-bold text-slate-100 uppercase tracking-wider">
                    {sub.name}
                  </span>
                </div>

                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded border flex items-center gap-1 font-semibold ${badgeConfig.bg} ${badgeConfig.text} ${badgeConfig.border}`}
                >
                  <StatusIcon className="w-3 h-3" />
                  <span>{badgeConfig.label}</span>
                </span>
              </div>

              <p className="text-xs font-mono text-slate-300 mb-3 leading-relaxed">
                {sub.message}
              </p>
            </div>

            <div className="pt-2 border-t border-nova-border/40 flex items-center justify-between text-[10px] font-mono text-slate-500">
              <span>Latency: {sub.latency_ms !== undefined ? `${sub.latency_ms}ms` : 'N/A'}</span>
              <span>Updated: {new Date(sub.last_checked).toLocaleTimeString()}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
};
