import React from 'react';
import { TriggerConfig, TriggerType } from '../../types';
import { AutomationSchedule } from './AutomationSchedule';

interface TriggerConfigurationProps {
  triggerConfig: TriggerConfig;
  onChange: (triggerConfig: TriggerConfig) => void;
}

const TRIGGER_TYPES: { id: TriggerType; label: string }[] = [
  { id: 'SCHEDULE', label: 'Scheduled Time' },
  { id: 'SYSTEM_THRESHOLD', label: 'Resource Threshold' },
  { id: 'APP_EVENT', label: 'App Event' },
  { id: 'WORKFLOW_EVENT', label: 'Workflow Outcome' },
  { id: 'TASK_OVERDUE', label: 'Task Overdue' },
  { id: 'MANUAL', label: 'Manual Only' },
];

export const TriggerConfiguration: React.FC<TriggerConfigurationProps> = ({
  triggerConfig,
  onChange,
}) => {
  const handleTypeChange = (t: TriggerType) => {
    onChange({
      ...triggerConfig,
      trigger_type: t,
      schedule: t === 'SCHEDULE' ? (triggerConfig.schedule || { schedule_type: 'DAILY', time_of_day: '08:00', timezone: 'UTC' }) : triggerConfig.schedule,
    });
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs font-mono uppercase tracking-wider text-cyan-400 mb-2">
          Trigger Mechanism
        </label>
        <div className="grid grid-cols-3 gap-2">
          {TRIGGER_TYPES.map(tt => (
            <button
              key={tt.id}
              type="button"
              onClick={() => handleTypeChange(tt.id)}
              className={`px-3 py-2 text-xs font-mono rounded border transition-all text-left ${
                triggerConfig.trigger_type === tt.id
                  ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 shadow-md shadow-cyan-950/30'
                  : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
              }`}
            >
              {tt.label}
            </button>
          ))}
        </div>
      </div>

      {/* SCHEDULE TRIGGER */}
      {triggerConfig.trigger_type === 'SCHEDULE' && (
        <AutomationSchedule
          schedule={triggerConfig.schedule || { schedule_type: 'DAILY', time_of_day: '08:00', timezone: 'UTC' }}
          onChange={sched => onChange({ ...triggerConfig, schedule: sched })}
        />
      )}

      {/* SYSTEM THRESHOLD TRIGGER */}
      {triggerConfig.trigger_type === 'SYSTEM_THRESHOLD' && (
        <div className="p-4 bg-slate-900/60 rounded-lg border border-cyan-500/20 grid grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1">Metric</label>
            <select
              value={triggerConfig.system_metric || 'memory_percent'}
              onChange={e => onChange({ ...triggerConfig, system_metric: e.target.value })}
              className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200 font-mono focus:border-cyan-400 focus:outline-none"
            >
              <option value="memory_percent">RAM Utilization (%)</option>
              <option value="cpu_percent">CPU Utilization (%)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1">Operator</label>
            <select
              value={triggerConfig.metric_operator || '>'}
              onChange={e => onChange({ ...triggerConfig, metric_operator: e.target.value })}
              className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200 font-mono focus:border-cyan-400 focus:outline-none"
            >
              <option value=">">&gt; (Greater than)</option>
              <option value=">=">&gt;= (Greater or equal)</option>
              <option value="<">&lt; (Less than)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1">Threshold (%)</label>
            <input
              type="number"
              value={triggerConfig.metric_threshold || 85}
              onChange={e => onChange({ ...triggerConfig, metric_threshold: parseFloat(e.target.value) || 0 })}
              className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-1.5 text-xs text-cyan-400 font-mono focus:border-cyan-400 focus:outline-none"
            />
          </div>
        </div>
      )}

      {/* APP EVENT TRIGGER */}
      {triggerConfig.trigger_type === 'APP_EVENT' && (
        <div className="p-4 bg-slate-900/60 rounded-lg border border-cyan-500/20 grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1">Executable Name</label>
            <input
              type="text"
              placeholder="e.g. Code.exe, slack.exe"
              value={triggerConfig.app_name || ''}
              onChange={e => onChange({ ...triggerConfig, app_name: e.target.value })}
              className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200 font-mono focus:border-cyan-400 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1">Event Type</label>
            <select
              value={triggerConfig.app_action || 'launched'}
              onChange={e => onChange({ ...triggerConfig, app_action: e.target.value })}
              className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200 font-mono focus:border-cyan-400 focus:outline-none"
            >
              <option value="launched">Application Launched</option>
              <option value="closed">Application Closed</option>
            </select>
          </div>
        </div>
      )}

      {/* WORKFLOW EVENT TRIGGER */}
      {triggerConfig.trigger_type === 'WORKFLOW_EVENT' && (
        <div className="p-4 bg-slate-900/60 rounded-lg border border-cyan-500/20 grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1">Workflow Filter (Optional)</label>
            <input
              type="text"
              placeholder="e.g. deploy, test"
              value={triggerConfig.workflow_id_pattern || ''}
              onChange={e => onChange({ ...triggerConfig, workflow_id_pattern: e.target.value })}
              className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200 font-mono focus:border-cyan-400 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1">Target Outcome</label>
            <select
              value={triggerConfig.workflow_outcome || 'COMPLETED'}
              onChange={e => onChange({ ...triggerConfig, workflow_outcome: e.target.value })}
              className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200 font-mono focus:border-cyan-400 focus:outline-none"
            >
              <option value="COMPLETED">Workflow Completed Successfully</option>
              <option value="FAILED">Workflow Failed</option>
            </select>
          </div>
        </div>
      )}
    </div>
  );
};
