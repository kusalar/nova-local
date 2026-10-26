import React, { useState } from 'react';
import { 
  Play, 
  Pause, 
  Trash2, 
  Edit3, 
  Clock, 
  Shield, 
  Zap, 
  CheckCircle, 
  AlertTriangle,
  RotateCw
} from 'lucide-react';
import { AutomationRule, AutonomyLevel } from '../../types';

interface AutomationListProps {
  automations: AutomationRule[];
  onToggleEnable: (id: string, currentEnabled: boolean) => Promise<void>;
  onRunNow: (id: string) => Promise<void>;
  onEdit: (rule: AutomationRule) => void;
  onDelete: (id: string) => Promise<void>;
  onViewHistory: (id: string) => void;
  runningIds: Set<string>;
}

export const AutomationList: React.FC<AutomationListProps> = ({
  automations,
  onToggleEnable,
  onRunNow,
  onEdit,
  onDelete,
  onViewHistory,
  runningIds,
}) => {
  const [filter, setFilter] = useState<'all' | 'active' | 'disabled'>('all');

  const filtered = automations.filter(a => {
    if (filter === 'active') return a.enabled;
    if (filter === 'disabled') return !a.enabled;
    return true;
  });

  const getAutonomyBadge = (level: AutonomyLevel) => {
    switch (level) {
      case 'OBSERVE':
        return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-900/40 text-blue-400 border border-blue-500/30">OBSERVE</span>;
      case 'PREPARE':
        return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-900/40 text-amber-400 border border-amber-500/30">PREPARE</span>;
      case 'EXECUTE_LOW_RISK':
        return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-900/40 text-emerald-400 border border-emerald-500/30">LOW RISK</span>;
      case 'REQUIRES_APPROVAL':
        return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-900/40 text-purple-400 border border-purple-500/30">APPROVAL REQ</span>;
      case 'BLOCKED':
        return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-red-900/40 text-red-400 border border-red-500/30">BLOCKED</span>;
      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col h-full space-y-4">
      {/* Filter Tabs */}
      <div className="flex items-center justify-between pb-2 border-b border-cyan-500/20">
        <div className="flex space-x-2">
          {(['all', 'active', 'disabled'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setFilter(tab)}
              className={`px-3 py-1 text-xs uppercase font-mono tracking-wider rounded transition-colors ${
                filter === tab
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                  : 'text-slate-400 hover:text-cyan-300 hover:bg-slate-800/40'
              }`}
            >
              {tab} ({tab === 'all' ? automations.length : automations.filter(a => tab === 'active' ? a.enabled : !a.enabled).length})
            </button>
          ))}
        </div>
      </div>

      {/* Routine Cards List */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-1 custom-scrollbar">
        {filtered.length === 0 ? (
          <div className="text-center py-16 text-slate-500 font-mono text-sm border border-dashed border-slate-800 rounded-lg">
            No automations match the current filter.
          </div>
        ) : (
          filtered.map(auto => {
            const isRunning = runningIds.has(auto.id);
            return (
              <div
                key={auto.id}
                className={`p-4 rounded-lg border transition-all duration-200 ${
                  auto.enabled
                    ? 'bg-slate-900/70 border-cyan-500/30 hover:border-cyan-400/60 shadow-lg shadow-cyan-950/20'
                    : 'bg-slate-950/50 border-slate-800/60 opacity-70'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                        {auto.name}
                        {isRunning && (
                          <span className="flex items-center text-[10px] text-cyan-400 font-mono animate-pulse">
                            <RotateCw className="w-3 h-3 mr-1 animate-spin" /> RUNNING
                          </span>
                        )}
                      </h3>
                      {getAutonomyBadge(auto.autonomy_level)}
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                        {auto.action_type}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 line-clamp-2 max-w-xl">
                      {auto.description || 'No description provided.'}
                    </p>
                  </div>

                  {/* Actions Toolbar */}
                  <div className="flex items-center space-x-1.5 ml-4">
                    {/* Toggle Enable */}
                    <button
                      onClick={() => onToggleEnable(auto.id, auto.enabled)}
                      title={auto.enabled ? 'Disable routine' : 'Enable routine'}
                      className={`p-1.5 rounded transition-colors ${
                        auto.enabled
                          ? 'text-cyan-400 hover:bg-cyan-500/20'
                          : 'text-slate-500 hover:bg-slate-800 hover:text-slate-300'
                      }`}
                    >
                      {auto.enabled ? <CheckCircle className="w-4 h-4 text-emerald-400" /> : <Pause className="w-4 h-4" />}
                    </button>

                    {/* Run Now */}
                    <button
                      onClick={() => onRunNow(auto.id)}
                      disabled={isRunning || !auto.enabled}
                      title="Run immediately"
                      className="p-1.5 rounded text-cyan-400 hover:bg-cyan-500/20 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      <Play className="w-4 h-4" />
                    </button>

                    {/* Edit */}
                    <button
                      onClick={() => onEdit(auto)}
                      title="Edit rule"
                      className="p-1.5 rounded text-slate-400 hover:text-cyan-300 hover:bg-slate-800 transition-colors"
                    >
                      <Edit3 className="w-4 h-4" />
                    </button>

                    {/* History */}
                    <button
                      onClick={() => onViewHistory(auto.id)}
                      title="Execution logs"
                      className="p-1.5 rounded text-slate-400 hover:text-cyan-300 hover:bg-slate-800 transition-colors"
                    >
                      <Clock className="w-4 h-4" />
                    </button>

                    {/* Delete */}
                    <button
                      onClick={() => onDelete(auto.id)}
                      title="Delete routine"
                      className="p-1.5 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-950/30 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Footer Metadata */}
                <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-400">
                  <div className="flex items-center space-x-4">
                    <span className="flex items-center text-slate-400">
                      <Zap className="w-3 h-3 mr-1 text-cyan-400" />
                      Trigger: {auto.trigger_config.trigger_type}
                      {auto.trigger_config.schedule?.time_of_day && ` @ ${auto.trigger_config.schedule.time_of_day}`}
                    </span>
                    {auto.next_run_at && (
                      <span className="flex items-center text-amber-400/90">
                        <Clock className="w-3 h-3 mr-1 text-amber-400" />
                        Next: {new Date(auto.next_run_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center space-x-3 text-slate-500">
                    <span>Runs: {auto.run_count}</span>
                    {auto.failure_count > 0 && (
                      <span className="text-rose-400">Failures: {auto.failure_count}</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
