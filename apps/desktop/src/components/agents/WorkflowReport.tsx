import React from 'react';
import { 
  FileText, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  HelpCircle, 
  ListChecks, 
  ArrowRight,
  ShieldCheck
} from 'lucide-react';
import { WorkflowReport as IWorkflowReport } from '../../types';

interface WorkflowReportProps {
  report: IWorkflowReport | null;
  onClose?: () => void;
}

export const WorkflowReport: React.FC<WorkflowReportProps> = ({
  report,
  onClose
}) => {
  if (!report) {
    return (
      <div className="hud-panel p-8 rounded-lg border border-slate-800 bg-slate-900/40 text-center">
        <FileText className="w-8 h-8 text-slate-600 mx-auto mb-2" />
        <div className="text-sm font-mono text-slate-400">NO WORKFLOW REPORT AVAILABLE</div>
        <div className="text-xs text-slate-500 mt-1">
          Execute a workflow to completion to generate a verifiable technical report.
        </div>
      </div>
    );
  }

  const isCompleted = report.status === 'completed';

  return (
    <div className="hud-panel p-5 rounded-lg border border-cyan-800/40 bg-slate-900/70 flex flex-col gap-4">
      {/* Report Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-cyan-400" />
            <h3 className="text-sm font-mono font-bold text-slate-100 uppercase tracking-wider">
              WORKFLOW EXECUTION REPORT: {report.workflow_id}
            </h3>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
              isCompleted
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                : 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
            }`}>
              {report.status}
            </span>
          </div>
          <p className="text-xs text-slate-300 mt-1 italic">
            "{report.objective}"
          </p>
        </div>

        {/* Metrics */}
        <div className="flex items-center gap-2">
          <div className="px-2.5 py-1 rounded bg-slate-950 border border-slate-800 text-center">
            <div className="text-[10px] font-mono text-slate-500 uppercase">Steps</div>
            <div className="text-xs font-mono font-bold text-slate-200">
              {report.completed_steps}/{report.total_steps}
            </div>
          </div>
          <div className="px-2.5 py-1 rounded bg-slate-950 border border-slate-800 text-center">
            <div className="text-[10px] font-mono text-slate-500 uppercase">Duration</div>
            <div className="text-xs font-mono font-bold text-cyan-400">
              {report.duration_seconds.toFixed(1)}s
            </div>
          </div>
        </div>
      </div>

      {/* Verifiable Evidence Summary */}
      <div className="space-y-2">
        <h4 className="text-xs font-mono font-semibold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          Verifiable Execution Evidence ({report.evidence_summary.length})
        </h4>
        <div className="p-3 rounded bg-slate-950/80 border border-slate-800 space-y-1.5">
          {report.evidence_summary.length > 0 ? (
            report.evidence_summary.map((ev, i) => (
              <div key={i} className="flex items-start gap-2 text-xs text-slate-300 font-mono">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                <span>{ev}</span>
              </div>
            ))
          ) : (
            <div className="text-xs text-slate-500 italic">No evidence items recorded.</div>
          )}
        </div>
      </div>

      {/* Technical Findings */}
      <div className="space-y-2">
        <h4 className="text-xs font-mono font-semibold text-cyan-300 uppercase tracking-wider flex items-center gap-1.5">
          <ListChecks className="w-4 h-4 text-cyan-400" />
          Synthesized Technical Findings
        </h4>
        <div className="p-3 rounded bg-slate-950/80 border border-slate-800 text-xs text-slate-200 font-sans leading-relaxed whitespace-pre-wrap">
          {report.technical_findings || 'Workflow completed without additional narrative.'}
        </div>
      </div>

      {/* Unresolved Issues & Next Steps */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* Unresolved Issues */}
        <div className="p-3 rounded bg-slate-950/80 border border-slate-800 space-y-2">
          <h5 className="text-[11px] font-mono font-semibold text-amber-400 uppercase flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            Unresolved Issues ({report.unresolved_issues.length})
          </h5>
          {report.unresolved_issues.length > 0 ? (
            <ul className="text-xs text-slate-300 space-y-1 pl-4 list-disc marker:text-amber-400">
              {report.unresolved_issues.map((issue, i) => (
                <li key={i}>{issue}</li>
              ))}
            </ul>
          ) : (
            <div className="text-xs text-emerald-400 font-mono">None detected</div>
          )}
        </div>

        {/* Recommended Next Steps */}
        <div className="p-3 rounded bg-slate-950/80 border border-slate-800 space-y-2">
          <h5 className="text-[11px] font-mono font-semibold text-cyan-400 uppercase flex items-center gap-1.5">
            <ArrowRight className="w-3.5 h-3.5 text-cyan-400" />
            Recommended Next Steps ({report.next_steps.length})
          </h5>
          {report.next_steps.length > 0 ? (
            <ul className="text-xs text-slate-300 space-y-1 pl-4 list-disc marker:text-cyan-400">
              {report.next_steps.map((nextStep, i) => (
                <li key={i}>{nextStep}</li>
              ))}
            </ul>
          ) : (
            <div className="text-xs text-slate-400 font-mono">Workflow goal achieved</div>
          )}
        </div>
      </div>
    </div>
  );
};
