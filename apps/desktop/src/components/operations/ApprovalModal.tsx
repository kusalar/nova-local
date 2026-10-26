import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, ShieldCheck, XCircle, CheckCircle, RefreshCw, Layers } from 'lucide-react';
import { TaskPlan } from '../../types';

interface ApprovalModalProps {
  isOpen: boolean;
  onClose: () => void;
  task: TaskPlan | null;
  onApprove: (taskId: string) => void;
  onReject: (taskId: string) => void;
  isProcessing?: boolean;
}

export const ApprovalModal: React.FC<ApprovalModalProps> = ({
  isOpen,
  onClose,
  task,
  onApprove,
  onReject,
  isProcessing = false
}) => {
  if (!isOpen || !task) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          className="w-full max-w-xl bg-nova-surface border border-amber-500/40 rounded-xl shadow-[0_0_40px_rgba(245,158,11,0.2)] overflow-hidden flex flex-col font-mono"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-amber-500/30 bg-amber-950/20">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400">
                <AlertTriangle className="w-5 h-5 animate-pulse" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-slate-100 font-display tracking-wider">
                  DIRECTIVE CONFIRMATION REQUIRED
                </h2>
                <p className="text-[11px] text-amber-400/80">
                  Task ID: {task.task_id}
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              disabled={isProcessing}
              className="text-slate-400 hover:text-slate-200 transition-colors p-1"
            >
              <XCircle className="w-5 h-5" />
            </button>
          </div>

          {/* Body */}
          <div className="p-6 space-y-4 max-h-[60vh] overflow-y-auto custom-scrollbar">
            {/* Directive Overview */}
            <div className="p-3.5 bg-nova-dark/70 rounded-lg border border-nova-border/60">
              <div className="text-[11px] text-slate-400 mb-1 uppercase tracking-wider font-semibold">
                User Directive
              </div>
              <div className="text-xs text-slate-200 font-sans italic">
                "{task.prompt}"
              </div>
              <div className="mt-2 text-xs text-amber-300 font-sans">
                {task.description}
              </div>
            </div>

            {/* Impact & Reason */}
            {task.confirmation_reason && (
              <div className="p-3 bg-amber-950/30 border border-amber-500/30 rounded-lg text-xs text-amber-200">
                <span className="font-semibold text-amber-400 block mb-0.5">Authorization Reason:</span>
                {task.confirmation_reason}
              </div>
            )}

            {/* Steps & Resources Affected */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-slate-400 font-semibold tracking-wider uppercase">
                  Operation Breakdown ({task.steps.length} {task.steps.length === 1 ? 'Step' : 'Steps'})
                </span>
                <span className="text-[11px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30">
                  Confirmation Enforced
                </span>
              </div>

              <div className="space-y-2">
                {task.steps.map((step) => {
                  const isConf = step.permission_level === 'CONFIRMATION_REQUIRED';
                  return (
                    <div
                      key={step.step_id}
                      className={`p-3 rounded-lg border text-xs ${
                        isConf
                          ? 'bg-amber-950/20 border-amber-500/40 text-amber-100'
                          : 'bg-nova-dark/50 border-nova-border/50 text-slate-300'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-bold flex items-center gap-1.5">
                          <span className="w-4 h-4 rounded-full bg-slate-800 text-[10px] flex items-center justify-center text-slate-300">
                            {step.step_id}
                          </span>
                          {step.tool_id}
                        </span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                          isConf ? 'bg-amber-500/20 text-amber-300' : 'bg-slate-800 text-slate-400'
                        }`}>
                          {step.permission_level}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-300 font-sans">
                        {step.description}
                      </div>

                      {/* Display Arguments */}
                      {Object.keys(step.arguments).length > 0 && (
                        <div className="mt-1.5 p-1.5 bg-black/40 rounded text-[10px] text-slate-400 overflow-x-auto">
                          {JSON.stringify(step.arguments)}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Security Guarantee */}
            <div className="flex items-center gap-2 p-2.5 rounded bg-nova-cyan/5 border border-nova-cyan/20 text-[11px] text-nova-cyan">
              <ShieldCheck className="w-4 h-4 flex-shrink-0" />
              <span>
                Reversible operations can be undone through the Execution History audit ledger.
              </span>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-nova-border/60 bg-nova-dark/50">
            <button
              onClick={() => onReject(task.task_id)}
              disabled={isProcessing}
              className="px-4 py-2 rounded-lg text-xs font-semibold text-rose-400 hover:text-rose-300 hover:bg-rose-950/30 border border-rose-500/30 transition-all flex items-center gap-1.5"
            >
              <XCircle className="w-4 h-4" />
              Reject Operation
            </button>

            <button
              onClick={() => onApprove(task.task_id)}
              disabled={isProcessing}
              className="px-5 py-2 rounded-lg text-xs font-semibold bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-[0_0_15px_rgba(245,158,11,0.3)] transition-all flex items-center gap-2 font-display tracking-wider"
            >
              {isProcessing ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Executing...
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4" />
                  Approve & Execute
                </>
              )}
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
