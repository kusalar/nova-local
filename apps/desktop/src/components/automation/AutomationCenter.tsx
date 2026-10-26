import React, { useState, useEffect, useCallback } from 'react';
import { 
  Zap, 
  Play, 
  Pause, 
  Plus, 
  Sparkles, 
  Clock, 
  Sun, 
  Activity, 
  Bell, 
  History, 
  RefreshCw,
  AlertTriangle,
  ShieldCheck
} from 'lucide-react';
import { 
  AutomationRule, 
  AutomationStatusResponse, 
  RoutineTemplate, 
  AutomationCreate, 
  AutomationUpdate,
  AutomationHistoryRecord 
} from '../../types';
import { apiService } from '../../services/api';

import { AutomationList } from './AutomationList';
import { AutomationEditor } from './AutomationEditor';
import { RoutineTemplates } from './RoutineTemplates';
import { DailyBriefingPanel } from './DailyBriefingPanel';
import { ProjectHealthPanel } from './ProjectHealthPanel';
import { NotificationCenter } from './NotificationCenter';
import { AutomationHistory } from './AutomationHistory';

export const AutomationCenter: React.FC = () => {
  const [activeTab, setActiveTab] = useState<
    'routines' | 'templates' | 'briefing' | 'health' | 'notifications' | 'history'
  >('routines');

  const [automations, setAutomations] = useState<AutomationRule[]>([]);
  const [status, setStatus] = useState<AutomationStatusResponse | null>(null);
  const [templates, setTemplates] = useState<RoutineTemplate[]>([]);
  const [history, setHistory] = useState<AutomationHistoryRecord[]>([]);
  const [selectedHistoryRuleId, setSelectedHistoryRuleId] = useState<string | undefined>(undefined);

  const [editingRule, setEditingRule] = useState<AutomationRule | null>(null);
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [runningIds, setRunningIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);

  // Load all status and automation data
  const fetchData = useCallback(async () => {
    try {
      const [autos, st, tpls] = await Promise.all([
        apiService.listAutomations(),
        apiService.getAutomationStatus(),
        apiService.getRoutineTemplates(),
      ]);
      setAutomations(autos);
      setStatus(st);
      setTemplates(tpls);
    } catch (err) {
      console.error('Failed to load automation center data:', err);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Global pause/resume toggle
  const handleToggleGlobalPause = async () => {
    if (!status) return;
    try {
      if (status.is_paused) {
        await apiService.resumeAllAutomations();
      } else {
        await apiService.pauseAllAutomations();
      }
      await fetchData();
    } catch (err) {
      console.error('Failed to toggle global pause:', err);
    }
  };

  // Enable/disable individual routine
  const handleToggleEnable = async (id: string, currentEnabled: boolean) => {
    try {
      if (currentEnabled) {
        await apiService.disableAutomation(id);
      } else {
        await apiService.enableAutomation(id);
      }
      await fetchData();
    } catch (err) {
      console.error('Failed to toggle routine:', err);
    }
  };

  // Immediate execution
  const handleRunNow = async (id: string) => {
    setRunningIds(prev => new Set(prev).add(id));
    try {
      await apiService.runAutomation(id);
      await fetchData();
    } catch (err) {
      console.error('Error running automation:', err);
    } finally {
      setRunningIds(prev => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  };

  // Delete routine
  const handleDelete = async (id: string) => {
    try {
      await apiService.deleteAutomation(id);
      await fetchData();
    } catch (err) {
      console.error('Failed to delete automation:', err);
    }
  };

  // View history for specific rule
  const handleViewHistory = async (id: string) => {
    setSelectedHistoryRuleId(id);
    try {
      const logs = await apiService.getAutomationHistory(id);
      setHistory(logs);
      setActiveTab('history');
    } catch (err) {
      console.error('Failed to load rule history:', err);
    }
  };

  // Open editor for new rule or template
  const handleCreateNew = () => {
    setEditingRule(null);
    setIsEditorOpen(true);
  };

  const handleUseTemplate = (tpl: RoutineTemplate) => {
    const newRule: any = {
      name: tpl.name,
      description: tpl.description,
      autonomy_level: tpl.autonomy_level,
      action_type: tpl.action_type,
      trigger_config: tpl.trigger_config,
      action_payload: tpl.action_payload,
      retry_policy: { max_retries: 2, retry_delay_seconds: 60, stop_on_critical: true },
    };
    setEditingRule(newRule);
    setIsEditorOpen(true);
  };

  // Save rule (create or update)
  const handleSaveRule = async (data: AutomationCreate | AutomationUpdate) => {
    if (editingRule && editingRule.id) {
      await apiService.updateAutomation(editingRule.id, data as AutomationUpdate);
    } else {
      await apiService.createAutomation(data as AutomationCreate);
    }
    await fetchData();
  };

  return (
    <div className="flex flex-col h-full space-y-4 p-6 bg-slate-950 text-slate-100 overflow-hidden">
      {/* Top Banner / HUD Header */}
      <div className="flex items-center justify-between pb-4 border-b border-cyan-500/30">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-lg bg-cyan-950/60 border border-cyan-500/40 text-cyan-400 shadow-lg shadow-cyan-950/30">
            <Zap className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-lg font-bold tracking-wider text-slate-100 uppercase font-mono">
                Automation Command Center
              </h1>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold">
                v0.7
              </span>
              {status?.is_paused && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 font-semibold animate-pulse">
                  PAUSED
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 font-mono">
              Proactive Intelligence, Scheduled Routines, Smart Reminders & Event Automation
            </p>
          </div>
        </div>

        {/* Global Controls */}
        <div className="flex items-center space-x-3">
          <button
            onClick={handleToggleGlobalPause}
            className={`px-3 py-1.5 text-xs font-mono uppercase rounded border transition-all flex items-center gap-1.5 font-semibold ${
              status?.is_paused
                ? 'bg-amber-500/20 border-amber-500/50 text-amber-300 hover:bg-amber-500/30'
                : 'bg-slate-900 border-slate-700 text-slate-300 hover:border-cyan-500/40 hover:text-cyan-400'
            }`}
          >
            {status?.is_paused ? <Play className="w-3.5 h-3.5 text-amber-400" /> : <Pause className="w-3.5 h-3.5" />}
            {status?.is_paused ? 'Resume All' : 'Pause All'}
          </button>

          <button
            onClick={handleCreateNew}
            className="px-4 py-1.5 text-xs font-mono uppercase bg-cyan-500 text-slate-950 font-bold rounded hover:bg-cyan-400 transition-colors flex items-center gap-1.5 shadow-md shadow-cyan-500/20"
          >
            <Plus className="w-3.5 h-3.5" />
            New Routine
          </button>
        </div>
      </div>

      {/* Telemetry / Status Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="p-3.5 rounded-lg bg-slate-900/60 border border-cyan-500/20 shadow-md">
          <span className="text-[10px] font-mono uppercase text-slate-400">Active Automations</span>
          <div className="text-xl font-bold font-mono text-cyan-400 mt-0.5">
            {status ? `${status.active_count} / ${status.total_count}` : '--'}
          </div>
        </div>

        <div className="p-3.5 rounded-lg bg-slate-900/60 border border-cyan-500/20 shadow-md">
          <span className="text-[10px] font-mono uppercase text-slate-400">Next Scheduled Run</span>
          <div className="text-xs font-bold font-mono text-amber-400 mt-1 truncate">
            {status?.next_scheduled_run
              ? new Date(status.next_scheduled_run).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })
              : 'None Scheduled'}
          </div>
        </div>

        <div className="p-3.5 rounded-lg bg-slate-900/60 border border-cyan-500/20 shadow-md">
          <span className="text-[10px] font-mono uppercase text-slate-400">Pending Reminders</span>
          <div className="text-xl font-bold font-mono text-emerald-400 mt-0.5">
            {status?.pending_reminders_count ?? 0}
          </div>
        </div>

        <div className="p-3.5 rounded-lg bg-slate-900/60 border border-cyan-500/20 shadow-md">
          <span className="text-[10px] font-mono uppercase text-slate-400">Unread Alerts</span>
          <div className="text-xl font-bold font-mono text-purple-400 mt-0.5">
            {status?.unread_notifications_count ?? 0}
          </div>
        </div>
      </div>

      {/* Subnavigation Tabs */}
      <div className="flex items-center space-x-2 border-b border-slate-800">
        {[
          { id: 'routines', label: 'Automations', icon: Zap },
          { id: 'templates', label: 'Routine Templates', icon: Sparkles },
          { id: 'briefing', label: 'Daily Briefing', icon: Sun },
          { id: 'health', label: 'Project Health', icon: Activity },
          { id: 'notifications', label: 'Notification Center', icon: Bell },
          { id: 'history', label: 'Execution History', icon: History },
        ].map(t => {
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              onClick={() => {
                if (t.id === 'history' && !selectedHistoryRuleId) {
                  apiService.getAutomationHistory('', 50).then(setHistory);
                }
                setActiveTab(t.id as any);
              }}
              className={`px-4 py-2 text-xs font-mono uppercase tracking-wider transition-all flex items-center gap-2 border-b-2 ${
                activeTab === t.id
                  ? 'border-cyan-400 text-cyan-400 font-bold bg-cyan-950/20'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Tab Panels */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {activeTab === 'routines' && (
          <AutomationList
            automations={automations}
            onToggleEnable={handleToggleEnable}
            onRunNow={handleRunNow}
            onEdit={rule => {
              setEditingRule(rule);
              setIsEditorOpen(true);
            }}
            onDelete={handleDelete}
            onViewHistory={handleViewHistory}
            runningIds={runningIds}
          />
        )}

        {activeTab === 'templates' && (
          <RoutineTemplates
            templates={templates}
            onUseTemplate={handleUseTemplate}
          />
        )}

        {activeTab === 'briefing' && <DailyBriefingPanel />}

        {activeTab === 'health' && <ProjectHealthPanel />}

        {activeTab === 'notifications' && <NotificationCenter />}

        {activeTab === 'history' && (
          <AutomationHistory
            automationId={selectedHistoryRuleId}
            history={history}
            onBack={() => {
              setSelectedHistoryRuleId(undefined);
              setActiveTab('routines');
            }}
          />
        )}
      </div>

      {/* Editor Modal */}
      {isEditorOpen && (
        <AutomationEditor
          initialRule={editingRule}
          onSave={handleSaveRule}
          onClose={() => {
            setIsEditorOpen(false);
            setEditingRule(null);
          }}
        />
      )}
    </div>
  );
};
