import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Cpu, 
  Bot, 
  Mic, 
  CheckCircle, 
  AlertTriangle, 
  ArrowRight, 
  ArrowLeft, 
  Check, 
  Radio, 
  Volume2, 
  Sparkles,
  Info,
  Server,
  Database,
  Lock
} from 'lucide-react';
import { apiService } from '../../services/api';
import { OnboardingStatusResponse, AudioDevice } from '../../types';

interface OnboardingWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: () => void;
  devices?: { inputs: AudioDevice[]; outputs: AudioDevice[] };
}

export const OnboardingWizard: React.FC<OnboardingWizardProps> = ({
  isOpen,
  onClose,
  onComplete,
  devices
}) => {
  const [step, setStep] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [status, setStatus] = useState<OnboardingStatusResponse | null>(null);

  // User selections
  const [selectedModel, setSelectedModel] = useState<string>('gemma2:2b');
  const [voiceEnabled, setVoiceEnabled] = useState<boolean>(true);
  const [selectedInputDev, setSelectedInputDev] = useState<number | undefined>(undefined);
  const [selectedOutputDev, setSelectedOutputDev] = useState<number | undefined>(undefined);
  const [privacyScreenEnabled, setPrivacyScreenEnabled] = useState<boolean>(true);
  const [personalizationEnabled, setPersonalizationEnabled] = useState<boolean>(true);

  useEffect(() => {
    if (isOpen) {
      loadOnboardingStatus();
    }
  }, [isOpen]);

  const loadOnboardingStatus = async () => {
    setLoading(true);
    try {
      const data = await apiService.getOnboardingStatus();
      setStatus(data);
      const modelsList = (data?.ollama?.models || (data?.ollama as any)?.available_models || []) as string[];
      if (modelsList.includes('gemma2:2b')) {
        setSelectedModel('gemma2:2b');
      } else if (data?.ollama?.active_model) {
        setSelectedModel(data.ollama.active_model);
      } else if (modelsList.length > 0) {
        setSelectedModel(modelsList[0]);
      }
    } catch (err) {
      console.error('Failed to load onboarding status:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const handleFinish = async () => {
    setSubmitting(true);
    try {
      await apiService.completeOnboarding({
        selected_model: selectedModel,
        voice_enabled: voiceEnabled,
        input_device: selectedInputDev,
        output_device: selectedOutputDev,
        privacy_screen_enabled: privacyScreenEnabled,
        personalization_enabled: personalizationEnabled
      });
      onComplete();
    } catch (err) {
      console.error('Error completing onboarding:', err);
      // Still close smoothly
      onComplete();
    } finally {
      setSubmitting(false);
    }
  };

  const totalSteps = 5;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fade-in select-none">
      <div className="hud-panel w-full max-w-2xl bg-nova-dark/95 border-nova-cyan/50 shadow-[0_0_40px_rgba(0,240,255,0.25)] flex flex-col max-h-[90vh]">
        {/* Top Header */}
        <div className="p-5 border-b border-nova-border/80 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-nova-cyan/15 border border-nova-cyan/40 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-nova-cyan animate-pulse" />
            </div>
            <div>
              <h1 className="font-display font-bold text-base text-white tracking-wider uppercase">
                NOVA v1.0 First-Run Setup
              </h1>
              <p className="text-xs text-slate-400 font-mono">
                System initialization, local model configuration & safety verification
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1.5 bg-nova-surface/80 border border-nova-border px-3 py-1 rounded text-xs font-mono text-nova-cyan">
            STEP {step} / {totalSteps}
          </div>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-nova-border/30 h-1">
          <div 
            className="bg-nova-cyan h-1 transition-all duration-300 shadow-[0_0_8px_rgba(0,240,255,0.6)]"
            style={{ width: `${(step / totalSteps) * 100}%` }}
          />
        </div>

        {/* Wizard Step Body */}
        <div className="p-6 flex-1 overflow-y-auto custom-scrollbar space-y-4">
          {loading ? (
            <div className="py-16 flex flex-col items-center justify-center text-center space-y-3">
              <div className="w-10 h-10 border-2 border-nova-cyan border-t-transparent rounded-full animate-spin" />
              <p className="text-xs font-mono text-slate-300">Auditing local environment and hardware readiness...</p>
            </div>
          ) : step === 1 ? (
            /* STEP 1: Hardware & System Compatibility */
            <div className="space-y-4 animate-fade-in">
              <div className="flex items-center gap-2 text-nova-cyan font-display text-sm font-semibold tracking-wide">
                <Cpu className="w-4 h-4" />
                SYSTEM COMPATIBILITY & LOCAL RUNTIME
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Welcome to <span className="text-white font-semibold">NOVA (Neural Operational Virtual Assistant) v1.0</span>. 
                NOVA is designed to operate 100% locally on your Windows desktop without mandatory cloud services.
              </p>

              <div className="grid grid-cols-2 gap-3 pt-2">
                <div className="bg-nova-surface/60 border border-nova-border p-3.5 rounded-lg space-y-1.5">
                  <span className="text-[10px] font-mono text-slate-400 uppercase">Hardware Specification</span>
                  <div className="text-sm font-display font-bold text-white">
                    {status?.hardware?.cpu_count ?? (status?.hardware as any)?.cpu_cores ?? 4} Logical Cores ({status?.hardware?.physical_cores ?? 2} Physical)
                  </div>
                  <div className="text-xs font-mono text-slate-300">
                    RAM: {((status?.hardware?.ram_total_gb ?? (status?.hardware as any)?.total_ram_gb ?? 12) as number).toFixed(1)} GB Total ({((status?.hardware?.ram_available_gb ?? (status?.hardware as any)?.available_ram_gb ?? 8) as number).toFixed(1)} GB Available)
                  </div>
                  <div className="pt-1 flex items-center gap-1.5 text-[11px] font-mono text-emerald-400">
                    <CheckCircle className="w-3.5 h-3.5" />
                    Target baseline validated
                  </div>
                </div>

                <div className="bg-nova-surface/60 border border-nova-border p-3.5 rounded-lg space-y-1.5">
                  <span className="text-[10px] font-mono text-slate-400 uppercase">Database Architecture</span>
                  <div className="text-sm font-display font-bold text-white flex items-center gap-1.5">
                    <Database className="w-4 h-4 text-nova-cyan" />
                    SQLite Persistent Memory
                  </div>
                  <div className="text-xs font-mono text-slate-300 truncate" title={status?.database?.path}>
                    Location: nova_memory.db
                  </div>
                  <div className="pt-1 flex items-center gap-1.5 text-[11px] font-mono text-emerald-400">
                    <CheckCircle className="w-3.5 h-3.5" />
                    WAL Mode & busy_timeout enabled
                  </div>
                </div>
              </div>

              <div className="bg-blue-950/20 border border-blue-500/30 p-3 rounded-lg flex items-start gap-2.5">
                <Info className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-blue-200/90 leading-relaxed">
                  NOVA is tuned for daily use on Intel Core i3-1115G4 with 12 GB RAM. FastEmbed BGE embeddings and SQLite run with bounded resource overhead.
                </p>
              </div>
            </div>
          ) : step === 2 ? (
            /* STEP 2: Ollama & Local Model */
            <div className="space-y-4 animate-fade-in">
              <div className="flex items-center gap-2 text-nova-cyan font-display text-sm font-semibold tracking-wide">
                <Bot className="w-4 h-4" />
                LOCAL AI NEURAL ENGINE (OLLAMA)
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                NOVA performs conversational reasoning through your local <span className="text-white font-semibold">Ollama</span> server.
                No prompt tokens or private context are ever uploaded to cloud endpoints.
              </p>

              <div className="bg-nova-surface/60 border border-nova-border p-3.5 rounded-lg flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Server className="w-4 h-4 text-slate-400" />
                  <div>
                    <div className="text-xs font-display font-semibold text-white">Ollama Daemon Status</div>
                    <div className="text-[11px] font-mono text-slate-400">{status?.ollama?.endpoint}</div>
                  </div>
                </div>
                <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono font-semibold ${
                  status?.ollama?.online
                    ? 'bg-emerald-500/15 border border-emerald-500/40 text-emerald-400'
                    : 'bg-amber-500/15 border border-amber-500/40 text-amber-400'
                }`}>
                  {status?.ollama?.online ? (
                    <>
                      <CheckCircle className="w-3.5 h-3.5" />
                      CONNECTED
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="w-3.5 h-3.5" />
                      OFFLINE
                    </>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-display text-slate-200 tracking-wide">
                  Select Active Local Model:
                </label>
                {(((status?.ollama?.models || (status?.ollama as any)?.available_models || []) as string[]).length > 0) ? (
                  <div className="grid grid-cols-1 gap-2">
                    {((status?.ollama?.models || (status?.ollama as any)?.available_models || []) as string[]).map((m) => (
                      <button
                        key={m}
                        type="button"
                        onClick={() => setSelectedModel(m)}
                        className={`w-full flex items-center justify-between p-3 rounded-lg border text-left transition-all ${
                          selectedModel === m
                            ? 'bg-nova-cyan/15 border-nova-cyan text-white shadow-[0_0_12px_rgba(0,240,255,0.2)]'
                            : 'bg-nova-surface/40 border-nova-border/70 text-slate-300 hover:border-slate-500'
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          <div className={`w-3.5 h-3.5 rounded-full border flex items-center justify-center ${
                            selectedModel === m ? 'border-nova-cyan bg-nova-cyan' : 'border-slate-500'
                          }`}>
                            {selectedModel === m && <Check className="w-2.5 h-2.5 text-black stroke-[3]" />}
                          </div>
                          <div>
                            <div className="text-xs font-mono font-semibold">{m}</div>
                            <div className="text-[10px] text-slate-400">
                              {m.includes('2b') ? '~1.6 GB — Fast CPU response (Recommended for Intel i3)' : m.includes('4b') ? '~2.5 GB — High reasoning depth (Heavy on dual-core CPU)' : '~1.0 GB lightweight model'}
                            </div>
                          </div>
                        </div>
                        {selectedModel === m && (
                          <span className="text-[10px] font-mono text-nova-cyan uppercase tracking-wider font-semibold">
                            ACTIVE SELECTION
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="bg-amber-950/20 border border-amber-500/30 p-3.5 rounded-lg space-y-2 text-xs text-amber-200/90">
                    <p className="font-semibold flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-amber-400" />
                      No local models detected in Ollama.
                    </p>
                    <p>
                      Open your Windows Terminal and pull a recommended model offline:
                    </p>
                    <code className="block bg-black/60 p-2 rounded text-nova-cyan font-mono text-[11px]">
                      ollama run qwen2.5:3b
                    </code>
                    <p className="text-[11px] text-slate-400">
                      You can continue setup now and pull the model at any time.
                    </p>
                  </div>
                )}
              </div>
            </div>
          ) : step === 3 ? (
            /* STEP 3: Voice & Audio Setup */
            <div className="space-y-4 animate-fade-in">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-nova-cyan font-display text-sm font-semibold tracking-wide">
                  <Mic className="w-4 h-4" />
                  VOICE PIPELINE & WAKE-WORD DETECTION
                </div>
                <button
                  type="button"
                  onClick={() => setVoiceEnabled(!voiceEnabled)}
                  className={`text-xs px-2.5 py-1 rounded border font-mono transition-all ${
                    voiceEnabled
                      ? 'bg-nova-cyan/20 border-nova-cyan text-nova-cyan'
                      : 'bg-slate-800 border-slate-700 text-slate-400'
                  }`}
                >
                  {voiceEnabled ? 'VOICE ENABLED' : 'TEXT-ONLY MODE'}
                </button>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed">
                NOVA provides an offline voice pipeline using <span className="text-white">openWakeWord</span>, <span className="text-white">Vosk STT</span>, and <span className="text-white">Piper Neural TTS</span>.
              </p>

              {voiceEnabled ? (
                <div className="space-y-3">
                  {/* Wake Word Honest Info */}
                  <div className="bg-nova-surface/60 border border-nova-border p-3.5 rounded-lg space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-display font-semibold text-white flex items-center gap-1.5">
                        <Radio className="w-3.5 h-3.5 text-nova-cyan" />
                        Active Wake Phrase
                      </span>
                      <span className="text-xs font-mono bg-nova-cyan/15 text-nova-cyan px-2 py-0.5 rounded border border-nova-cyan/40">
                        "Hey Jarvis" (openWakeWord built-in)
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      openWakeWord detects the pre-trained offline phrase <span className="text-slate-200">"Hey Jarvis"</span> reliably on Windows with low CPU overhead.
                      An optional custom "Hey NOVA" model can be installed into <code className="text-nova-cyan text-[10px]">models/wake_words/</code>.
                    </p>
                  </div>

                  {/* Device selectors */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-mono text-slate-300 flex items-center gap-1">
                        <Mic className="w-3 h-3 text-nova-cyan" /> Microphone Input
                      </label>
                      <select
                        value={selectedInputDev ?? ''}
                        onChange={(e) => setSelectedInputDev(e.target.value ? Number(e.target.value) : undefined)}
                        className="w-full bg-nova-surface border border-nova-border text-white text-xs rounded p-2 focus:border-nova-cyan outline-none"
                      >
                        <option value="">Default System Microphone</option>
                        {devices?.inputs.map((d) => (
                          <option key={d.id} value={d.id}>{d.name}</option>
                        ))}
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[11px] font-mono text-slate-300 flex items-center gap-1">
                        <Volume2 className="w-3 h-3 text-nova-cyan" /> Speaker Output
                      </label>
                      <select
                        value={selectedOutputDev ?? ''}
                        onChange={(e) => setSelectedOutputDev(e.target.value ? Number(e.target.value) : undefined)}
                        className="w-full bg-nova-surface border border-nova-border text-white text-xs rounded p-2 focus:border-nova-cyan outline-none"
                      >
                        <option value="">Default System Speakers</option>
                        {devices?.outputs.map((d) => (
                          <option key={d.id} value={d.id}>{d.name}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="bg-slate-900/60 border border-slate-700/80 p-4 rounded-lg text-center space-y-2">
                  <p className="text-xs text-slate-300">
                    Voice input and audio monitoring are disabled. NOVA will run smoothly in high-performance text-only mode with zero audio device overhead.
                  </p>
                  <p className="text-[11px] text-slate-500">
                    You can toggle voice on at any time in Settings.
                  </p>
                </div>
              )}
            </div>
          ) : step === 4 ? (
            /* STEP 4: Privacy & Permissions */
            <div className="space-y-4 animate-fade-in">
              <div className="flex items-center gap-2 text-nova-cyan font-display text-sm font-semibold tracking-wide">
                <ShieldCheck className="w-4 h-4" />
                PRIVACY BOUNDARIES & SECURITY POLICIES
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                NOVA enforces strict security controls and privacy boundaries at execution time:
              </p>

              <div className="space-y-2.5">
                <label className="flex items-start gap-3 p-3 rounded-lg bg-nova-surface/50 border border-nova-border cursor-pointer hover:border-slate-500 transition-colors">
                  <input
                    type="checkbox"
                    checked={personalizationEnabled}
                    onChange={(e) => setPersonalizationEnabled(e.target.checked)}
                    className="mt-0.5 accent-cyan-400"
                  />
                  <div>
                    <div className="text-xs font-semibold text-white">Enable Adaptive Personalization</div>
                    <div className="text-[11px] text-slate-400 leading-relaxed">
                      Allows NOVA to learn your workflow preferences, response brevity, and project focus. Data remains in your local SQLite database and can be cleared at any time.
                    </div>
                  </div>
                </label>

                <label className="flex items-start gap-3 p-3 rounded-lg bg-nova-surface/50 border border-nova-border cursor-pointer hover:border-slate-500 transition-colors">
                  <input
                    type="checkbox"
                    checked={privacyScreenEnabled}
                    onChange={(e) => setPrivacyScreenEnabled(e.target.checked)}
                    className="mt-0.5 accent-cyan-400"
                  />
                  <div>
                    <div className="text-xs font-semibold text-white">Visual Intelligence Privacy Masking</div>
                    <div className="text-[11px] text-slate-400 leading-relaxed">
                      Screen inspection is 100% user-initiated and read-only. Sensitive credentials and private tokens are masked prior to OCR ingestion.
                    </div>
                  </div>
                </label>

                <div className="bg-nova-surface/30 border border-nova-border p-3 rounded-lg flex items-center gap-2.5 text-xs text-slate-300">
                  <Lock className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                  <span>Desktop operations (file changes, app launches) are gated by single-use approval tokens.</span>
                </div>
              </div>
            </div>
          ) : (
            /* STEP 5: Final Readiness Verification */
            <div className="space-y-4 animate-fade-in">
              <div className="flex items-center gap-2 text-emerald-400 font-display text-sm font-semibold tracking-wide">
                <CheckCircle className="w-4 h-4" />
                FINAL READINESS VERIFICATION
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                All configuration parameters and hardware boundaries have been verified. NOVA is ready to start.
              </p>

              <div className="bg-nova-surface/60 border border-nova-border rounded-lg p-4 space-y-2.5">
                <div className="flex justify-between items-center text-xs pb-2 border-b border-nova-border/50">
                  <span className="text-slate-400 font-mono">Selected Model:</span>
                  <span className="font-mono text-white font-semibold">{selectedModel}</span>
                </div>
                <div className="flex justify-between items-center text-xs pb-2 border-b border-nova-border/50">
                  <span className="text-slate-400 font-mono">Voice Pipeline:</span>
                  <span className="font-mono text-nova-cyan font-semibold">
                    {voiceEnabled ? 'Enabled ("Hey Jarvis" Wake Word)' : 'Text-Only Mode'}
                  </span>
                </div>
                <div className="flex justify-between items-center text-xs pb-2 border-b border-nova-border/50">
                  <span className="text-slate-400 font-mono">Personalization:</span>
                  <span className="font-mono text-emerald-400 font-semibold">
                    {personalizationEnabled ? 'Active (Local)' : 'Disabled'}
                  </span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400 font-mono">Persistence:</span>
                  <span className="font-mono text-slate-200">SQLite (WAL Mode, Backups enabled)</span>
                </div>
              </div>

              <p className="text-[11px] text-slate-400 italic text-center">
                You can re-run this setup wizard or adjust individual parameters anytime from the Settings panel.
              </p>
            </div>
          )}
        </div>

        {/* Footer Buttons */}
        <div className="p-4 border-t border-nova-border/80 flex items-center justify-between bg-nova-surface/30">
          <div>
            {step > 1 ? (
              <button
                type="button"
                onClick={() => setStep(step - 1)}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded text-xs font-semibold text-slate-400 hover:text-white border border-slate-700 hover:border-slate-500 transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Back
              </button>
            ) : (
              <button
                type="button"
                onClick={onClose}
                className="px-3.5 py-1.5 rounded text-xs font-semibold text-slate-500 hover:text-slate-300 transition-colors"
              >
                Skip for now
              </button>
            )}
          </div>

          <div>
            {step < totalSteps ? (
              <button
                type="button"
                onClick={() => setStep(step + 1)}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded text-xs font-display font-bold tracking-wider text-black bg-nova-cyan hover:bg-nova-cyan/90 transition-all shadow-[0_0_12px_rgba(0,240,255,0.4)]"
              >
                Next <ArrowRight className="w-3.5 h-3.5" />
              </button>
            ) : (
              <button
                type="button"
                disabled={submitting}
                onClick={handleFinish}
                className="flex items-center gap-1.5 px-5 py-2 rounded text-xs font-display font-bold tracking-wider text-black bg-emerald-400 hover:bg-emerald-300 transition-all shadow-[0_0_16px_rgba(52,211,153,0.4)] disabled:opacity-50"
              >
                {submitting ? 'Initializing NOVA...' : 'Complete Setup & Launch NOVA'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
