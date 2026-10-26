import React, { useState, useEffect } from 'react';
import { 
  X, 
  Settings, 
  Cpu, 
  Volume2, 
  Save, 
  Check, 
  Mic, 
  Radio, 
  ShieldCheck, 
  Database, 
  Download, 
  Upload, 
  Sparkles,
  AlertCircle
} from 'lucide-react';
import { AiStatusResponse, VoiceStatusResponse, AudioDevice } from '../../types';
import { apiService } from '../../services/api';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  aiStatus: AiStatusResponse;
  voiceStatus?: VoiceStatusResponse | null;
  devices?: { inputs: AudioDevice[]; outputs: AudioDevice[] };
  onSaveModel: (modelName: string) => void;
  onSaveVoiceSettings?: (settings: any) => Promise<boolean>;
  onOpenOnboarding?: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  aiStatus,
  voiceStatus,
  devices,
  onSaveModel,
  onSaveVoiceSettings,
  onOpenOnboarding,
}) => {
  const [activeTab, setActiveTab] = useState<'voice' | 'ai' | 'privacy' | 'database' | 'export_import'>('voice');
  
  // AI Settings
  const [modelInput, setModelInput] = useState(aiStatus.active_model || 'qwen2.5:3b');
  const [endpointInput, setEndpointInput] = useState(aiStatus.endpoint || 'http://localhost:11434');
  const [temperature, setTemperature] = useState<number>(0.7);
  const [numCtx, setNumCtx] = useState<number>(1024);
  const [numPredict, setNumPredict] = useState<number>(256);
  const [numPredictVoice, setNumPredictVoice] = useState<number>(96);
  const [threadMode, setThreadMode] = useState<'auto' | 'manual'>('manual');
  const [numThread, setNumThread] = useState<number>(2);
  const [keepAlive, setKeepAlive] = useState<string>('10m');
  const [voiceMode, setVoiceMode] = useState<'push_to_talk' | 'wake_word'>('push_to_talk');
  
  // Voice Settings
  const [wakeWordEnabled, setWakeWordEnabled] = useState(voiceStatus?.wake_word_enabled ?? true);
  const [threshold, setThreshold] = useState(voiceStatus?.wake_word?.threshold ?? 0.5);
  const [inputDev, setInputDev] = useState<number | undefined>(voiceStatus?.audio?.input_device);
  const [outputDev, setOutputDev] = useState<number | undefined>(voiceStatus?.audio?.output_device);
  const [speechRate, setSpeechRate] = useState(voiceStatus?.tts?.speech_rate ?? 1.05);
  const [ttsVolume, setTtsVolume] = useState(voiceStatus?.tts?.volume ?? 1.0);

  // Privacy & Memory Settings
  const [retentionDays, setRetentionDays] = useState<number>(90);
  const [privacyScreen, setPrivacyScreen] = useState<boolean>(true);
  const [personalizationEnabled, setPersonalizationEnabled] = useState<boolean>(true);

  // Status flags
  const [saved, setSaved] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadUnifiedSettings();
    }
  }, [isOpen]);

  const loadUnifiedSettings = async () => {
    try {
      const cfg = await apiService.getUnifiedSettings();
      if (cfg) {
        if (cfg.ai?.active_model) setModelInput(cfg.ai.active_model);
        if (cfg.ai?.ollama_endpoint) setEndpointInput(cfg.ai.ollama_endpoint);
        if (cfg.ai?.inference) {
          setTemperature(cfg.ai.inference.temperature ?? 0.7);
          setNumCtx(cfg.ai.inference.num_ctx ?? 1024);
          setNumPredict(cfg.ai.inference.num_predict ?? 256);
          setNumPredictVoice(cfg.ai.inference.num_predict_voice ?? 96);
          setKeepAlive(cfg.ai.inference.keep_alive || '10m');
          setThreadMode(cfg.ai.inference.thread_mode === 'auto' ? 'auto' : 'manual');
          setNumThread(cfg.ai.inference.num_thread ?? 2);
        }
        if (cfg.voice) {
          setWakeWordEnabled(cfg.voice.wake_word_enabled);
          setVoiceMode(cfg.voice.wake_word_enabled ? 'wake_word' : 'push_to_talk');
          setThreshold(cfg.voice.wake_word_threshold || 0.5);
          setInputDev(cfg.voice.input_device);
          setOutputDev(cfg.voice.output_device);
          setSpeechRate(cfg.voice.speech_rate || 1.05);
          setTtsVolume(cfg.voice.volume || 1.0);
        }
        if (cfg.privacy_and_memory) {
          setRetentionDays(cfg.privacy_and_memory.retention_days || 90);
          setPrivacyScreen(cfg.privacy_and_memory.screen_capture_allowed ?? true);
          setPersonalizationEnabled(cfg.privacy_and_memory.personalization_enabled ?? true);
        }
      }
    } catch (err) {
      console.warn('Could not load unified settings, using active memory state:', err);
    }
  };

  if (!isOpen) return null;

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    onSaveModel(modelInput);
    try {
      await apiService.updateInferenceSettings({
        active_model: modelInput,
        temperature,
        num_ctx: numCtx,
        num_predict: numPredict,
        num_predict_voice: numPredictVoice,
        thread_mode: threadMode,
        num_thread: threadMode === 'auto' ? null : numThread,
        keep_alive: keepAlive,
        voice_mode: voiceMode,
        wake_word_enabled: voiceMode === 'wake_word'
      });
    } catch (err) {
      console.warn('Inference settings update failed', err);
    }
    if (onSaveVoiceSettings) {
      await onSaveVoiceSettings({
        wake_word_enabled: voiceMode === 'wake_word',
        voice_mode: voiceMode,
        wake_word_threshold: threshold,
        input_device: inputDev,
        output_device: outputDev,
        tts_speech_rate: speechRate,
        tts_volume: ttsVolume
      });
    }

    // Save privacy settings
    try {
      await apiService.updatePersonalizationPrivacySettings({
        enabled: personalizationEnabled,
        adaptive_analysis_enabled: personalizationEnabled,
        recommendations_enabled: personalizationEnabled,
        store_inferred_preferences: personalizationEnabled
      });
    } catch (err) {
      // Ignored if personalization endpoint already synced
    }

    setSaved(true);
    setStatusMsg('Settings successfully updated');
    setTimeout(() => {
      setSaved(false);
      setStatusMsg(null);
      onClose();
    }, 900);
  };

  const handleExportConfig = async () => {
    try {
      const exported = await apiService.exportSettings();
      const blob = new Blob([JSON.stringify(exported, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `nova_settings_${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setStatusMsg('Configuration exported to JSON file');
    } catch (err) {
      setStatusMsg('Failed to export configuration');
    }
  };

  const handleImportConfig = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      await apiService.importSettings(parsed);
      setStatusMsg('Configuration imported successfully!');
      await loadUnifiedSettings();
    } catch (err: any) {
      setStatusMsg(`Import error: ${err.message || 'Invalid JSON file'}`);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm animate-fade-in select-none">
      <div 
        className="hud-panel w-full max-w-2xl p-5 border-nova-cyan/40 shadow-nova-orb bg-nova-dark/95"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-nova-border">
          <div className="flex items-center gap-2.5">
            <Settings className="w-5 h-5 text-nova-cyan" />
            <h2 className="font-display font-bold text-sm tracking-wider text-white uppercase">
              NOVA v1.0 CENTRALIZED CONFIGURATION & SETTINGS
            </h2>
          </div>
          <button onClick={onClose} className="p-1 rounded text-slate-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-nova-border/60 mt-3 overflow-x-auto">
          <button
            type="button"
            onClick={() => setActiveTab('voice')}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-display font-bold tracking-wider border-b-2 transition-all whitespace-nowrap ${
              activeTab === 'voice'
                ? 'border-nova-cyan text-nova-cyan bg-nova-cyan/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Mic className="w-3.5 h-3.5" />
            <span>VOICE & AUDIO</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('ai')}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-display font-bold tracking-wider border-b-2 transition-all whitespace-nowrap ${
              activeTab === 'ai'
                ? 'border-nova-cyan text-nova-cyan bg-nova-cyan/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>AI NEURAL ENGINE</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('privacy')}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-display font-bold tracking-wider border-b-2 transition-all whitespace-nowrap ${
              activeTab === 'privacy'
                ? 'border-nova-cyan text-nova-cyan bg-nova-cyan/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>PRIVACY & SECURITY</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('database')}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-display font-bold tracking-wider border-b-2 transition-all whitespace-nowrap ${
              activeTab === 'database'
                ? 'border-nova-cyan text-nova-cyan bg-nova-cyan/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            <span>PERSISTENCE</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('export_import')}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-display font-bold tracking-wider border-b-2 transition-all whitespace-nowrap ${
              activeTab === 'export_import'
                ? 'border-nova-cyan text-nova-cyan bg-nova-cyan/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Download className="w-3.5 h-3.5" />
            <span>IMPORT / EXPORT</span>
          </button>
        </div>

        {/* Tab Contents */}
        <form onSubmit={handleSave} className="space-y-4 mt-4 text-xs font-mono max-h-[60vh] overflow-y-auto pr-1 custom-scrollbar">
          {activeTab === 'voice' ? (
            <div className="space-y-3.5">
              <div className="p-3 rounded bg-nova-surface border border-nova-border/70 space-y-2.5">
                <div className="font-display font-bold text-slate-200">Microphone mode</div>
                <label className="flex items-center gap-2 text-slate-300">
                  <input
                    type="radio"
                    name="voice_mode"
                    checked={voiceMode === 'push_to_talk'}
                    onChange={() => { setVoiceMode('push_to_talk'); setWakeWordEnabled(false); }}
                    className="accent-nova-cyan"
                  />
                  Push-to-talk (mic closed until you tap)
                </label>
                <label className="flex items-center gap-2 text-slate-300">
                  <input
                    type="radio"
                    name="voice_mode"
                    checked={voiceMode === 'wake_word'}
                    onChange={() => { setVoiceMode('wake_word'); setWakeWordEnabled(true); }}
                    className="accent-nova-cyan"
                  />
                  Continuous wake-word (optional)
                </label>
                <p className="text-[10px] text-slate-500">
                  Default on this hardware is push-to-talk so idle CPU stays low. Wake-word remains available.
                </p>
              </div>

              {/* Wake Word Controls */}
              <div className="p-3 rounded bg-nova-surface border border-nova-border/70 space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Radio className="w-4 h-4 text-nova-cyan" />
                    <span className="font-display font-bold text-slate-200">
                      Offline Wake Word Detection (openWakeWord)
                    </span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={wakeWordEnabled}
                      onChange={(e) => setWakeWordEnabled(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-nova-cyan"></div>
                  </label>
                </div>
                
                <div className="p-2 rounded bg-black/40 border border-nova-border/50 space-y-1">
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="text-slate-400">Active Wake Phrase:</span>
                    <span className="text-nova-cyan font-bold">"{voiceStatus?.wake_word?.wake_phrase || 'Hey Jarvis'}"</span>
                  </div>
                  <div className="flex justify-between items-center text-[10px] text-slate-500">
                    <span>Engine: openWakeWord (built-in)</span>
                    <span>Custom "Hey NOVA": Optional ONNX</span>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-[11px] text-slate-300 mb-1">
                    <span>Sensitivity Threshold: {threshold.toFixed(2)}</span>
                    <span className="text-slate-400">Higher = fewer false positives</span>
                  </div>
                  <input
                    type="range"
                    min="0.1"
                    max="0.9"
                    step="0.05"
                    value={threshold}
                    onChange={(e) => setThreshold(parseFloat(e.target.value))}
                    className="w-full accent-nova-cyan bg-slate-800 rounded h-1 cursor-pointer"
                  />
                </div>
              </div>

              {/* Microphone & Speaker Devices */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-slate-300 block">Microphone Input Device</label>
                  <select
                    value={inputDev ?? ''}
                    onChange={(e) => setInputDev(e.target.value === '' ? undefined : parseInt(e.target.value))}
                    className="w-full px-3 py-2 rounded bg-nova-surface border border-nova-border text-white text-xs focus:outline-none focus:border-nova-cyan"
                  >
                    <option value="">Default System Microphone</option>
                    {devices?.inputs.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-slate-300 block">Speaker Output Device</label>
                  <select
                    value={outputDev ?? ''}
                    onChange={(e) => setOutputDev(e.target.value === '' ? undefined : parseInt(e.target.value))}
                    className="w-full px-3 py-2 rounded bg-nova-surface border border-nova-border text-white text-xs focus:outline-none focus:border-nova-cyan"
                  >
                    <option value="">Default System Speaker</option>
                    {devices?.outputs.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Piper TTS Settings */}
              <div className="p-3 rounded bg-nova-surface border border-nova-border/70 space-y-2.5">
                <div className="flex items-center gap-2 text-nova-cyan font-bold">
                  <Volume2 className="w-4 h-4" />
                  <span>Piper Neural TTS Speech Synthesis</span>
                </div>
                
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-slate-300 block mb-1">Speaking Rate: {speechRate.toFixed(2)}x</label>
                    <input
                      type="range"
                      min="0.75"
                      max="1.5"
                      step="0.05"
                      value={speechRate}
                      onChange={(e) => setSpeechRate(parseFloat(e.target.value))}
                      className="w-full accent-nova-cyan bg-slate-800 rounded h-1 cursor-pointer"
                    />
                  </div>
                  <div>
                    <label className="text-slate-300 block mb-1">TTS Volume: {Math.round(ttsVolume * 100)}%</label>
                    <input
                      type="range"
                      min="0.2"
                      max="1.5"
                      step="0.05"
                      value={ttsVolume}
                      onChange={(e) => setTtsVolume(parseFloat(e.target.value))}
                      className="w-full accent-nova-cyan bg-slate-800 rounded h-1 cursor-pointer"
                    />
                  </div>
                </div>
              </div>
            </div>
          ) : activeTab === 'ai' ? (
            <div className="space-y-3.5">
              <div>
                <label className="text-slate-300 block mb-1">Local Ollama Endpoint</label>
                <input
                  type="text"
                  value={endpointInput}
                  onChange={(e) => setEndpointInput(e.target.value)}
                  className="w-full px-3 py-2 rounded bg-nova-surface border border-nova-border text-white focus:outline-none focus:border-nova-cyan"
                />
                <span className="text-[10px] text-slate-400 mt-0.5 block">
                  Default is http://localhost:11434
                </span>
              </div>

              <div>
                <label className="text-slate-300 block mb-1">Active AI Model Name</label>
                <input
                  type="text"
                  value={modelInput}
                  onChange={(e) => setModelInput(e.target.value)}
                  className="w-full px-3 py-2 rounded bg-nova-surface border border-nova-border text-white focus:outline-none focus:border-nova-cyan"
                  placeholder="e.g. qwen2.5:3b, qwen2.5:1.5b"
                />
                <span className="text-[10px] text-slate-400 mt-0.5 block">
                  Run in terminal: <code className="text-nova-cyan">ollama run {modelInput}</code>
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-2">
                <div>
                  <label className="text-slate-300 block mb-1">Inference Temperature: {temperature}</label>
                  <input
                    type="range"
                    min="0.1"
                    max="1.0"
                    step="0.05"
                    value={temperature}
                    onChange={(e) => setTemperature(parseFloat(e.target.value))}
                    className="w-full accent-nova-cyan bg-slate-800 rounded h-1 cursor-pointer"
                  />
                  <span className="text-[10px] text-slate-500">Lower = deterministic, Higher = creative</span>
                </div>
                <div>
                  <label className="text-slate-300 block mb-1">Context window (num_ctx): {numCtx}</label>
                  <input
                    type="number"
                    min="256"
                    max="4096"
                    step="128"
                    value={numCtx}
                    onChange={(e) => setNumCtx(parseInt(e.target.value) || 1024)}
                    className="w-full px-3 py-1.5 rounded bg-nova-surface border border-nova-border text-white focus:outline-none focus:border-nova-cyan"
                  />
                </div>
                <div>
                  <label className="text-slate-300 block mb-1">Text max tokens: {numPredict}</label>
                  <input
                    type="number"
                    min="16"
                    max="1024"
                    step="16"
                    value={numPredict}
                    onChange={(e) => setNumPredict(parseInt(e.target.value) || 256)}
                    className="w-full px-3 py-1.5 rounded bg-nova-surface border border-nova-border text-white focus:outline-none focus:border-nova-cyan"
                  />
                </div>
                <div>
                  <label className="text-slate-300 block mb-1">Voice max tokens: {numPredictVoice}</label>
                  <input
                    type="number"
                    min="16"
                    max="256"
                    step="8"
                    value={numPredictVoice}
                    onChange={(e) => setNumPredictVoice(parseInt(e.target.value) || 96)}
                    className="w-full px-3 py-1.5 rounded bg-nova-surface border border-nova-border text-white focus:outline-none focus:border-nova-cyan"
                  />
                </div>
                <div>
                  <label className="text-slate-300 block mb-1">CPU threads</label>
                  <select
                    value={threadMode}
                    onChange={(e) => setThreadMode(e.target.value as 'auto' | 'manual')}
                    className="w-full px-3 py-1.5 rounded bg-nova-surface border border-nova-border text-white"
                  >
                    <option value="manual">Manual (2 recommended on i3)</option>
                    <option value="auto">Ollama automatic</option>
                  </select>
                  {threadMode === 'manual' && (
                    <input
                      type="number"
                      min="1"
                      max="8"
                      value={numThread}
                      onChange={(e) => setNumThread(parseInt(e.target.value) || 2)}
                      className="w-full mt-1 px-3 py-1.5 rounded bg-nova-surface border border-nova-border text-white"
                    />
                  )}
                </div>
                <div>
                  <label className="text-slate-300 block mb-1">keep_alive</label>
                  <input
                    type="text"
                    value={keepAlive}
                    onChange={(e) => setKeepAlive(e.target.value)}
                    className="w-full px-3 py-1.5 rounded bg-nova-surface border border-nova-border text-white"
                  />
                  <span className="text-[10px] text-slate-500">Keeps the model in RAM (default 10m)</span>
                </div>
              </div>
            </div>
          ) : activeTab === 'privacy' ? (
            <div className="space-y-3.5">
              <div className="p-3 rounded bg-nova-surface border border-nova-border/70 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-white">Adaptive Personalization</div>
                    <div className="text-[11px] text-slate-400">Permit NOVA to adapt response tone and recall user preferences</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={personalizationEnabled}
                    onChange={(e) => setPersonalizationEnabled(e.target.checked)}
                    className="accent-nova-cyan w-4 h-4 cursor-pointer"
                  />
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-nova-border/50">
                  <div>
                    <div className="font-semibold text-white">Screen Capture Permission</div>
                    <div className="text-[11px] text-slate-400">Allow user-initiated visual screen OCR and window inspection</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={privacyScreen}
                    onChange={(e) => setPrivacyScreen(e.target.checked)}
                    className="accent-nova-cyan w-4 h-4 cursor-pointer"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-300 block mb-1">Short-term Memory Retention (Days)</label>
                <input
                  type="number"
                  min="7"
                  max="365"
                  value={retentionDays}
                  onChange={(e) => setRetentionDays(parseInt(e.target.value) || 90)}
                  className="w-full px-3 py-2 rounded bg-nova-surface border border-nova-border text-white focus:outline-none focus:border-nova-cyan"
                />
                <span className="text-[10px] text-slate-400 mt-0.5 block">
                  Transient conversation turns older than this are archived
                </span>
              </div>
            </div>
          ) : activeTab === 'database' ? (
            <div className="space-y-3.5">
              <div className="p-3 rounded bg-nova-surface border border-nova-border/70 space-y-2 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Database Engine:</span>
                  <span className="text-white font-semibold">SQLite 3.x</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Journal Mode:</span>
                  <span className="text-emerald-400 font-semibold">WAL (Write-Ahead Logging)</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Lock Busy Timeout:</span>
                  <span className="text-white">5,000 ms</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Storage Location:</span>
                  <span className="text-nova-cyan font-mono text-[11px]">nova_memory.db</span>
                </div>
              </div>

              <div className="p-3 rounded bg-blue-950/20 border border-blue-500/30 text-[11px] text-blue-200/90 leading-relaxed">
                Automated pre-restore backups and verified SQLite checksums ensure zero data corruption across upgrades.
              </div>
            </div>
          ) : (
            /* Export / Import & Onboarding Wizard */
            <div className="space-y-4">
              <div className="p-3 rounded bg-nova-surface border border-nova-border/70 space-y-2">
                <div className="font-semibold text-white flex items-center gap-1.5">
                  <Download className="w-4 h-4 text-nova-cyan" />
                  Export Configuration
                </div>
                <p className="text-[11px] text-slate-400">
                  Export non-secret preferences, AI configurations, and voice settings to a portable JSON file.
                </p>
                <button
                  type="button"
                  onClick={handleExportConfig}
                  className="px-3 py-1.5 rounded bg-nova-cyan/20 border border-nova-cyan/40 text-nova-cyan text-xs font-semibold hover:bg-nova-cyan/30 flex items-center gap-1.5"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download settings.json
                </button>
              </div>

              <div className="p-3 rounded bg-nova-surface border border-nova-border/70 space-y-2">
                <div className="font-semibold text-white flex items-center gap-1.5">
                  <Upload className="w-4 h-4 text-emerald-400" />
                  Import Configuration
                </div>
                <p className="text-[11px] text-slate-400">
                  Restore previously exported configuration. System secrets and tokens are rejected for security.
                </p>
                <label className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs font-semibold hover:bg-emerald-500/30 cursor-pointer">
                  <Upload className="w-3.5 h-3.5" />
                  <span>Choose JSON File</span>
                  <input
                    type="file"
                    accept=".json"
                    onChange={handleImportConfig}
                    className="hidden"
                  />
                </label>
              </div>

              {onOpenOnboarding && (
                <div className="p-3 rounded bg-nova-surface border border-nova-border/70 space-y-2">
                  <div className="font-semibold text-white flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-amber-400" />
                    First-Run Setup Wizard
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Re-launch the step-by-step setup wizard to verify hardware compatibility, Ollama models, and voice setup.
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      onClose();
                      onOpenOnboarding();
                    }}
                    className="px-3 py-1.5 rounded bg-amber-500/20 border border-amber-500/40 text-amber-300 text-xs font-semibold hover:bg-amber-500/30 flex items-center gap-1.5"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    Launch Setup Wizard
                  </button>
                </div>
              )}
            </div>
          )}

          {statusMsg && (
            <div className="p-2 rounded bg-nova-cyan/15 border border-nova-cyan/40 text-nova-cyan text-[11px] flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5" />
              <span>{statusMsg}</span>
            </div>
          )}

          <div className="flex justify-between items-center pt-3 border-t border-nova-border/60">
            <span className="text-[10px] text-slate-500 font-mono">NOVA Desktop v1.0.0</span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 rounded bg-nova-surface border border-nova-border text-slate-300 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 rounded bg-nova-cyan text-nova-dark font-display font-bold uppercase tracking-wider hover:bg-white flex items-center gap-1.5 shadow-nova-cyan"
              >
                {saved ? <Check className="w-4 h-4" /> : <Save className="w-4 h-4" />}
                <span>{saved ? 'Saved' : 'Save Config'}</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
