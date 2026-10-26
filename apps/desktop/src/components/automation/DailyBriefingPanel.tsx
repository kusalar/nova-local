import React, { useState } from 'react';
import { Sun, Play, Volume2, VolumeX, RefreshCw, CheckCircle2, Clock } from 'lucide-react';
import { apiService } from '../../services/api';

export const DailyBriefingPanel: React.FC = () => {
  const [briefingText, setBriefingText] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [speakAloud, setSpeakAloud] = useState(false);

  const handleGenerateBriefing = async () => {
    setLoading(true);
    try {
      // Find or create daily briefing rule and trigger it
      const rules = await apiService.listAutomations();
      let briefingRule = rules.find(r => r.action_type === 'DAILY_BRIEFING');
      if (!briefingRule) {
        briefingRule = await apiService.createAutomation({
          name: 'Manual Daily Briefing',
          action_type: 'DAILY_BRIEFING',
          trigger_config: { trigger_type: 'MANUAL' },
          action_payload: { speak_aloud: speakAloud }
        });
      }

      const res = await apiService.runAutomation(briefingRule.id);
      if (res.result?.content) {
        setBriefingText(res.result.content);
      } else {
        setBriefingText(res.result?.summary || 'Briefing compiled successfully.');
      }
    } catch (e: any) {
      setBriefingText(`Error generating briefing: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4 p-5 bg-slate-900/60 rounded-xl border border-cyan-500/20 shadow-lg shadow-cyan-950/20">
      <div className="flex items-center justify-between pb-3 border-b border-cyan-500/20">
        <div>
          <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <Sun className="w-4 h-4 text-amber-400" />
            Daily Executive Briefing Agent
          </h3>
          <p className="text-xs text-slate-400 font-mono">
            Verifiable synthesis of project tasks, deadlines, workflow outcomes, and system telemetry.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            type="button"
            onClick={() => setSpeakAloud(!speakAloud)}
            title={speakAloud ? 'TTS Spoken Audio Enabled' : 'TTS Audio Muted'}
            className={`p-1.5 rounded transition-colors ${
              speakAloud ? 'text-cyan-400 bg-cyan-950/60 border border-cyan-500/40' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            {speakAloud ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
          </button>

          <button
            onClick={handleGenerateBriefing}
            disabled={loading}
            className="px-4 py-1.5 text-xs font-mono uppercase bg-cyan-500 text-slate-950 font-bold rounded hover:bg-cyan-400 transition-colors flex items-center gap-1.5 shadow-md shadow-cyan-500/20 disabled:opacity-50"
          >
            {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
            {loading ? 'Synthesizing...' : 'Compile Briefing Now'}
          </button>
        </div>
      </div>

      {/* Briefing Content Display */}
      {briefingText ? (
        <div className="p-4 rounded-lg bg-slate-950/80 border border-slate-800 font-mono text-xs leading-relaxed text-slate-200 whitespace-pre-wrap">
          {briefingText}
        </div>
      ) : (
        <div className="text-center py-10 text-slate-500 font-mono text-xs border border-dashed border-slate-800 rounded-lg">
          Click "Compile Briefing Now" to generate an on-demand executive briefing from your persistent memory and system telemetry.
        </div>
      )}
    </div>
  );
};
