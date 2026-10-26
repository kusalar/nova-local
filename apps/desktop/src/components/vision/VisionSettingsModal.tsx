import React, { useState } from 'react';
import { 
  X, 
  ShieldCheck, 
  ShieldAlert, 
  Sliders, 
  Trash2, 
  HardDrive, 
  Save, 
  AlertTriangle,
  Eye,
  Lock
} from 'lucide-react';
import { VisionSettings, RetentionPolicy } from '../../types';

interface VisionSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: VisionSettings;
  onSave: (updated: Partial<VisionSettings>) => void;
  onClearCaptures: () => void;
  temporaryCount: number;
}

export const VisionSettingsModal: React.FC<VisionSettingsModalProps> = ({
  isOpen,
  onClose,
  settings,
  onSave,
  onClearCaptures,
  temporaryCount
}) => {
  const [formData, setFormData] = useState<VisionSettings>(settings);
  const [isSaved, setIsSaved] = useState(false);

  if (!isOpen) return null;

  const handleSave = () => {
    onSave(formData);
    setIsSaved(true);
    setTimeout(() => {
      setIsSaved(false);
      onClose();
    }, 800);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
      <div className="bg-nova-dark border border-nova-border rounded-xl w-full max-w-lg overflow-hidden shadow-[0_0_30px_rgba(0,240,255,0.15)] animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-nova-border/70 bg-nova-surface/40">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-nova-cyan" />
            <h3 className="text-sm font-semibold font-display tracking-wider text-slate-100">
              VISION PRIVACY & CAPTURE CONTROLS
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-100 hover:bg-nova-surface transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <div className="p-4 space-y-4 max-h-[75vh] overflow-y-auto custom-scrollbar font-mono text-xs">
          {/* Master Enable */}
          <div className="flex items-center justify-between p-3 bg-nova-surface/30 border border-nova-border/60 rounded-lg">
            <div>
              <span className="font-semibold text-slate-200 block">Vision Intelligence Subsystem</span>
              <span className="text-[11px] text-slate-400">
                Allow NOVA to inspect desktop screens upon explicit user request.
              </span>
            </div>
            <input
              type="checkbox"
              checked={formData.enabled}
              onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
              className="w-4 h-4 accent-nova-cyan cursor-pointer"
            />
          </div>

          {/* Retention Policy */}
          <div className="p-3 bg-nova-surface/30 border border-nova-border/60 rounded-lg space-y-2">
            <span className="font-semibold text-slate-200 block">Screenshot Retention Policy</span>
            <div className="space-y-1.5">
              {[
                { id: 'EPHEMERAL', label: 'Ephemeral (Purge immediately after question)', desc: 'Zero persistence. Recommended default.' },
                { id: 'SESSION', label: 'Session (Retain until app restart/clear)', desc: 'Kept in temporary memory cache.' },
                { id: 'PERSISTENT', label: 'Persistent (Manual save only)', desc: 'Saved locally only when explicitly requested.' }
              ].map((p) => (
                <label key={p.id} className="flex items-start gap-2 p-1.5 rounded hover:bg-nova-dark/60 cursor-pointer">
                  <input
                    type="radio"
                    name="retention"
                    value={p.id}
                    checked={formData.retention_policy === p.id}
                    onChange={(e) => setFormData({ ...formData, retention_policy: e.target.value as RetentionPolicy })}
                    className="mt-0.5 accent-nova-cyan"
                  />
                  <div>
                    <span className="text-slate-200 block font-semibold">{p.label}</span>
                    <span className="text-[10px] text-slate-500">{p.desc}</span>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Privacy Protections */}
          <div className="p-3 bg-nova-surface/30 border border-nova-border/60 rounded-lg space-y-3">
            <span className="font-semibold text-slate-200 block">Security & Credential Redaction</span>
            
            <div className="flex items-center justify-between">
              <div>
                <span className="text-slate-200 block">Automatic Credential Redaction</span>
                <span className="text-[10px] text-slate-500">
                  Filter out API keys, tokens, passwords, and credit card numbers from OCR.
                </span>
              </div>
              <input
                type="checkbox"
                checked={formData.auto_redact_sensitive}
                onChange={(e) => setFormData({ ...formData, auto_redact_sensitive: e.target.checked })}
                className="w-4 h-4 accent-nova-cyan cursor-pointer"
              />
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-nova-border/40">
              <div>
                <span className="text-slate-200 block">Sensitive Window Shield</span>
                <span className="text-[10px] text-slate-500">
                  Block capture if 1Password, Bitwarden, KeePass, or UAC prompts are active.
                </span>
              </div>
              <input
                type="checkbox"
                checked={formData.exclude_sensitive_windows}
                onChange={(e) => setFormData({ ...formData, exclude_sensitive_windows: e.target.checked })}
                className="w-4 h-4 accent-nova-cyan cursor-pointer"
              />
            </div>
          </div>

          {/* Performance & Downscaling */}
          <div className="p-3 bg-nova-surface/30 border border-nova-border/60 rounded-lg space-y-3">
            <span className="font-semibold text-slate-200 block">Performance & Scaling</span>
            
            <div>
              <div className="flex justify-between text-[11px] mb-1">
                <span className="text-slate-300">Max Dimension Scaling:</span>
                <span className="text-nova-cyan font-bold">{formData.max_image_dimension} px</span>
              </div>
              <input
                type="range"
                min={800}
                max={2560}
                step={80}
                value={formData.max_image_dimension}
                onChange={(e) => setFormData({ ...formData, max_image_dimension: Number(e.target.value) })}
                className="w-full accent-nova-cyan"
              />
              <span className="text-[10px] text-slate-500 block mt-0.5">
                Downscaled intelligently to preserve CPU efficiency and stay within 12GB memory budget.
              </span>
            </div>
          </div>

          {/* Ephemeral Cache Purge */}
          <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg flex items-center justify-between">
            <div>
              <span className="text-rose-300 font-semibold block">Ephemeral Screenshot Cache</span>
              <span className="text-[10px] text-slate-400">
                {temporaryCount} temporary capture(s) in local storage.
              </span>
            </div>
            <button
              onClick={onClearCaptures}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/50 rounded text-xs transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Purge Cache</span>
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-nova-border/70 bg-nova-surface/40 flex items-center justify-end gap-2">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="flex items-center gap-1.5 px-4 py-1.5 bg-nova-cyan/20 hover:bg-nova-cyan/30 text-nova-cyan border border-nova-cyan/50 rounded text-xs font-semibold tracking-wide transition-all"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{isSaved ? 'Saved!' : 'Save Settings'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
