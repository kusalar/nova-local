import React, { useState, useEffect } from 'react';
import { 
  Sliders, 
  Plus, 
  Trash2, 
  Edit3, 
  Check, 
  X, 
  Sparkles, 
  ShieldCheck, 
  Filter, 
  RefreshCw,
  Info
} from 'lucide-react';
import { UserPreference, PreferenceCategory } from '../../types';
import { apiService } from '../../services/api';

const CATEGORIES: { id: PreferenceCategory; label: string }[] = [
  { id: 'response_length', label: 'Response Length' },
  { id: 'explanation_depth', label: 'Explanation Depth' },
  { id: 'programming_language', label: 'Programming Languages' },
  { id: 'development_tools', label: 'Development Tools' },
  { id: 'communication_style', label: 'Communication Style' },
  { id: 'notification_behavior', label: 'Notification Behavior' },
  { id: 'voice_response', label: 'Voice Response' },
  { id: 'automation_schedule', label: 'Automation Schedules' },
  { id: 'general', label: 'General' },
];

export const PreferenceManager: React.FC = () => {
  const [preferences, setPreferences] = useState<UserPreference[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [explicitOnly, setExplicitOnly] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // New preference modal/form state
  const [isAdding, setIsAdding] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [newKey, setNewKey] = useState('');
  const [newCategory, setNewCategory] = useState<PreferenceCategory>('response_length');
  const [newValue, setNewValue] = useState('');
  const [newScope, setNewScope] = useState('');

  const loadPreferences = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const cat = selectedCategory === 'all' ? undefined : selectedCategory;
      const data = await apiService.getPreferences(cat, explicitOnly);
      setPreferences(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load preferences');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPreferences();
  }, [selectedCategory, explicitOnly]);

  const handleSavePreference = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKey.trim() || !newValue.trim()) return;

    try {
      let parsedValue: any = newValue;
      try {
        parsedValue = JSON.parse(newValue);
      } catch {
        parsedValue = newValue;
      }

      if (editingId !== null) {
        await apiService.updatePreference(editingId, {
          value: parsedValue,
          context_scope: newScope.trim() || undefined
        });
      } else {
        await apiService.setPreference({
          key: newKey.trim(),
          category: newCategory,
          value: parsedValue,
          is_explicit: true,
          source: 'explicit_ui',
          context_scope: newScope.trim() || undefined
        });
      }

      setIsAdding(false);
      setEditingId(null);
      setNewKey('');
      setNewValue('');
      setNewScope('');
      loadPreferences();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to save preference');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await apiService.deletePreference(id);
      setPreferences(prev => prev.filter(p => p.id !== id));
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to delete preference');
    }
  };

  const startEdit = (pref: UserPreference) => {
    setEditingId(pref.id);
    setNewKey(pref.key);
    setNewCategory(pref.category);
    setNewValue(typeof pref.value === 'object' ? JSON.stringify(pref.value) : String(pref.value));
    setNewScope(pref.context_scope || '');
    setIsAdding(true);
  };

  return (
    <div className="space-y-4">
      {/* Header Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg bg-nova-surface/60 border border-nova-border/70 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs font-mono text-nova-cyan">
            <Filter className="w-3.5 h-3.5" />
            <span>CATEGORY:</span>
          </div>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="bg-nova-dark/80 border border-nova-border rounded px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-nova-cyan"
          >
            <option value="all">All Categories</option>
            {CATEGORIES.map(c => (
              <option key={c.id} value={c.id}>{c.label}</option>
            ))}
          </select>

          <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer ml-2">
            <input
              type="checkbox"
              checked={explicitOnly}
              onChange={(e) => setExplicitOnly(e.target.checked)}
              className="rounded bg-nova-dark border-nova-border text-nova-cyan focus:ring-0"
            />
            <span className="font-mono text-[11px]">Explicit Only</span>
          </label>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadPreferences}
            className="p-1.5 rounded text-slate-400 hover:text-nova-cyan hover:bg-nova-surface border border-transparent hover:border-nova-border transition-all"
            title="Refresh preferences"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => {
              setEditingId(null);
              setNewKey('');
              setNewCategory('response_length');
              setNewValue('');
              setNewScope('');
              setIsAdding(true);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-nova-cyan/20 border border-nova-cyan/50 text-nova-cyan hover:bg-nova-cyan/30 text-xs font-mono tracking-wider transition-all shadow-[0_0_10px_rgba(0,240,255,0.15)]"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>ADD PREFERENCE</span>
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 rounded bg-red-950/60 border border-red-500/40 text-red-200 text-xs font-mono flex items-center justify-between">
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)}><X className="w-3.5 h-3.5" /></button>
        </div>
      )}

      {/* Add / Edit Form Modal */}
      {isAdding && (
        <form onSubmit={handleSavePreference} className="p-4 rounded-lg bg-nova-dark/95 border border-nova-cyan/40 shadow-xl space-y-3">
          <div className="flex items-center justify-between border-b border-nova-border/60 pb-2">
            <h4 className="text-xs font-mono text-nova-cyan uppercase tracking-wider flex items-center gap-2">
              <Sliders className="w-3.5 h-3.5" />
              {editingId ? 'Edit Preference' : 'Create Explicit Preference'}
            </h4>
            <button
              type="button"
              onClick={() => setIsAdding(false)}
              className="text-slate-400 hover:text-slate-200"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            <div>
              <label className="block font-mono text-slate-400 mb-1">Key / Identifier</label>
              <input
                type="text"
                value={newKey}
                onChange={(e) => setNewKey(e.target.value)}
                disabled={editingId !== null}
                placeholder="e.g. response_length, primary_language"
                className="w-full bg-nova-surface border border-nova-border rounded px-2.5 py-1.5 text-slate-100 font-mono disabled:opacity-50 focus:outline-none focus:border-nova-cyan"
                required
              />
            </div>

            <div>
              <label className="block font-mono text-slate-400 mb-1">Category</label>
              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value as PreferenceCategory)}
                disabled={editingId !== null}
                className="w-full bg-nova-surface border border-nova-border rounded px-2.5 py-1.5 text-slate-100 font-mono focus:outline-none focus:border-nova-cyan"
              >
                {CATEGORIES.map(c => (
                  <option key={c.id} value={c.id}>{c.label}</option>
                ))}
              </select>
            </div>

            <div className="md:col-span-2">
              <label className="block font-mono text-slate-400 mb-1">Value (String or JSON)</label>
              <textarea
                value={newValue}
                onChange={(e) => setNewValue(e.target.value)}
                placeholder='e.g. "concise", "detailed", ["Python", "Rust"], or {"detail": "high"}'
                rows={2}
                className="w-full bg-nova-surface border border-nova-border rounded px-2.5 py-1.5 text-slate-100 font-mono focus:outline-none focus:border-nova-cyan"
                required
              />
            </div>

            <div className="md:col-span-2">
              <label className="block font-mono text-slate-400 mb-1">Project Scope (Optional)</label>
              <input
                type="text"
                value={newScope}
                onChange={(e) => setNewScope(e.target.value)}
                placeholder="Leave blank for global, or specify project name (e.g. Nova, HireLens)"
                className="w-full bg-nova-surface border border-nova-border rounded px-2.5 py-1.5 text-slate-100 font-mono focus:outline-none focus:border-nova-cyan"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-nova-border/60">
            <button
              type="button"
              onClick={() => setIsAdding(false)}
              className="px-3 py-1 rounded text-xs font-mono text-slate-400 hover:text-slate-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 rounded bg-nova-cyan text-nova-dark font-mono font-semibold text-xs tracking-wider hover:bg-nova-teal transition-all flex items-center gap-1.5"
            >
              <Check className="w-3.5 h-3.5" />
              <span>SAVE PREFERENCE</span>
            </button>
          </div>
        </form>
      )}

      {/* Preferences Grid */}
      {preferences.length === 0 ? (
        <div className="p-8 text-center border border-dashed border-nova-border/50 rounded-lg text-slate-500 font-mono text-xs">
          <Info className="w-6 h-6 mx-auto mb-2 text-slate-600" />
          No preferences found for the current filter. Add one or interact via chat/voice!
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {preferences.map((pref) => {
            const isExplicit = pref.is_explicit;
            const displayVal = typeof pref.value === 'object' ? JSON.stringify(pref.value) : String(pref.value);

            return (
              <div
                key={pref.id}
                className="group relative p-3 rounded-lg bg-nova-surface/40 hover:bg-nova-surface/70 border border-nova-border/60 hover:border-nova-cyan/40 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-1.5">
                    <span className="font-mono text-xs font-semibold text-slate-200 group-hover:text-nova-cyan transition-colors">
                      {pref.key}
                    </span>
                    <span
                      className={`text-[9px] font-mono px-1.5 py-0.5 rounded flex items-center gap-1 ${
                        isExplicit
                          ? 'bg-emerald-950/70 text-emerald-400 border border-emerald-500/30'
                          : 'bg-purple-950/70 text-purple-300 border border-purple-500/30'
                      }`}
                    >
                      {isExplicit ? <ShieldCheck className="w-2.5 h-2.5" /> : <Sparkles className="w-2.5 h-2.5" />}
                      {isExplicit ? 'EXPLICIT' : 'INFERRED'}
                    </span>
                  </div>

                  <div className="text-[10px] font-mono text-nova-cyanDim mb-2">
                    {pref.category.replace('_', ' ').toUpperCase()}
                    {pref.context_scope && (
                      <span className="ml-1.5 px-1 py-0.2 rounded bg-nova-dark/80 border border-nova-border text-slate-400">
                        {pref.context_scope}
                      </span>
                    )}
                  </div>

                  <div className="p-2 rounded bg-nova-dark/80 border border-nova-border/50 font-mono text-xs text-nova-teal break-words">
                    {displayVal}
                  </div>
                </div>

                <div className="mt-3 pt-2 border-t border-nova-border/40 flex items-center justify-between text-[10px] font-mono text-slate-500">
                  <span>Confidence: {(pref.confidence * 100).toFixed(0)}%</span>
                  <div className="flex items-center gap-1 opacity-80 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => startEdit(pref)}
                      className="p-1 text-slate-400 hover:text-nova-cyan transition-colors"
                      title="Edit preference"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => handleDelete(pref.id)}
                      className="p-1 text-slate-400 hover:text-red-400 transition-colors"
                      title="Delete preference"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
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
