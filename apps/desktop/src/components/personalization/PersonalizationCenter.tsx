import React, { useState, useEffect } from 'react';
import { 
  BrainCircuit, 
  Sliders, 
  Layers, 
  Sparkles, 
  Network, 
  History, 
  ShieldCheck, 
  RefreshCw, 
  ArrowLeft,
  Power,
  FolderGit2
} from 'lucide-react';
import { PreferenceManager } from './PreferenceManager';
import { ContextOverview } from './ContextOverview';
import { RecommendationPanel } from './RecommendationPanel';
import { KnowledgeGraphView } from './KnowledgeGraphView';
import { FeedbackHistory } from './FeedbackHistory';
import { PersonalizationPrivacy } from './PersonalizationPrivacy';
import { PersonalizationStatus } from '../../types';
import { apiService } from '../../services/api';

interface PersonalizationCenterProps {
  onBackToDashboard?: () => void;
}

export const PersonalizationCenter: React.FC<PersonalizationCenterProps> = ({
  onBackToDashboard
}) => {
  const [activeSubTab, setActiveSubTab] = useState<
    'preferences' | 'context' | 'recommendations' | 'knowledge-graph' | 'feedback' | 'privacy'
  >('preferences');

  const [status, setStatus] = useState<PersonalizationStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);

  const loadStatus = async () => {
    try {
      const data = await apiService.getPersonalizationStatus();
      setStatus(data);
    } catch (err) {
      console.error('Failed to load personalization status:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const handleToggleMaster = async () => {
    if (!status) return;
    try {
      if (status.enabled) {
        await apiService.disablePersonalization();
      } else {
        await apiService.enablePersonalization();
      }
      await loadStatus();
    } catch (err) {
      console.error('Failed to toggle personalization:', err);
    }
  };

  const tabs = [
    { id: 'preferences', label: 'User Preferences', icon: Sliders, badge: status?.total_preferences },
    { id: 'context', label: 'Context Engine', icon: Layers },
    { id: 'recommendations', label: 'Recommendations', icon: Sparkles, badge: status?.pending_recommendations_count },
    { id: 'knowledge-graph', label: 'Knowledge Graph', icon: Network, badge: status?.total_graph_entities },
    { id: 'feedback', label: 'Feedback Loop', icon: History },
    { id: 'privacy', label: 'Privacy & Control', icon: ShieldCheck },
  ];

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-nova-dark/95 text-slate-100 p-4 space-y-4">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl bg-nova-surface/40 border border-nova-border/70 backdrop-blur-md">
        <div className="flex items-center gap-3">
          {onBackToDashboard && (
            <button
              onClick={onBackToDashboard}
              className="p-2 rounded-lg bg-nova-surface hover:bg-nova-surface/80 border border-nova-border text-slate-300 hover:text-nova-cyan transition-all"
              title="Back to Command Center"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
          )}

          <div className="p-2.5 rounded-xl bg-nova-cyan/10 border border-nova-cyan/30 text-nova-cyan">
            <BrainCircuit className="w-6 h-6 animate-pulse" />
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-display font-bold tracking-wider text-slate-100">
                PERSONAL INTELLIGENCE CENTER
              </h1>
              <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-nova-cyan/20 text-nova-cyan border border-nova-cyan/40">
                v0.8
              </span>
            </div>
            <p className="text-xs font-mono text-slate-400">
              Adaptive Intelligence, Explicit Preferences & Local Personal Knowledge Graph
            </p>
          </div>
        </div>

        {/* Status Badges & Master Switch */}
        <div className="flex flex-wrap items-center gap-3">
          {status && (
            <div className="flex items-center gap-2 text-[11px] font-mono">
              <span className="px-2 py-0.5 rounded bg-nova-dark/80 border border-nova-border text-slate-300 flex items-center gap-1.5">
                <FolderGit2 className="w-3 h-3 text-nova-cyan" />
                {status.active_project ? `Project: ${status.active_project}` : 'Global Context'}
              </span>

              <span className="px-2 py-0.5 rounded bg-nova-dark/80 border border-nova-border text-slate-300">
                {status.explicit_preferences_count} Explicit / {status.total_preferences} Prefs
              </span>

              <span className="px-2 py-0.5 rounded bg-nova-dark/80 border border-nova-border text-slate-300">
                {status.total_graph_entities} Graph Entities
              </span>
            </div>
          )}

          <button
            onClick={() => {
              setRefreshing(true);
              loadStatus();
            }}
            className="p-1.5 rounded text-slate-400 hover:text-nova-cyan hover:bg-nova-surface border border-transparent hover:border-nova-border transition-all"
            title="Refresh status"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>

          {status && (
            <button
              onClick={handleToggleMaster}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded font-mono text-xs font-semibold tracking-wider transition-all border ${
                status.enabled
                  ? 'bg-emerald-950/80 border-emerald-500/50 text-emerald-300 hover:bg-emerald-900/80 shadow-[0_0_10px_rgba(16,185,129,0.2)]'
                  : 'bg-slate-800 border-slate-600 text-slate-400 hover:bg-slate-700'
              }`}
            >
              <Power className="w-3.5 h-3.5" />
              <span>{status.enabled ? 'ACTIVE' : 'DISABLED'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-1 border-b border-nova-border/70 pb-1">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeSubTab === tab.id;

          return (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id as any)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-t-lg text-xs font-mono tracking-wider transition-all border-b-2 ${
                isActive
                  ? 'bg-nova-surface/60 border-nova-cyan text-nova-cyan font-semibold shadow-[0_2px_8px_rgba(0,240,255,0.15)]'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-nova-surface/30 border-transparent'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
              {tab.badge !== undefined && tab.badge > 0 && (
                <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                  isActive ? 'bg-nova-cyan/20 text-nova-cyan' : 'bg-slate-800 text-slate-400'
                }`}>
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Active Tab View Body */}
      <div className="flex-1 overflow-y-auto pr-1 custom-scrollbar">
        {activeSubTab === 'preferences' && <PreferenceManager />}
        {activeSubTab === 'context' && <ContextOverview />}
        {activeSubTab === 'recommendations' && <RecommendationPanel />}
        {activeSubTab === 'knowledge-graph' && <KnowledgeGraphView />}
        {activeSubTab === 'feedback' && <FeedbackHistory />}
        {activeSubTab === 'privacy' && <PersonalizationPrivacy />}
      </div>
    </div>
  );
};
