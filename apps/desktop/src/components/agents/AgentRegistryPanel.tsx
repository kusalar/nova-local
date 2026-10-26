import React from 'react';
import { 
  Bot, 
  Search, 
  Code2, 
  Cpu, 
  Eye, 
  Database, 
  ShieldCheck, 
  CheckCircle, 
  Clock, 
  AlertCircle,
  Activity
} from 'lucide-react';
import { AgentMetadata, AgentRole } from '../../types';

interface AgentRegistryPanelProps {
  agents: AgentMetadata[];
  selectedAgent: AgentMetadata | null;
  onSelectAgent: (agent: AgentMetadata) => void;
  isLoading: boolean;
}

export const AgentRegistryPanel: React.FC<AgentRegistryPanelProps> = ({
  agents,
  selectedAgent,
  onSelectAgent,
  isLoading
}) => {
  const getAgentIcon = (role: AgentRole) => {
    switch (role) {
      case 'researcher':
        return <Search className="w-5 h-5 text-cyan-400" />;
      case 'developer':
        return <Code2 className="w-5 h-5 text-emerald-400" />;
      case 'system':
        return <Cpu className="w-5 h-5 text-amber-400" />;
      case 'vision':
        return <Eye className="w-5 h-5 text-purple-400" />;
      case 'memory':
        return <Database className="w-5 h-5 text-blue-400" />;
      default:
        return <Bot className="w-5 h-5 text-cyan-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'idle':
        return (
          <span className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            IDLE
          </span>
        );
      case 'busy':
        return (
          <span className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
            EXECUTING
          </span>
        );
      case 'waiting_approval':
        return (
          <span className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/30">
            <Clock className="w-3 h-3 text-purple-400 animate-spin" />
            APPROVAL REQUIRED
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-slate-700/50 text-slate-400 border border-slate-600">
            OFFLINE
          </span>
        );
    }
  };

  return (
    <div className="h-full flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold tracking-wider text-cyan-300 font-mono flex items-center gap-2">
            <Bot className="w-4 h-4 text-cyan-400" />
            SPECIALIZED AGENT REGISTRY
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Bounded logical agents executing through local Ollama intelligence and safe tool authorizations
          </p>
        </div>
        <div className="text-xs font-mono text-cyan-400/80 px-2.5 py-1 rounded bg-cyan-950/40 border border-cyan-800/40">
          5 REGISTERED AGENTS
        </div>
      </div>

      {isLoading ? (
        <div className="flex-1 flex items-center justify-center text-slate-400 text-sm font-mono">
          <Activity className="w-5 h-5 text-cyan-400 animate-spin mr-2" />
          Querying Agent Registry...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {agents.map((agent) => {
            const isSelected = selectedAgent?.role === agent.role;

            return (
              <div
                key={agent.role}
                onClick={() => onSelectAgent(agent)}
                className={`p-3.5 rounded-lg border transition-all cursor-pointer flex flex-col justify-between ${
                  isSelected
                    ? 'bg-cyan-950/40 border-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.15)]'
                    : 'bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-800/40'
                }`}
              >
                <div>
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-md bg-slate-800/80 border border-slate-700">
                        {getAgentIcon(agent.role)}
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-slate-200">
                          {agent.name}
                        </h4>
                        <span className="text-[10px] font-mono text-cyan-400 uppercase">
                          {agent.role}
                        </span>
                      </div>
                    </div>
                    {getStatusBadge(agent.status)}
                  </div>

                  <p className="text-xs text-slate-400 line-clamp-2 mb-3">
                    {agent.description}
                  </p>

                  <div className="space-y-2">
                    <div>
                      <div className="text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-1">
                        Capabilities
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {agent.capabilities.slice(0, 3).map((cap, i) => (
                          <span
                            key={i}
                            className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700/60"
                          >
                            {cap}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <div className="text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1">
                        <ShieldCheck className="w-3 h-3 text-emerald-400" />
                        Authorized Tools ({agent.allowed_tools.length})
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {agent.allowed_tools.slice(0, 3).map((t, i) => (
                          <span
                            key={i}
                            className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/30 text-emerald-300 border border-emerald-800/40"
                          >
                            {t}
                          </span>
                        ))}
                        {agent.allowed_tools.length > 3 && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                            +{agent.allowed_tools.length - 3} more
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-cyan-400">
                  <span>View Details & Audits</span>
                  <span>→</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
