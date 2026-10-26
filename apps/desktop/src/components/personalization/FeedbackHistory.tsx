import React, { useState, useEffect } from 'react';
import { 
  History, 
  ThumbsUp, 
  ThumbsDown, 
  Edit3, 
  AlertOctagon, 
  Trash2, 
  RefreshCw, 
  Info,
  Calendar
} from 'lucide-react';
import { FeedbackRecord, FeedbackType } from '../../types';
import { apiService } from '../../services/api';

const FEEDBACK_ICONS: Record<FeedbackType, React.ElementType> = {
  useful: ThumbsUp,
  dismiss_permanent: ThumbsDown,
  preference_correction: Edit3,
  association_incorrect: AlertOctagon,
  forget_preference: Trash2,
};

const FEEDBACK_COLORS: Record<FeedbackType, string> = {
  useful: 'text-emerald-400 bg-emerald-950/60 border-emerald-500/40',
  dismiss_permanent: 'text-slate-300 bg-slate-800 border-slate-600',
  preference_correction: 'text-blue-400 bg-blue-950/60 border-blue-500/40',
  association_incorrect: 'text-amber-400 bg-amber-950/60 border-amber-500/40',
  forget_preference: 'text-rose-400 bg-rose-950/60 border-rose-500/40',
};

export const FeedbackHistory: React.FC = () => {
  const [history, setHistory] = useState<FeedbackRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadHistory = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const data = await apiService.getFeedbackHistory(50);
      setHistory(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load feedback history');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="p-3.5 rounded-lg bg-nova-surface/60 border border-nova-border/70 backdrop-blur-md flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-mono text-nova-cyan">
          <History className="w-4 h-4" />
          <span>FEEDBACK & CORRECTION AUDIT TRAIL</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono text-slate-400">
            {history.length} logged feedback records
          </span>
          <button
            onClick={loadHistory}
            className="p-1.5 rounded text-slate-400 hover:text-nova-cyan hover:bg-nova-surface border border-transparent hover:border-nova-border transition-all"
            title="Refresh history"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 rounded bg-red-950/60 border border-red-500/40 text-red-200 text-xs font-mono">
          {errorMsg}
        </div>
      )}

      {history.length === 0 ? (
        <div className="p-8 text-center border border-dashed border-nova-border/50 rounded-lg text-slate-500 font-mono text-xs">
          <Info className="w-6 h-6 mx-auto mb-2 text-slate-600" />
          No feedback records recorded yet. As you interact with recommendations or correct NOVA, audit entries will appear here.
        </div>
      ) : (
        <div className="space-y-2.5">
          {history.map((record) => {
            const Icon = FEEDBACK_ICONS[record.feedback_type] || History;
            const colorClass = FEEDBACK_COLORS[record.feedback_type] || 'text-slate-300 bg-slate-800 border-slate-600';

            return (
              <div
                key={record.id}
                className="p-3.5 rounded-lg bg-nova-surface/40 hover:bg-nova-surface/60 border border-nova-border/60 transition-all flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs font-mono"
              >
                <div className="flex items-start gap-3">
                  <span className={`p-1.5 rounded border ${colorClass} mt-0.5`}>
                    <Icon className="w-3.5 h-3.5" />
                  </span>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-200 uppercase tracking-wide">
                        {record.feedback_type.replace('_', ' ')}
                      </span>
                      {record.target_id && (
                        <span className="text-[10px] text-slate-500">
                          Target: {record.target_id}
                        </span>
                      )}
                    </div>
                    {record.user_correction && (
                      <p className="text-slate-300 mt-1 text-[11px] bg-nova-dark/60 p-1.5 rounded border border-nova-border/40">
                        "{record.user_correction}"
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-3 text-[10px] text-slate-500 self-end md:self-center">
                  <div className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    <span>{new Date(record.created_at).toLocaleString()}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
