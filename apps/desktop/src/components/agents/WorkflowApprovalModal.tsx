import React, { useState } from 'react';
import { 
  ShieldAlert, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Bot, 
  Wrench, 
  Terminal,
  Lock
} from 'lucide-react';
import { WorkflowStep } from '../../types';

interface WorkflowApprovalModalProps {
  step: WorkflowStep | null;
  workflowId: string;
  isOpen: boolean;
  onApprove: (stepId: number) => Promise<void>;
  onReject: (stepId: number, reason: string) => Promise<void>;
  onClose: () => void;
}

export const WorkflowApprovalModal: React.FC<WorkflowApprovalModalProps> = ({
  step,
  workflowId,
  isOpen,
  onApprove,
  onReject,
  onClose
}) => {
  const [rejectReason, setRejectReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showRejectInput, setShowRejectInput] = useState(false);

  if (!isOpen || !step) return null;

  const handleApprove = async () => {
    try {
      setIsSubmitting(true);
      await onApprove(step.step_id);
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    try {
      setIsSubmitting(true);
      await onReject(step.step_id, rejectReason || 'Step rejected by operator');
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="hud-panel w-full max-w-lg p-5 rounded-lg border-2 border-purple-500/80 bg-slate-900 shadow-[0_0_30px_rgba(168,85,247,0.3)]">
        {/* Header */}
        <div className="flex items-center gap-3 border-b border-purple-500/30 pb-3 mb-4">
          <div className="p-2 rounded bg-purple-500/20 text-purple-400 border border-purple-500/40 animate-pulse">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-sm font-mono font-bold text-purple-300 uppercase tracking-wider">
              HUMAN CONFIRMATION CHECKPOINT
            </h3>
            <p className="text-xs text-slate-400 font-mono">
              Workflow: {workflowId} | Step #{step.step_id}
            </p>
          </div>
        </div>

        {/* Warning Banner */}
        <div className="p-3 rounded bg-purple-950/40 border border-purple-500/40 text-xs text-purple-200 mb-4 flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />
          <span>
            This step requires explicit human approval under NOVA v0.4 & v0.6 security policy before proceeding. The orchestrator will pause until you grant or deny authorization.
          </span>
        </div>

        {/* Step Details */}
        <div className="space-y-3 mb-4 text-xs font-mono">
          <div className="p-3 rounded bg-slate-950 border border-slate-800 space-y-2">
            <div className="flex justify-between items-center text-slate-400">
              <span className="uppercase text-slate-500">Operation:</span>
              <span className="text-slate-200 font-semibold">{step.description}</span>
            </div>
            <div className="flex justify-between items-center text-slate-400">
              <span className="uppercase text-slate-500">Assigned Agent:</span>
              <span className="text-cyan-400 font-semibold flex items-center gap-1">
                <Bot className="w-3.5 h-3.5" />
                {step.assigned_agent.toUpperCase()}
              </span>
            </div>
            <div className="flex justify-between items-center text-slate-400">
              <span className="uppercase text-slate-500">Target Tool:</span>
              <span className="text-emerald-400 font-semibold flex items-center gap-1">
                <Wrench className="w-3.5 h-3.5" />
                {step.required_tool || 'None (Logical Task)'}
              </span>
            </div>
            <div className="flex justify-between items-center text-slate-400">
              <span className="uppercase text-slate-500">Security Classification:</span>
              <span className="text-amber-400 font-bold uppercase">{step.permission_level}</span>
            </div>
          </div>

          {/* Arguments */}
          <div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1">
              <Terminal className="w-3 h-3 text-cyan-400" />
              Operation Arguments:
            </div>
            <pre className="p-2.5 rounded bg-slate-950 border border-slate-800 text-[11px] text-slate-300 max-h-32 overflow-y-auto custom-scrollbar whitespace-pre-wrap">
              {JSON.stringify(step.input_arguments, null, 2)}
            </pre>
          </div>
        </div>

        {/* Reject reason input */}
        {showRejectInput && (
          <div className="mb-4">
            <label className="text-[11px] font-mono text-slate-400 block mb-1">
              Rejection Reason:
            </label>
            <input
              type="text"
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="e.g. Unsafe parameters, wrong workspace, redundant task..."
              className="w-full px-3 py-1.5 text-xs font-mono rounded bg-slate-950 border border-slate-700 text-slate-200 focus:outline-none focus:border-purple-400"
            />
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between gap-2 pt-2 border-t border-slate-800">
          {!showRejectInput ? (
            <button
              onClick={() => setShowRejectInput(true)}
              disabled={isSubmitting}
              className="px-3 py-1.5 rounded bg-rose-950/60 hover:bg-rose-900 border border-rose-800 text-rose-300 font-mono text-xs transition-colors"
            >
              Reject Step
            </button>
          ) : (
            <button
              onClick={handleReject}
              disabled={isSubmitting}
              className="px-3 py-1.5 rounded bg-rose-600 hover:bg-rose-500 text-white font-mono text-xs font-semibold transition-colors flex items-center gap-1"
            >
              <XCircle className="w-3.5 h-3.5" />
              Confirm Rejection
            </button>
          )}

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              disabled={isSubmitting}
              className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono text-xs transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleApprove}
              disabled={isSubmitting}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded bg-purple-600 hover:bg-purple-500 text-white font-mono text-xs font-bold uppercase transition-colors shadow-[0_0_15px_rgba(168,85,247,0.4)]"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              {isSubmitting ? 'Approving...' : 'Authorize Execution'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
