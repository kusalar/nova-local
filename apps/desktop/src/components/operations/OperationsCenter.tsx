import React, { useState, useEffect, useCallback } from 'react';
import { 
  Wrench, 
  Layers, 
  History, 
  Terminal, 
  ShieldCheck, 
  Sparkles, 
  RefreshCw,
  Cpu,
  ArrowLeft,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';
import { AvailableToolsPanel } from './AvailableToolsPanel';
import { TaskPlannerPanel } from './TaskPlannerPanel';
import { ExecutionTimeline } from './ExecutionTimeline';
import { ExecutionHistoryTable } from './ExecutionHistoryTable';
import { ApprovalModal } from './ApprovalModal';
import { apiService } from '../../services/api';
import { ToolDefinition, TaskPlan, ExecutionRecord } from '../../types';

interface OperationsCenterProps {
  onBackToDashboard: () => void;
}

export const OperationsCenter: React.FC<OperationsCenterProps> = ({ onBackToDashboard }) => {
  const [activeSubTab, setActiveSubTab] = useState<'planner' | 'tools' | 'history'>('planner');
  
  // Data State
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [executions, setExecutions] = useState<ExecutionRecord[]>([]);
  const [activePlan, setActivePlan] = useState<TaskPlan | null>(null);
  
  // Loading & Action states
  const [isLoadingTools, setIsLoadingTools] = useState(false);
  const [isLoadingExecutions, setIsLoadingExecutions] = useState(false);
  const [isPlanning, setIsPlanning] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [isApprovalModalOpen, setIsApprovalModalOpen] = useState(false);
  const [notification, setNotification] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showNotification = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const loadTools = useCallback(async () => {
    try {
      setIsLoadingTools(true);
      const data = await apiService.getTools();
      setTools(data);
    } catch (err: any) {
      showNotification(`Failed to load tools: ${err.message}`, 'error');
    } finally {
      setIsLoadingTools(false);
    }
  }, []);

  const loadExecutions = useCallback(async () => {
    try {
      setIsLoadingExecutions(true);
      const data = await apiService.listExecutions(50);
      setExecutions(data);
    } catch (err: any) {
      showNotification(`Failed to load executions: ${err.message}`, 'error');
    } finally {
      setIsLoadingExecutions(false);
    }
  }, []);

  useEffect(() => {
    loadTools();
    loadExecutions();
  }, [loadTools, loadExecutions]);

  const handlePlanTask = async (prompt: string): Promise<TaskPlan | null> => {
    try {
      setIsPlanning(true);
      const plan = await apiService.planTask(prompt);
      setActivePlan(plan);
      showNotification(`Generated plan with ${plan.steps.length} steps.`, 'success');
      return plan;
    } catch (err: any) {
      showNotification(`Planning failed: ${err.message}`, 'error');
      return null;
    } finally {
      setIsPlanning(false);
    }
  };

  const handleExecutePlan = async (plan: TaskPlan) => {
    if (plan.requires_confirmation) {
      setIsApprovalModalOpen(true);
      return;
    }

    try {
      setIsExecuting(true);
      const executed = await apiService.executeTask(plan.task_id, plan);
      setActivePlan(executed);
      await loadExecutions();
      if (executed.status === 'COMPLETED') {
        showNotification(`Task '${executed.task_id}' executed successfully!`, 'success');
      } else {
        showNotification(`Task completed with status: ${executed.status}`, 'info');
      }
    } catch (err: any) {
      showNotification(`Execution failed: ${err.message}`, 'error');
    } finally {
      setIsExecuting(false);
    }
  };

  const handleApprove = async (taskId: string) => {
    try {
      setIsExecuting(true);
      const approved = await apiService.approveTask(taskId);
      setActivePlan(approved);
      setIsApprovalModalOpen(false);
      await loadExecutions();
      showNotification(`Approved and executed task '${taskId}'!`, 'success');
    } catch (err: any) {
      showNotification(`Approval failed: ${err.message}`, 'error');
    } finally {
      setIsExecuting(false);
    }
  };

  const handleReject = async (taskId: string) => {
    try {
      const rejected = await apiService.rejectTask(taskId);
      setActivePlan(rejected);
      setIsApprovalModalOpen(false);
      showNotification(`Task '${taskId}' rejected.`, 'info');
    } catch (err: any) {
      showNotification(`Rejection failed: ${err.message}`, 'error');
    }
  };

  const handleCancelTask = async (taskId: string) => {
    try {
      const cancelled = await apiService.cancelTask(taskId);
      setActivePlan(cancelled);
      showNotification(`Task '${taskId}' cancelled.`, 'info');
    } catch (err: any) {
      showNotification(`Cancellation failed: ${err.message}`, 'error');
    }
  };

  const handleRollback = async (executionId: string) => {
    try {
      const res = await apiService.rollbackExecution(executionId);
      showNotification(`Rollback successful: ${res.detail}`, 'success');
      await loadExecutions();
    } catch (err: any) {
      showNotification(`Rollback error: ${err.message}`, 'error');
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-nova-dark/95 text-slate-100 p-4 space-y-3.5 select-none font-sans">
      {/* Top Header & Status Banner */}
      <div className="flex items-center justify-between p-3.5 bg-nova-surface/60 border border-nova-border/70 rounded-xl">
        <div className="flex items-center gap-3">
          <button
            onClick={onBackToDashboard}
            className="p-2 rounded-lg bg-nova-dark/80 hover:bg-nova-dark text-slate-400 hover:text-nova-cyan border border-nova-border/60 transition-all flex items-center gap-1.5 text-xs font-mono"
            title="Return to Main Dashboard"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Command Center
          </button>

          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-bold text-slate-100 font-display tracking-wider flex items-center gap-2">
                <Wrench className="w-4 h-4 text-nova-cyan" />
                OPERATIONS CENTER v0.4
              </h1>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-nova-cyan/10 text-nova-cyan border border-nova-cyan/30">
                OFFLINE AUTONOMOUS ENGINE
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Secure desktop tools, multi-step task planning, authorization gates, and audit rollback.
            </p>
          </div>
        </div>

        {/* Global Stats */}
        <div className="hidden lg:flex items-center gap-3 text-xs font-mono">
          <div className="px-3 py-1.5 rounded-lg bg-nova-dark/60 border border-nova-border/50 text-center">
            <span className="text-[10px] text-slate-400 block uppercase">Verified Tools</span>
            <span className="text-sm font-bold text-nova-cyan">{tools.length}</span>
          </div>

          <div className="px-3 py-1.5 rounded-lg bg-nova-dark/60 border border-nova-border/50 text-center">
            <span className="text-[10px] text-slate-400 block uppercase">Audit Events</span>
            <span className="text-sm font-bold text-purple-400">{executions.length}</span>
          </div>

          <div className="px-3 py-1.5 rounded-lg bg-nova-dark/60 border border-nova-border/50 text-center">
            <span className="text-[10px] text-slate-400 block uppercase">Security Boundary</span>
            <span className="text-sm font-bold text-emerald-400">Strict Roots</span>
          </div>
        </div>
      </div>

      {/* Sub-Navigation Tabs */}
      <div className="flex items-center justify-between border-b border-nova-border/60 pb-2">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveSubTab('planner')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold font-display tracking-wider transition-all flex items-center gap-1.5 ${
              activeSubTab === 'planner'
                ? 'bg-nova-surface border border-nova-cyan/50 text-nova-cyan shadow-[0_0_12px_rgba(0,240,255,0.2)]'
                : 'text-slate-400 hover:text-slate-200 hover:bg-nova-surface/40'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            DIRECTIVE PLANNER
          </button>

          <button
            onClick={() => setActiveSubTab('tools')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold font-display tracking-wider transition-all flex items-center gap-1.5 ${
              activeSubTab === 'tools'
                ? 'bg-nova-surface border border-nova-cyan/50 text-nova-cyan shadow-[0_0_12px_rgba(0,240,255,0.2)]'
                : 'text-slate-400 hover:text-slate-200 hover:bg-nova-surface/40'
            }`}
          >
            <Wrench className="w-3.5 h-3.5" />
            TOOL CATALOG ({tools.length})
          </button>

          <button
            onClick={() => setActiveSubTab('history')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold font-display tracking-wider transition-all flex items-center gap-1.5 ${
              activeSubTab === 'history'
                ? 'bg-nova-surface border border-nova-cyan/50 text-nova-cyan shadow-[0_0_12px_rgba(0,240,255,0.2)]'
                : 'text-slate-400 hover:text-slate-200 hover:bg-nova-surface/40'
            }`}
          >
            <History className="w-3.5 h-3.5" />
            AUDIT & ROLLBACK
          </button>
        </div>

        {notification && (
          <div className={`px-3 py-1 rounded-lg text-xs font-mono flex items-center gap-1.5 border ${
            notification.type === 'success' ? 'bg-emerald-950/50 text-emerald-300 border-emerald-500/40' :
            notification.type === 'error' ? 'bg-rose-950/50 text-rose-300 border-rose-500/40' :
            'bg-cyan-950/50 text-cyan-300 border-cyan-500/40'
          }`}>
            {notification.type === 'success' ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
            {notification.message}
          </div>
        )}
      </div>

      {/* Main Tab Content */}
      <div className="flex-1 overflow-hidden relative">
        {activeSubTab === 'planner' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5 h-full">
            <div className="lg:col-span-7 h-full overflow-hidden">
              <TaskPlannerPanel
                onPlanTask={handlePlanTask}
                onExecutePlan={handleExecutePlan}
                activePlan={activePlan}
                isPlanning={isPlanning}
                isExecuting={isExecuting}
              />
            </div>

            <div className="lg:col-span-5 h-full overflow-hidden">
              <ExecutionTimeline
                task={activePlan}
                onCancelTask={handleCancelTask}
                onRollback={handleRollback}
              />
            </div>
          </div>
        )}

        {activeSubTab === 'tools' && (
          <AvailableToolsPanel
            tools={tools}
            isLoading={isLoadingTools}
          />
        )}

        {activeSubTab === 'history' && (
          <ExecutionHistoryTable
            executions={executions}
            isLoading={isLoadingExecutions}
            onRefresh={loadExecutions}
            onRollback={handleRollback}
          />
        )}
      </div>

      {/* Confirmation Authorization Modal */}
      <ApprovalModal
        isOpen={isApprovalModalOpen}
        onClose={() => setIsApprovalModalOpen(false)}
        task={activePlan}
        onApprove={handleApprove}
        onReject={handleReject}
        isProcessing={isExecuting}
      />
    </div>
  );
};
