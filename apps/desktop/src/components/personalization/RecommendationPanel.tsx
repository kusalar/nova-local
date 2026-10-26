import React, { useState, useEffect } from 'react';
import { 
  Lightbulb, 
  ThumbsUp, 
  ThumbsDown, 
  CheckCircle, 
  XCircle, 
  RefreshCw, 
  FolderGit2, 
  ArrowRight, 
  ShieldAlert, 
  Sparkles,
  MessageSquarePlus,
  AlertCircle
} from 'lucide-react';
import { Recommendation, FeedbackType } from '../../types';
import { apiService } from '../../services/api';

export const RecommendationPanel: React.FC = () => {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [includeDismissed, setIncludeDismissed] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Correction feedback modal
  const [correctionTarget, setCorrectionTarget] = useState<string | null>(null);
  const [correctionText, setCorrectionText] = useState<string>('');

  const loadRecommendations = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const data = await apiService.getRecommendations(20, includeDismissed);
      setRecommendations(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load recommendations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecommendations();
  }, [includeDismissed]);

  const handleFeedback = async (id: string, type: FeedbackType, correction?: string) => {
    try {
      await apiService.submitRecommendationFeedback(id, {
        feedback_type: type,
        user_correction: correction
      });
      setSuccessMsg(`Feedback registered (${type.replace('_', ' ')})`);
      setTimeout(() => setSuccessMsg(null), 3000);
      setCorrectionTarget(null);
      setCorrectionText('');
      loadRecommendations();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to submit feedback');
    }
  };

  const handleRefresh = async () => {
    try {
      setLoading(true);
      await apiService.refreshPersonalization();
      await loadRecommendations();
      setSuccessMsg('Recommendations refreshed with latest project intelligence');
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to refresh recommendations');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Banner and Controls */}
      <div className="p-3.5 rounded-lg bg-nova-surface/60 border border-nova-border/70 backdrop-blur-md flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-nova-cyan" />
          <span className="font-mono text-xs text-slate-200">
            EVIDENCE-BACKED ADAPTIVE RECOMMENDATIONS
          </span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950/80 border border-amber-500/40 text-amber-300 flex items-center gap-1">
            <ShieldAlert className="w-3 h-3" />
            NO AUTONOMOUS EXECUTION
          </span>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={includeDismissed}
              onChange={(e) => setIncludeDismissed(e.target.checked)}
              className="rounded bg-nova-dark border-nova-border text-nova-cyan focus:ring-0"
            />
            <span className="font-mono text-[11px]">Include Dismissed</span>
          </label>

          <button
            onClick={handleRefresh}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-nova-cyan/20 border border-nova-cyan/50 text-nova-cyan hover:bg-nova-cyan/30 text-xs font-mono tracking-wider transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>RE-ANALYZE</span>
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 rounded bg-red-950/60 border border-red-500/40 text-red-200 text-xs font-mono">
          {errorMsg}
        </div>
      )}

      {successMsg && (
        <div className="p-3 rounded bg-emerald-950/60 border border-emerald-500/40 text-emerald-200 text-xs font-mono flex items-center gap-2">
          <CheckCircle className="w-3.5 h-3.5" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Correction Modal */}
      {correctionTarget && (
        <div className="p-4 rounded-lg bg-nova-dark/95 border border-nova-cyan/40 shadow-xl space-y-3">
          <div className="flex items-center justify-between border-b border-nova-border/60 pb-2">
            <h4 className="text-xs font-mono text-nova-cyan uppercase tracking-wider flex items-center gap-2">
              <MessageSquarePlus className="w-3.5 h-3.5" />
              Provide User Correction
            </h4>
            <button
              onClick={() => setCorrectionTarget(null)}
              className="text-slate-400 hover:text-slate-200"
            >
              <XCircle className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs font-mono text-slate-400">
            Tell NOVA why this recommendation or association was incorrect. NOVA will store your explicit correction and avoid repeating it.
          </p>
          <textarea
            value={correctionText}
            onChange={(e) => setCorrectionText(e.target.value)}
            placeholder="e.g. This project doesn't use Docker; or this task was moved to another sprint"
            rows={3}
            className="w-full bg-nova-surface border border-nova-border rounded px-3 py-2 text-slate-100 font-mono text-xs focus:outline-none focus:border-nova-cyan"
          />
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setCorrectionTarget(null)}
              className="px-3 py-1 rounded text-xs font-mono text-slate-400 hover:text-slate-200"
            >
              Cancel
            </button>
            <button
              onClick={() => handleFeedback(correctionTarget, 'preference_correction', correctionText)}
              className="px-4 py-1.5 rounded bg-nova-cyan text-nova-dark font-mono font-semibold text-xs tracking-wider hover:bg-nova-teal transition-all"
            >
              SUBMIT CORRECTION
            </button>
          </div>
        </div>
      )}

      {/* Recommendation List */}
      {recommendations.length === 0 ? (
        <div className="p-8 text-center border border-dashed border-nova-border/50 rounded-lg text-slate-500 font-mono text-xs">
          <Lightbulb className="w-6 h-6 mx-auto mb-2 text-slate-600" />
          No recommendations at this time. NOVA continuously checks workflow outcomes, project tasks, and scheduled routines.
        </div>
      ) : (
        <div className="space-y-3">
          {recommendations.map((rec) => {
            const isDismissed = rec.status === 'dismissed';

            return (
              <div
                key={rec.id}
                className={`p-4 rounded-lg border transition-all ${
                  isDismissed
                    ? 'bg-nova-surface/20 border-nova-border/30 opacity-60'
                    : 'bg-nova-surface/40 hover:bg-nova-surface/70 border-nova-border/70 hover:border-nova-cyan/40'
                }`}
              >
                <div className="flex flex-wrap items-start justify-between gap-3 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="p-1 rounded bg-nova-cyan/10 border border-nova-cyan/30 text-nova-cyan">
                      <Lightbulb className="w-4 h-4" />
                    </span>
                    <h3 className="font-mono text-sm font-semibold text-slate-100">
                      {rec.text}
                    </h3>
                  </div>

                  <div className="flex items-center gap-2">
                    {rec.related_project && (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-nova-dark/80 border border-nova-border text-nova-cyan flex items-center gap-1">
                        <FolderGit2 className="w-3 h-3" />
                        {rec.related_project}
                      </span>
                    )}
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-teal-950/60 border border-teal-500/30 text-teal-300">
                      Confidence: {(rec.confidence * 100).toFixed(0)}%
                    </span>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded uppercase ${
                      isDismissed
                        ? 'bg-slate-800 text-slate-400'
                        : 'bg-blue-950/60 text-blue-300 border border-blue-500/30'
                    }`}>
                      {rec.status}
                    </span>
                  </div>
                </div>

                {/* Reason */}
                <div className="text-xs font-mono text-slate-300 mb-2">
                  <span className="text-slate-500">Reason: </span>
                  {rec.reason}
                </div>

                {/* Supporting Evidence */}
                {rec.evidence && rec.evidence.length > 0 && (
                  <div className="mb-3 p-2.5 rounded bg-nova-dark/80 border border-nova-border/50">
                    <span className="text-[10px] font-mono text-nova-cyan uppercase block mb-1">
                      Supporting Evidence
                    </span>
                    <ul className="space-y-1">
                      {rec.evidence.map((ev, i) => (
                        <li key={i} className="text-[11px] font-mono text-slate-300 flex items-start gap-1.5">
                          <span className="text-nova-teal mt-0.5">•</span>
                          <span>{ev}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Suggested Action */}
                {rec.suggested_action && (
                  <div className="mb-3 flex items-center gap-2 text-xs font-mono text-nova-teal">
                    <ArrowRight className="w-3.5 h-3.5 flex-shrink-0" />
                    <span className="text-slate-400">Suggested Action:</span>
                    <span className="font-semibold text-slate-200">{rec.suggested_action}</span>
                  </div>
                )}

                {/* Feedback Action Buttons */}
                <div className="pt-2 border-t border-nova-border/40 flex flex-wrap items-center justify-between gap-2">
                  <span className="text-[10px] font-mono text-slate-500">
                    Created: {new Date(rec.created_at).toLocaleString()}
                  </span>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleFeedback(rec.id, 'useful')}
                      className="flex items-center gap-1 px-2.5 py-1 rounded bg-emerald-950/60 hover:bg-emerald-900/80 border border-emerald-500/40 text-emerald-300 text-xs font-mono transition-colors"
                      title="Mark recommendation as useful"
                    >
                      <ThumbsUp className="w-3 h-3" />
                      <span>Useful</span>
                    </button>

                    <button
                      onClick={() => handleFeedback(rec.id, 'dismiss_permanent')}
                      className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-300 text-xs font-mono transition-colors"
                      title="Dismiss and don't suggest this pattern again"
                    >
                      <ThumbsDown className="w-3 h-3" />
                      <span>Don't Suggest Again</span>
                    </button>

                    <button
                      onClick={() => {
                        setCorrectionTarget(rec.id);
                        setCorrectionText('');
                      }}
                      className="flex items-center gap-1 px-2.5 py-1 rounded bg-nova-surface hover:bg-nova-surface/90 border border-nova-border text-nova-cyan text-xs font-mono transition-colors"
                      title="Provide correction"
                    >
                      <MessageSquarePlus className="w-3 h-3" />
                      <span>Correct</span>
                    </button>
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
