import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldCheck,
  Activity,
  Database,
  AlertTriangle,
  FileText,
  RefreshCw,
  Cpu,
  Layers,
  ArrowLeft,
} from 'lucide-react';
import { apiService } from '../../services/api';
import {
  SystemHealthSummary,
  ConcurrencyMetrics,
  DatabaseStatus,
  RecentErrorItem,
} from '../../types';
import { SubsystemHealthGrid } from './SubsystemHealthGrid';
import { ResourceMonitor } from './ResourceMonitor';
import { DatabaseHealthPanel } from './DatabaseHealthPanel';
import { BackupManager } from './BackupManager';
import { RecentErrorsPanel } from './RecentErrorsPanel';
import { DiagnosticExport } from './DiagnosticExport';

interface SystemReliabilityCenterProps {
  onBackToDashboard?: () => void;
}

export const SystemReliabilityCenter: React.FC<SystemReliabilityCenterProps> = ({
  onBackToDashboard,
}) => {
  const [activeTab, setActiveTab] = useState<'subsystems' | 'database' | 'errors' | 'export'>('subsystems');
  const [healthData, setHealthData] = useState<SystemHealthSummary | null>(null);
  const [resourceMetrics, setResourceMetrics] = useState<ConcurrencyMetrics | null>(null);
  const [databaseStatus, setDatabaseStatus] = useState<DatabaseStatus | null>(null);
  const [recentErrors, setRecentErrors] = useState<RecentErrorItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  const fetchAllData = useCallback(async () => {
    try {
      setLoading(true);
      const [health, resources, dbStatus, errors] = await Promise.allSettled([
        apiService.getDetailedHealth(),
        apiService.getResourceMetrics(),
        apiService.getDatabaseStatus(),
        apiService.getRecentErrors(50),
      ]);

      if (health.status === 'fulfilled') setHealthData(health.value);
      if (resources.status === 'fulfilled') setResourceMetrics(resources.value);
      if (dbStatus.status === 'fulfilled') setDatabaseStatus(dbStatus.value);
      if (errors.status === 'fulfilled') setRecentErrors(errors.value);

      setLastRefreshed(new Date());
    } catch (err) {
      console.error('Failed to refresh reliability telemetry:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  // Periodic polling (15s interval, suspended when window is inactive)
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchAllData();
      }
    }, 15000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchAllData]);

  const overallState = healthData?.overall_status || 'UNKNOWN';
  const isHealthy = overallState === 'HEALTHY';
  const isDegraded = overallState === 'DEGRADED';
  const isError = overallState === 'ERROR';

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 overflow-y-auto">
      {/* Top Banner & Navigation */}
      <div className="p-6 border-b border-slate-800 bg-slate-900/40 backdrop-blur-md sticky top-0 z-10">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            {onBackToDashboard && (
              <button
                onClick={onBackToDashboard}
                className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-slate-100 border border-slate-700 transition-colors"
                title="Return to Command Center"
              >
                <ArrowLeft className="w-4 h-4" />
              </button>
            )}
            <div className="p-2.5 rounded-xl bg-cyan-950/60 border border-cyan-800/60 shadow-lg shadow-cyan-950/50">
              <ShieldCheck className="w-6 h-6 text-cyan-400" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-xl font-bold tracking-tight text-slate-100">
                  System Reliability Center
                </h1>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold font-mono uppercase tracking-wider bg-cyan-950 text-cyan-300 border border-cyan-800">
                  NOVA v0.9
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Centralized supervisor, hardware concurrency governor, and SQLite durability console
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto justify-end">
            {/* Overall Status Badge */}
            <div
              className={`px-3 py-1.5 rounded-lg border flex items-center gap-2 text-xs font-semibold ${
                isHealthy
                  ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-300'
                  : isDegraded
                  ? 'bg-amber-950/40 border-amber-800/60 text-amber-300'
                  : isError
                  ? 'bg-rose-950/40 border-rose-800/60 text-rose-300'
                  : 'bg-slate-800 border-slate-700 text-slate-300'
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  isHealthy
                    ? 'bg-emerald-400 animate-pulse'
                    : isDegraded
                    ? 'bg-amber-400 animate-pulse'
                    : 'bg-rose-400 animate-pulse'
                }`}
              />
              System Status: {overallState}
            </div>

            {/* Auto refresh & manual trigger */}
            <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg text-xs text-slate-400">
              <label className="flex items-center gap-1.5 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="rounded border-slate-700 bg-slate-950 text-cyan-500 text-[10px]"
                />
                Auto (15s)
              </label>
              <span className="text-slate-700">|</span>
              <button
                onClick={fetchAllData}
                disabled={loading}
                className="hover:text-slate-100 flex items-center gap-1 transition-colors disabled:opacity-50"
                title={`Last updated: ${lastRefreshed.toLocaleTimeString()}`}
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
                <span>Refresh</span>
              </button>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-1 mt-5 border-b border-slate-800 -mb-6 overflow-x-auto">
          <button
            onClick={() => setActiveTab('subsystems')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
              activeTab === 'subsystems'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-950/20'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <Layers className="w-4 h-4" />
            Subsystems & Resources
          </button>

          <button
            onClick={() => setActiveTab('database')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
              activeTab === 'database'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-950/20'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <Database className="w-4 h-4" />
            Database & Backups
          </button>

          <button
            onClick={() => setActiveTab('errors')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
              activeTab === 'errors'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-950/20'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <AlertTriangle className="w-4 h-4" />
            Ring Buffer & Errors
            {recentErrors.length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-amber-950 text-amber-300 border border-amber-800">
                {recentErrors.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('export')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
              activeTab === 'export'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-950/20'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <FileText className="w-4 h-4" />
            Sanitized Diagnostics Export
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="p-6 space-y-6 flex-1 max-w-7xl w-full mx-auto">
        {activeTab === 'subsystems' && (
          <div className="space-y-6">
            <ResourceMonitor />
            {healthData && <SubsystemHealthGrid subsystems={healthData.subsystems} />}
          </div>
        )}

        {activeTab === 'database' && (
          <div className="space-y-6">
            <DatabaseHealthPanel />
            <BackupManager />
          </div>
        )}

        {activeTab === 'errors' && (
          <RecentErrorsPanel
            errors={recentErrors}
            isLoading={loading}
            onRefresh={fetchAllData}
          />
        )}

        {activeTab === 'export' && <DiagnosticExport />}
      </div>
    </div>
  );
};
