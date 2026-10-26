import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Lock, 
  EyeOff, 
  Database, 
  Trash2, 
  AlertTriangle, 
  CheckCircle, 
  Cpu, 
  RefreshCw,
  Sliders
} from 'lucide-react';
import { PersonalizationPrivacySettings } from '../../types';
import { apiService } from '../../services/api';

export const PersonalizationPrivacy: React.FC = () => {
  const [settings, setSettings] = useState<PersonalizationPrivacySettings>({
    enabled: true,
    adaptive_analysis_enabled: true,
    recommendations_enabled: true,
    store_inferred_preferences: true,
    active_window_awareness_enabled: true,
    voice_personalization_enabled: true
  });
  const [loading, setLoading] = useState<boolean>(true);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Clear confirmation modal state
  const [showClearModal, setShowClearModal] = useState<boolean>(false);
  const [clearExplicit, setClearExplicit] = useState<boolean>(false);

  const loadSettings = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const data = await apiService.getPersonalizationPrivacySettings();
      setSettings(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load privacy settings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleToggle = async (key: keyof PersonalizationPrivacySettings, currentValue: boolean) => {
    try {
      const updated = { [key]: !currentValue };
      const res = await apiService.updatePersonalizationPrivacySettings(updated);
      setSettings(res);
      setSuccessMsg(`Setting '${key.replace(/_/g, ' ')}' updated.`);
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to update setting');
    }
  };

  const handleClearData = async () => {
    try {
      await apiService.clearPersonalizationData(clearExplicit);
      setShowClearModal(false);
      setSuccessMsg(clearExplicit ? 'All personalization data and explicit preferences cleared.' : 'Inferred personalization data cleared.');
      setTimeout(() => setSuccessMsg(null), 4000);
      loadSettings();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to clear data');
    }
  };

  return (
    <div className="space-y-4">
      {/* Privacy Guarantees Banner */}
      <div className="p-4 rounded-lg bg-emerald-950/20 border border-emerald-500/40 space-y-2">
        <div className="flex items-center gap-2 text-emerald-400 font-mono text-xs font-semibold uppercase tracking-wider">
          <ShieldCheck className="w-4 h-4" />
          <span>NOVA Zero-Cloud Privacy & Local-Only Guarantees</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 text-[11px] font-mono text-emerald-200/80">
          <div className="flex items-start gap-2">
            <Lock className="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
            <span>100% Offline & Local SQLite storage (`nova_memory.db`)</span>
          </div>
          <div className="flex items-start gap-2">
            <EyeOff className="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
            <span>No background keystroke logging or clipboard monitoring</span>
          </div>
          <div className="flex items-start gap-2">
            <Cpu className="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
            <span>Zero cloud analytics, telemetry or third-party profiling</span>
          </div>
          <div className="flex items-start gap-2">
            <Sliders className="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
            <span>Explicit user directives always override inferred data</span>
          </div>
        </div>
      </div>

      {successMsg && (
        <div className="p-3 rounded bg-emerald-950/60 border border-emerald-500/40 text-emerald-200 text-xs font-mono flex items-center gap-2">
          <CheckCircle className="w-3.5 h-3.5" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-3 rounded bg-red-950/60 border border-red-500/40 text-red-200 text-xs font-mono">
          {errorMsg}
        </div>
      )}

      {/* Control Toggles */}
      <div className="p-4 rounded-lg bg-nova-surface/40 border border-nova-border/70 space-y-3">
        <div className="flex items-center justify-between border-b border-nova-border/50 pb-2">
          <h3 className="text-xs font-mono text-nova-cyan uppercase tracking-wider">
            Adaptive Intelligence Controls
          </h3>
          <button
            onClick={loadSettings}
            className="p-1 rounded text-slate-400 hover:text-nova-cyan"
            title="Reload settings"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        <div className="space-y-3">
          {/* Master Toggle */}
          <div className="flex items-center justify-between p-3 rounded bg-nova-dark/80 border border-nova-border/60">
            <div>
              <span className="font-mono text-xs font-semibold text-slate-200 block">
                Master Personalization Engine
              </span>
              <span className="text-[11px] font-mono text-slate-400">
                Globally enable or disable all personalization, recommendation, and adaptive interaction layers.
              </span>
            </div>
            <button
              onClick={() => handleToggle('enabled', settings.enabled)}
              className={`px-3 py-1 rounded font-mono text-xs font-semibold tracking-wider transition-all ${
                settings.enabled
                  ? 'bg-emerald-950/80 border border-emerald-500/50 text-emerald-300'
                  : 'bg-slate-800 border border-slate-600 text-slate-400'
              }`}
            >
              {settings.enabled ? 'ENABLED' : 'DISABLED'}
            </button>
          </div>

          {/* Adaptive Analysis */}
          <div className="flex items-center justify-between p-3 rounded bg-nova-dark/80 border border-nova-border/60">
            <div>
              <span className="font-mono text-xs font-semibold text-slate-200 block">
                Adaptive Turn Analysis
              </span>
              <span className="text-[11px] font-mono text-slate-400">
                Analyze permitted conversation history to infer interaction preferences.
              </span>
            </div>
            <button
              onClick={() => handleToggle('adaptive_analysis_enabled', settings.adaptive_analysis_enabled)}
              disabled={!settings.enabled}
              className={`px-3 py-1 rounded font-mono text-xs font-semibold tracking-wider transition-all disabled:opacity-40 ${
                settings.adaptive_analysis_enabled
                  ? 'bg-teal-950/80 border border-teal-500/50 text-teal-300'
                  : 'bg-slate-800 border border-slate-600 text-slate-400'
              }`}
            >
              {settings.adaptive_analysis_enabled ? 'ON' : 'OFF'}
            </button>
          </div>

          {/* Recommendations */}
          <div className="flex items-center justify-between p-3 rounded bg-nova-dark/80 border border-nova-border/60">
            <div>
              <span className="font-mono text-xs font-semibold text-slate-200 block">
                Intelligent Recommendations
              </span>
              <span className="text-[11px] font-mono text-slate-400">
                Generate evidence-backed suggestions for failed workflows, unfinished tasks, and project checks.
              </span>
            </div>
            <button
              onClick={() => handleToggle('recommendations_enabled', settings.recommendations_enabled)}
              disabled={!settings.enabled}
              className={`px-3 py-1 rounded font-mono text-xs font-semibold tracking-wider transition-all disabled:opacity-40 ${
                settings.recommendations_enabled
                  ? 'bg-teal-950/80 border border-teal-500/50 text-teal-300'
                  : 'bg-slate-800 border border-slate-600 text-slate-400'
              }`}
            >
              {settings.recommendations_enabled ? 'ON' : 'OFF'}
            </button>
          </div>

          {/* Store Inferred Preferences */}
          <div className="flex items-center justify-between p-3 rounded bg-nova-dark/80 border border-nova-border/60">
            <div>
              <span className="font-mono text-xs font-semibold text-slate-200 block">
                Store Inferred Preferences
              </span>
              <span className="text-[11px] font-mono text-slate-400">
                Allow NOVA to save inferred communication preferences to SQLite (explicit directives always override).
              </span>
            </div>
            <button
              onClick={() => handleToggle('store_inferred_preferences', settings.store_inferred_preferences)}
              disabled={!settings.enabled}
              className={`px-3 py-1 rounded font-mono text-xs font-semibold tracking-wider transition-all disabled:opacity-40 ${
                settings.store_inferred_preferences
                  ? 'bg-teal-950/80 border border-teal-500/50 text-teal-300'
                  : 'bg-slate-800 border border-slate-600 text-slate-400'
              }`}
            >
              {settings.store_inferred_preferences ? 'ON' : 'OFF'}
            </button>
          </div>

          {/* Active Window Awareness */}
          <div className="flex items-center justify-between p-3 rounded bg-nova-dark/80 border border-nova-border/60">
            <div>
              <span className="font-mono text-xs font-semibold text-slate-200 block">
                Active Window Context Awareness
              </span>
              <span className="text-[11px] font-mono text-slate-400">
                Use foreground application window title and process in context resolution (from v0.5).
              </span>
            </div>
            <button
              onClick={() => handleToggle('active_window_awareness_enabled', settings.active_window_awareness_enabled)}
              disabled={!settings.enabled}
              className={`px-3 py-1 rounded font-mono text-xs font-semibold tracking-wider transition-all disabled:opacity-40 ${
                settings.active_window_awareness_enabled
                  ? 'bg-teal-950/80 border border-teal-500/50 text-teal-300'
                  : 'bg-slate-800 border border-slate-600 text-slate-400'
              }`}
            >
              {settings.active_window_awareness_enabled ? 'ON' : 'OFF'}
            </button>
          </div>

          {/* Voice Personalization */}
          <div className="flex items-center justify-between p-3 rounded bg-nova-dark/80 border border-nova-border/60">
            <div>
              <span className="font-mono text-xs font-semibold text-slate-200 block">
                Voice Command Integration
              </span>
              <span className="text-[11px] font-mono text-slate-400">
                Permit remembering preferences, querying project context, and toggling personalization via voice.
              </span>
            </div>
            <button
              onClick={() => handleToggle('voice_personalization_enabled', settings.voice_personalization_enabled)}
              disabled={!settings.enabled}
              className={`px-3 py-1 rounded font-mono text-xs font-semibold tracking-wider transition-all disabled:opacity-40 ${
                settings.voice_personalization_enabled
                  ? 'bg-teal-950/80 border border-teal-500/50 text-teal-300'
                  : 'bg-slate-800 border border-slate-600 text-slate-400'
              }`}
            >
              {settings.voice_personalization_enabled ? 'ON' : 'OFF'}
            </button>
          </div>
        </div>
      </div>

      {/* Data Wipe Section */}
      <div className="p-4 rounded-lg bg-red-950/20 border border-red-500/40 space-y-3">
        <div className="flex items-center gap-2 text-red-400 font-mono text-xs font-semibold uppercase tracking-wider">
          <Trash2 className="w-4 h-4" />
          <span>Data Sanitization & Data Removal</span>
        </div>
        <p className="text-[11px] font-mono text-slate-400">
          You can wipe inferred patterns and recommendations at any time. You may optionally retain your explicit preferences.
        </p>

        <button
          onClick={() => setShowClearModal(true)}
          className="px-3.5 py-1.5 rounded bg-red-950/70 border border-red-500/50 text-red-300 hover:bg-red-900/80 text-xs font-mono tracking-wider transition-all flex items-center gap-1.5"
        >
          <Trash2 className="w-3.5 h-3.5" />
          <span>CLEAR PERSONALIZATION DATA</span>
        </button>
      </div>

      {/* Confirmation Modal */}
      {showClearModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md p-5 rounded-lg bg-nova-dark border border-red-500/60 shadow-2xl space-y-4">
            <div className="flex items-center gap-2 text-red-400 font-mono text-sm font-bold">
              <AlertTriangle className="w-5 h-5" />
              <span>Confirm Personalization Data Wipe</span>
            </div>

            <p className="text-xs font-mono text-slate-300">
              This will clear recommendation history, interaction logs, and feedback.
            </p>

            <label className="flex items-center gap-2 text-xs font-mono text-slate-200 cursor-pointer p-2.5 rounded bg-nova-surface border border-nova-border">
              <input
                type="checkbox"
                checked={clearExplicit}
                onChange={(e) => setClearExplicit(e.target.checked)}
                className="rounded bg-nova-dark border-red-500 text-red-500 focus:ring-0"
              />
              <span>Also delete explicit preferences (Full Factory Reset)</span>
            </label>

            <div className="flex justify-end gap-2 pt-2 border-t border-nova-border/60">
              <button
                onClick={() => setShowClearModal(false)}
                className="px-3 py-1.5 rounded text-xs font-mono text-slate-400 hover:text-slate-200"
              >
                Cancel
              </button>
              <button
                onClick={handleClearData}
                className="px-4 py-1.5 rounded bg-red-600 hover:bg-red-500 text-white font-mono text-xs font-semibold tracking-wider transition-all"
              >
                WIPE DATA NOW
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
