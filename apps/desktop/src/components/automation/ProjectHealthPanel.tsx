import React, { useState } from 'react';
import { Activity, ShieldCheck, Play, RefreshCw, AlertTriangle, CheckCircle } from 'lucide-react';
import { apiService } from '../../services/api';

export const ProjectHealthPanel: React.FC = () => {
  const [workspace, setWorkspace] = useState('D:\\Nova');
  const [report, setReport] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleRunHealthCheck = async () => {
    setLoading(true);
    try {
      const rules = await apiService.listAutomations();
      let healthRule = rules.find(r => r.action_type === 'PROJECT_HEALTH');
      if (!healthRule) {
        healthRule = await apiService.createAutomation({
          name: 'On-Demand Health Check',
          action_type: 'PROJECT_HEALTH',
          trigger_config: { trigger_type: 'MANUAL', project_id: 'nova' },
          action_payload: {
            workspace_path: workspace,
            run_tests: false,
          }
        });
      }

      const res = await apiService.runAutomation(healthRule.id);
      if (res.result?.report) {
        setReport(res.result.report);
        setStatus(res.result.status || 'HEALTHY');
      } else {
        setReport(res.result?.summary || 'Project check complete.');
        setStatus('HEALTHY');
      }
    } catch (e: any) {
      setReport(`Health check failed: ${e.message}`);
      setStatus('WARNING');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4 p-5 bg-slate-900/60 rounded-xl border border-cyan-500/20 shadow-lg shadow-cyan-950/20">
      <div className="flex items-center justify-between pb-3 border-b border-cyan-500/20">
        <div>
          <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            Project Health Monitor
          </h3>
          <p className="text-xs text-slate-400 font-mono">
            Evidence-based inspection of git status, project integrity, and approved test runners.
          </p>
        </div>

        <button
          onClick={handleRunHealthCheck}
          disabled={loading}
          className="px-4 py-1.5 text-xs font-mono uppercase bg-cyan-500 text-slate-950 font-bold rounded hover:bg-cyan-400 transition-colors flex items-center gap-1.5 shadow-md shadow-cyan-500/20 disabled:opacity-50"
        >
          {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
          {loading ? 'Inspecting...' : 'Run Health Check'}
        </button>
      </div>

      {/* Target Workspace input */}
      <div className="flex items-center space-x-3">
        <label className="text-xs font-mono text-slate-300">Target Workspace:</label>
        <input
          type="text"
          value={workspace}
          onChange={e => setWorkspace(e.target.value)}
          className="flex-1 bg-slate-950 border border-slate-700 rounded px-3 py-1 text-xs text-cyan-300 font-mono focus:border-cyan-400 focus:outline-none"
        />
      </div>

      {/* Health Report Display */}
      {report ? (
        <div className="space-y-2">
          <div className="flex items-center space-x-2">
            {status === 'HEALTHY' ? (
              <span className="flex items-center text-xs font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-500/30 px-2 py-0.5 rounded">
                <CheckCircle className="w-3.5 h-3.5 mr-1" /> ALL SYSTEMS HEALTHY
              </span>
            ) : (
              <span className="flex items-center text-xs font-mono text-amber-400 bg-amber-950/40 border border-amber-500/30 px-2 py-0.5 rounded">
                <AlertTriangle className="w-3.5 h-3.5 mr-1" /> WARNING / ATTENTION NEEDED
              </span>
            )}
          </div>
          <div className="p-4 rounded-lg bg-slate-950/80 border border-slate-800 font-mono text-xs leading-relaxed text-slate-200 whitespace-pre-wrap">
            {report}
          </div>
        </div>
      ) : (
        <div className="text-center py-8 text-slate-500 font-mono text-xs border border-dashed border-slate-800 rounded-lg">
          No recent health check report. Run a health check to verify repository and test health.
        </div>
      )}
    </div>
  );
};
