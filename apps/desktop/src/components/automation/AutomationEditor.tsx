import React, { useState } from 'react';
import { X, Save, AlertCircle } from 'lucide-react';
import { 
  AutomationRule, 
  AutomationCreate, 
  AutomationUpdate, 
  AutonomyLevel, 
  AutomationActionType, 
  TriggerConfig,
  RetryPolicy
} from '../../types';
import { TriggerConfiguration } from './TriggerConfiguration';

interface AutomationEditorProps {
  initialRule?: AutomationRule | null;
  onSave: (data: AutomationCreate | AutomationUpdate) => Promise<void>;
  onClose: () => void;
}

export const AutomationEditor: React.FC<AutomationEditorProps> = ({
  initialRule,
  onSave,
  onClose,
}) => {
  const [name, setName] = useState(initialRule?.name || '');
  const [description, setDescription] = useState(initialRule?.description || '');
  const [autonomyLevel, setAutonomyLevel] = useState<AutonomyLevel>(
    initialRule?.autonomy_level || 'EXECUTE_LOW_RISK'
  );
  const [actionType, setActionType] = useState<AutomationActionType>(
    initialRule?.action_type || 'DAILY_BRIEFING'
  );
  const [workflowObjective, setWorkflowObjective] = useState(
    initialRule?.workflow_objective || ''
  );
  const [triggerConfig, setTriggerConfig] = useState<TriggerConfig>(
    initialRule?.trigger_config || {
      trigger_type: 'SCHEDULE',
      schedule: {
        schedule_type: 'DAILY',
        time_of_day: '08:00',
        timezone: 'UTC',
      },
    }
  );
  const [retryPolicy, setRetryPolicy] = useState<RetryPolicy>(
    initialRule?.retry_policy || {
      max_retries: 2,
      retry_delay_seconds: 60,
      stop_on_critical: true,
    }
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Please provide a descriptive name for this routine.');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await onSave({
        name: name.trim(),
        description: description.trim(),
        autonomy_level: autonomyLevel,
        action_type: actionType,
        workflow_objective: actionType === 'WORKFLOW' ? workflowObjective.trim() : undefined,
        trigger_config: triggerConfig,
        retry_policy: retryPolicy,
      });
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to save automation rule.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl bg-slate-900 border border-cyan-500/40 rounded-xl shadow-2xl shadow-cyan-950/40 max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-cyan-500/20 bg-slate-950/40">
          <div>
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              {initialRule ? 'Edit Automation Routine' : 'Create Automation Routine'}
            </h2>
            <p className="text-xs text-slate-400 font-mono">
              Configure proactive triggers, autonomy boundaries, and execution actions.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-5 custom-scrollbar">
          {error && (
            <div className="p-3 bg-rose-950/40 border border-rose-500/40 rounded flex items-center text-rose-300 text-xs font-mono">
              <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0" />
              {error}
            </div>
          )}

          {/* Name & Description */}
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1">Routine Name *</label>
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="e.g. Daily Morning Intelligence Briefing"
                className="w-full bg-slate-950/80 border border-slate-700 rounded px-3 py-2 text-sm text-slate-100 focus:border-cyan-400 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1">Description</label>
              <textarea
                rows={2}
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="What this automation does and why it runs..."
                className="w-full bg-slate-950/80 border border-slate-700 rounded px-3 py-2 text-xs text-slate-300 focus:border-cyan-400 focus:outline-none"
              />
            </div>
          </div>

          {/* Autonomy Level & Action Type */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1">Autonomy Boundary</label>
              <select
                value={autonomyLevel}
                onChange={e => setAutonomyLevel(e.target.value as AutonomyLevel)}
                className="w-full bg-slate-950/80 border border-slate-700 rounded px-3 py-2 text-xs text-cyan-400 font-mono focus:border-cyan-400 focus:outline-none"
              >
                <option value="OBSERVE">OBSERVE (Read-Only Telemetry/Memory)</option>
                <option value="PREPARE">PREPARE (Plan & Recommend)</option>
                <option value="EXECUTE_LOW_RISK">EXECUTE_LOW_RISK (Notifications & Safe Checks)</option>
                <option value="REQUIRES_APPROVAL">REQUIRES_APPROVAL (Approval Gated)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1">Action Subsystem</label>
              <select
                value={actionType}
                onChange={e => setActionType(e.target.value as AutomationActionType)}
                className="w-full bg-slate-950/80 border border-slate-700 rounded px-3 py-2 text-xs text-slate-200 font-mono focus:border-cyan-400 focus:outline-none"
              >
                <option value="DAILY_BRIEFING">Daily Briefing Agent</option>
                <option value="PROJECT_HEALTH">Project Health Monitor</option>
                <option value="REMINDER">Smart Task Reminder</option>
                <option value="WORKFLOW">Agent Orchestrator Workflow</option>
                <option value="NOTIFICATION">Direct Notification Alert</option>
              </select>
            </div>
          </div>

          {/* Workflow Objective (if WORKFLOW) */}
          {actionType === 'WORKFLOW' && (
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1">Agent Workflow Objective *</label>
              <input
                type="text"
                value={workflowObjective}
                onChange={e => setWorkflowObjective(e.target.value)}
                placeholder="e.g. Inspect recent test reports and compile diagnostic summary"
                className="w-full bg-slate-950/80 border border-slate-700 rounded px-3 py-2 text-sm text-cyan-300 font-mono focus:border-cyan-400 focus:outline-none"
              />
            </div>
          )}

          {/* Trigger Configuration */}
          <TriggerConfiguration triggerConfig={triggerConfig} onChange={setTriggerConfig} />

          {/* Retry Policy */}
          <div className="p-4 bg-slate-900/60 rounded-lg border border-cyan-500/20 grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1">Max Retries</label>
              <input
                type="number"
                min={0}
                max={5}
                value={retryPolicy.max_retries}
                onChange={e => setRetryPolicy({ ...retryPolicy, max_retries: parseInt(e.target.value) || 0 })}
                className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200 font-mono focus:border-cyan-400 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1">Retry Delay (Sec)</label>
              <input
                type="number"
                min={10}
                max={3600}
                value={retryPolicy.retry_delay_seconds}
                onChange={e => setRetryPolicy({ ...retryPolicy, retry_delay_seconds: parseInt(e.target.value) || 60 })}
                className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200 font-mono focus:border-cyan-400 focus:outline-none"
              />
            </div>
          </div>
        </form>

        {/* Footer Actions */}
        <div className="flex items-center justify-end px-6 py-3 border-t border-cyan-500/20 bg-slate-950/40 space-x-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-mono uppercase text-slate-400 hover:text-slate-200 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={saving}
            className="px-5 py-1.5 text-xs font-mono uppercase bg-cyan-500 text-slate-950 font-bold rounded hover:bg-cyan-400 transition-colors flex items-center gap-1.5 shadow-lg shadow-cyan-500/20 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Routine'}
          </button>
        </div>
      </div>
    </div>
  );
};
