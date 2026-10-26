import React, { useState, useEffect, useCallback } from 'react';
import { 
  Bot, 
  Layers, 
  GitFork, 
  History, 
  FileText, 
  ShieldCheck, 
  RefreshCw, 
  ArrowLeft,
  Activity,
  AlertCircle,
  CheckCircle2,
  Cpu
} from 'lucide-react';
import { 
  AgentMetadata, 
  WorkflowPlan, 
  WorkflowStep, 
  WorkflowReport as IWorkflowReport, 
  WorkflowSummary, 
  WorkflowEvent 
} from '../../types';
import { apiService } from '../../services/api';

import { AgentRegistryPanel } from './AgentRegistryPanel';
import { AgentDetailPanel } from './AgentDetailPanel';
import { WorkflowPlanner } from './WorkflowPlanner';
import { WorkflowExecutionGraph } from './WorkflowExecutionGraph';
import { WorkflowApprovalModal } from './WorkflowApprovalModal';
import { WorkflowReport } from './WorkflowReport';
import { WorkflowHistory } from './WorkflowHistory';
import { AgentActivityFeed } from './AgentActivityFeed';

interface AgentCommandCenterProps {
  onBackToDashboard: () => void;
}

export const AgentCommandCenter: React.FC<AgentCommandCenterProps> = ({
  onBackToDashboard
}) => {
  const [activeSubTab, setActiveSubTab] = useState<'planner' | 'graph' | 'registry' | 'history' | 'report'>('planner');

  // Agent & Workflow data
  const [agents, setAgents] = useState<AgentMetadata[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<AgentMetadata | null>(null);
  const [activePlan, setActivePlan] = useState<WorkflowPlan | null>(null);
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [workflowReport, setWorkflowReport] = useState<IWorkflowReport | null>(null);
  const [workflowEvents, setWorkflowEvents] = useState<WorkflowEvent[]>([]);

  // Approval modal state
  const [isApprovalModalOpen, setIsApprovalModalOpen] = useState(false);
  const [pendingApprovalStep, setPendingApprovalStep] = useState<WorkflowStep | null>(null);

  // Loading states
  const [isLoadingAgents, setIsLoadingAgents] = useState(false);
  const [isLoadingWorkflows, setIsLoadingWorkflows] = useState(false);
  const [isPlanning, setIsPlanning] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [notification, setNotification] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showNotification = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

  // Load registered agents
  const loadAgents = useCallback(async () => {
    try {
      setIsLoadingAgents(true);
      const data = await apiService.listAgents();
      setAgents(data);
    } catch (err: any) {
      showNotification(`Failed to load agents: ${err.message}`, 'error');
    } finally {
      setIsLoadingAgents(false);
    }
  }, []);

  // Load workflow history
  const loadWorkflows = useCallback(async () => {
    try {
      setIsLoadingWorkflows(true);
      const data = await apiService.listWorkflows(20);
      setWorkflows(data);
    } catch (err: any) {
      showNotification(`Failed to load workflow history: ${err.message}`, 'error');
    } finally {
      setIsLoadingWorkflows(false);
    }
  }, []);

  useEffect(() => {
    loadAgents();
    loadWorkflows();
  }, [loadAgents, loadWorkflows]);

  // Refresh active workflow and check for pending approvals
  const refreshActiveWorkflow = useCallback(async (workflowId: string) => {
    try {
      const plan = await apiService.getWorkflowById(workflowId);
      setActivePlan(plan);

      // Check if any step requires human approval
      const waitingStep = plan.steps.find(s => s.status === 'waiting_approval');
      if (waitingStep) {
        setPendingApprovalStep(waitingStep);
        setIsApprovalModalOpen(true);
      } else {
        setPendingApprovalStep(null);
      }

      // If workflow has completed or failed, load its final report
      if (plan.status === 'completed' || plan.status === 'failed') {
        try {
          const rep = await apiService.getWorkflowReport(workflowId);
          setWorkflowReport(rep);
        } catch {
          // Report may still be finalizing
        }
      }

      // Load events
      try {
        const evts = await apiService.getWorkflowEvents(workflowId);
        setWorkflowEvents(evts);
      } catch {
        // Events optional
      }
    } catch (err: any) {
      console.warn('Error refreshing workflow:', err);
    }
  }, []);

  // Poll active workflow when running
  useEffect(() => {
    if (!activePlan || (activePlan.status !== 'running' && activePlan.status !== 'waiting_approval')) {
      return;
    }

    const interval = setInterval(() => {
      refreshActiveWorkflow(activePlan.workflow_id);
    }, 2000);

    return () => clearInterval(interval);
  }, [activePlan, refreshActiveWorkflow]);

  // Handle plan workflow
  const handlePlanWorkflow = async (objective: string, projectId?: string) => {
    try {
      setIsPlanning(true);
      const plan = await apiService.planWorkflow(objective, projectId);
      setActivePlan(plan);
      setActiveSubTab('graph');
      showNotification(`Workflow planned: ${plan.steps.length} steps generated`, 'success');
      loadWorkflows();
      return plan;
    } catch (err: any) {
      showNotification(`Planning failed: ${err.message}`, 'error');
      return null;
    } finally {
      setIsPlanning(false);
    }
  };

  // Handle execute workflow
  const handleExecuteWorkflow = async (workflowId: string) => {
    try {
      setIsExecuting(true);
      const plan = await apiService.executeWorkflow(workflowId);
      setActivePlan(plan);
      setActiveSubTab('graph');
      showNotification(`Workflow ${workflowId} execution started`, 'info');
      // Immediate poll
      setTimeout(() => refreshActiveWorkflow(workflowId), 1000);
    } catch (err: any) {
      showNotification(`Execution failed: ${err.message}`, 'error');
    } finally {
      setIsExecuting(false);
    }
  };

  // Handle approve step
  const handleApproveStep = async (stepId: number) => {
    if (!activePlan) return;
    try {
      const updated = await apiService.approveWorkflowStep(activePlan.workflow_id, stepId);
      setActivePlan(updated);
      showNotification(`Step #${stepId} approved. Resuming execution...`, 'success');
      setTimeout(() => refreshActiveWorkflow(activePlan.workflow_id), 1000);
    } catch (err: any) {
      showNotification(`Approval failed: ${err.message}`, 'error');
    }
  };

  // Handle reject step
  const handleRejectStep = async (stepId: number, reason: string) => {
    if (!activePlan) return;
    try {
      const updated = await apiService.rejectWorkflowStep(activePlan.workflow_id, stepId, reason);
      setActivePlan(updated);
      showNotification(`Step #${stepId} rejected`, 'info');
      setTimeout(() => refreshActiveWorkflow(activePlan.workflow_id), 1000);
    } catch (err: any) {
      showNotification(`Rejection failed: ${err.message}`, 'error');
    }
  };

  // Handle cancel workflow
  const handleCancelWorkflow = async () => {
    if (!activePlan) return;
    try {
      const updated = await apiService.cancelWorkflow(activePlan.workflow_id);
      setActivePlan(updated);
      showNotification(`Workflow ${activePlan.workflow_id} cancelled`, 'info');
    } catch (err: any) {
      showNotification(`Cancellation failed: ${err.message}`, 'error');
    }
  };

  // Handle resume workflow
  const handleResumeWorkflow = async () => {
    if (!activePlan) return;
    try {
      const updated = await apiService.resumeWorkflow(activePlan.workflow_id);
      setActivePlan(updated);
      showNotification(`Workflow ${activePlan.workflow_id} resumed`, 'success');
      setTimeout(() => refreshActiveWorkflow(activePlan.workflow_id), 1000);
    } catch (err: any) {
      showNotification(`Resume failed: ${err.message}`, 'error');
    }
  };

  // Handle select past workflow
  const handleSelectWorkflow = async (workflowId: string) => {
    await refreshActiveWorkflow(workflowId);
    setActiveSubTab('graph');
  };

  return (
    <div className="flex-1 flex flex-col h-[calc(100vh-65px)] overflow-hidden bg-nova-dark/95 select-none p-4 custom-scrollbar">
      {/* Top Bar with Navigation & HUD Indicators */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-nova-border/70 mb-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onBackToDashboard}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-mono bg-slate-900 border border-slate-700/80 hover:border-cyan-500 hover:text-cyan-400 text-slate-300 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            BACK TO HUD
          </button>

          <div className="h-4 w-px bg-slate-800" />

          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-cyan-950/60 border border-cyan-800/80 text-cyan-400">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold font-mono text-cyan-300 tracking-wider">
                NOVA AGENT COMMAND CENTER
              </h2>
              <span className="text-[10px] font-mono text-slate-400">
                v0.6 Advanced Multi-Agent Orchestration Engine
              </span>
            </div>
          </div>
        </div>

        {/* Sub-tab navigation */}
        <div className="flex items-center gap-1 p-1 rounded-lg bg-slate-950/80 border border-slate-800">
          <button
            onClick={() => setActiveSubTab('planner')}
            className={`flex items-center gap-1.5 px-3 py-1 text-xs font-mono rounded transition-colors ${
              activeSubTab === 'planner'
                ? 'bg-cyan-600 text-slate-950 font-bold shadow-[0_0_8px_rgba(6,182,212,0.4)]'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            Planner
          </button>

          <button
            onClick={() => setActiveSubTab('graph')}
            className={`flex items-center gap-1.5 px-3 py-1 text-xs font-mono rounded transition-colors ${
              activeSubTab === 'graph'
                ? 'bg-cyan-600 text-slate-950 font-bold shadow-[0_0_8px_rgba(6,182,212,0.4)]'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <GitFork className="w-3.5 h-3.5" />
            Execution Graph
          </button>

          <button
            onClick={() => setActiveSubTab('registry')}
            className={`flex items-center gap-1.5 px-3 py-1 text-xs font-mono rounded transition-colors ${
              activeSubTab === 'registry'
                ? 'bg-cyan-600 text-slate-950 font-bold shadow-[0_0_8px_rgba(6,182,212,0.4)]'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Cpu className="w-3.5 h-3.5" />
            Agent Registry
          </button>

          <button
            onClick={() => setActiveSubTab('history')}
            className={`flex items-center gap-1.5 px-3 py-1 text-xs font-mono rounded transition-colors ${
              activeSubTab === 'history'
                ? 'bg-cyan-600 text-slate-950 font-bold shadow-[0_0_8px_rgba(6,182,212,0.4)]'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <History className="w-3.5 h-3.5" />
            History
          </button>

          <button
            onClick={() => setActiveSubTab('report')}
            className={`flex items-center gap-1.5 px-3 py-1 text-xs font-mono rounded transition-colors ${
              activeSubTab === 'report'
                ? 'bg-cyan-600 text-slate-950 font-bold shadow-[0_0_8px_rgba(6,182,212,0.4)]'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            Report
          </button>
        </div>
      </div>

      {/* Notifications */}
      {notification && (
        <div className={`mb-3 p-2.5 rounded-md text-xs font-mono flex items-center justify-between border ${
          notification.type === 'error' ? 'bg-rose-950/60 border-rose-800 text-rose-300' :
          notification.type === 'success' ? 'bg-emerald-950/60 border-emerald-800 text-emerald-300' :
          'bg-cyan-950/60 border-cyan-800 text-cyan-300'
        }`}>
          <div className="flex items-center gap-2">
            {notification.type === 'error' ? <AlertCircle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
            <span>{notification.message}</span>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto space-y-4 custom-scrollbar">
        {activeSubTab === 'planner' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            <div className="lg:col-span-8">
              <WorkflowPlanner
                onPlanWorkflow={handlePlanWorkflow}
                onExecuteWorkflow={handleExecuteWorkflow}
                activePlan={activePlan}
                isPlanning={isPlanning}
                isExecuting={isExecuting}
              />
            </div>
            <div className="lg:col-span-4 space-y-4">
              <AgentActivityFeed events={workflowEvents} />
            </div>
          </div>
        )}

        {activeSubTab === 'graph' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            <div className="lg:col-span-8">
              <WorkflowExecutionGraph
                plan={activePlan}
                onApproveStep={(stepId) => {
                  const step = activePlan?.steps.find(s => s.step_id === stepId) || null;
                  setPendingApprovalStep(step);
                  setIsApprovalModalOpen(true);
                }}
                onCancelWorkflow={handleCancelWorkflow}
                onResumeWorkflow={handleResumeWorkflow}
                isExecuting={isExecuting}
              />
            </div>
            <div className="lg:col-span-4 space-y-4">
              <AgentActivityFeed events={workflowEvents} />
            </div>
          </div>
        )}

        {activeSubTab === 'registry' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            <div className={selectedAgent ? "lg:col-span-8" : "lg:col-span-12"}>
              <AgentRegistryPanel
                agents={agents}
                selectedAgent={selectedAgent}
                onSelectAgent={(ag) => setSelectedAgent(ag)}
                isLoading={isLoadingAgents}
              />
            </div>
            {selectedAgent && (
              <div className="lg:col-span-4">
                <AgentDetailPanel
                  agent={selectedAgent}
                  onClose={() => setSelectedAgent(null)}
                />
              </div>
            )}
          </div>
        )}

        {activeSubTab === 'history' && (
          <WorkflowHistory
            workflows={workflows}
            selectedWorkflowId={activePlan?.workflow_id || null}
            onSelectWorkflow={handleSelectWorkflow}
            isLoading={isLoadingWorkflows}
            onRefresh={loadWorkflows}
          />
        )}

        {activeSubTab === 'report' && (
          <WorkflowReport
            report={workflowReport}
          />
        )}
      </div>

      {/* Human Approval Checkpoint Modal */}
      {isApprovalModalOpen && pendingApprovalStep && activePlan && (
        <WorkflowApprovalModal
          isOpen={isApprovalModalOpen}
          step={pendingApprovalStep}
          workflowId={activePlan.workflow_id}
          onApprove={handleApproveStep}
          onReject={handleRejectStep}
          onClose={() => setIsApprovalModalOpen(false)}
        />
      )}
    </div>
  );
};
