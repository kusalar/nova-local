import React, { useState, useEffect, useCallback } from 'react';
import { 
  Eye, 
  ArrowLeft, 
  Settings, 
  Trash2, 
  RefreshCw, 
  ShieldCheck, 
  Monitor, 
  Sparkles,
  Layers,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { ScreenPreviewPanel } from './ScreenPreviewPanel';
import { WindowAwarenessPanel } from './WindowAwarenessPanel';
import { OcrTextPanel } from './OcrTextPanel';
import { VisualQueryPanel } from './VisualQueryPanel';
import { VisionSettingsModal } from './VisionSettingsModal';
import { apiService } from '../../services/api';
import { 
  VisionStatus, 
  WindowInfo, 
  CaptureMetadata, 
  OcrResult, 
  VisualAnalysisResponse, 
  CaptureTarget, 
  ImageFormat,
  VisionSettings
} from '../../types';

interface VisionCenterProps {
  onBackToDashboard: () => void;
  onSpeakText?: (text: string) => void;
}

export const VisionCenter: React.FC<VisionCenterProps> = ({ 
  onBackToDashboard,
  onSpeakText
}) => {
  // Vision Status & Data
  const [visionStatus, setVisionStatus] = useState<VisionStatus | null>(null);
  const [windows, setWindows] = useState<WindowInfo[]>([]);
  const [currentCapture, setCurrentCapture] = useState<CaptureMetadata | null>(null);
  const [currentOcr, setCurrentOcr] = useState<OcrResult | null>(null);
  const [lastAnalysis, setLastAnalysis] = useState<VisualAnalysisResponse | null>(null);

  // Loading States
  const [isLoadingStatus, setIsLoadingStatus] = useState(false);
  const [isCapturing, setIsCapturing] = useState(false);
  const [isLoadingWindows, setIsLoadingWindows] = useState(false);
  const [isLoadingOcr, setIsLoadingOcr] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Settings Modal & Notification
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [notification, setNotification] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showNotification = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

  // Load Vision Status & Windows
  const loadStatus = useCallback(async () => {
    try {
      setIsLoadingStatus(true);
      const status = await apiService.getVisionStatus();
      setVisionStatus(status);
    } catch (err: any) {
      showNotification(`Failed to load vision status: ${err.message}`, 'error');
    } finally {
      setIsLoadingStatus(false);
    }
  }, []);

  const loadWindows = useCallback(async () => {
    try {
      setIsLoadingWindows(true);
      const wins = await apiService.listDesktopWindows();
      setWindows(wins);
    } catch (err: any) {
      showNotification(`Failed to enumerate windows: ${err.message}`, 'error');
    } finally {
      setIsLoadingWindows(false);
    }
  }, []);

  useEffect(() => {
    loadStatus();
    loadWindows();
  }, [loadStatus, loadWindows]);

  // Actions
  const handleCapture = async (target: CaptureTarget, monitorIndex?: number, format: ImageFormat = 'PNG') => {
    try {
      setIsCapturing(true);
      const meta = await apiService.captureScreen(target, monitorIndex, format);
      setCurrentCapture(meta);
      setCurrentOcr(null); // Reset OCR for new capture
      loadStatus();
      loadWindows();
      showNotification(`Captured ${target} (${meta.width}x${meta.height})`, 'success');
    } catch (err: any) {
      showNotification(`Capture failed: ${err.message}`, 'error');
    } finally {
      setIsCapturing(false);
    }
  };

  const handleRunOcr = async () => {
    try {
      setIsLoadingOcr(true);
      const ocrRes = await apiService.extractOcr(currentCapture?.capture_id);
      setCurrentOcr(ocrRes);
      showNotification(`OCR completed: ${ocrRes.total_words} words extracted in ${ocrRes.duration_ms}ms.`, 'success');
    } catch (err: any) {
      showNotification(`OCR extraction failed: ${err.message}`, 'error');
    } finally {
      setIsLoadingOcr(false);
    }
  };

  const handleAnalyze = async (prompt: string, target: CaptureTarget) => {
    try {
      setIsAnalyzing(true);
      const response = await apiService.analyzeScreen({
        prompt,
        capture_target: target,
        use_existing_capture_id: currentCapture?.capture_id,
        include_ocr: true
      });
      setLastAnalysis(response);
      if (response.capture_metadata) {
        setCurrentCapture(response.capture_metadata);
      }
      if (response.ocr_result) {
        setCurrentOcr(response.ocr_result);
      }
      loadStatus();
      showNotification(`Analysis completed (${response.duration_ms}ms).`, 'success');
    } catch (err: any) {
      showNotification(`Analysis failed: ${err.message}`, 'error');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleClearTemporaryCaptures = async () => {
    try {
      const res = await apiService.clearTemporaryCaptures();
      setCurrentCapture(null);
      setCurrentOcr(null);
      setLastAnalysis(null);
      loadStatus();
      showNotification(`Purged ${res.cleared_count} ephemeral capture(s) from disk.`, 'success');
    } catch (err: any) {
      showNotification(`Failed to clear captures: ${err.message}`, 'error');
    }
  };

  const handleSaveSettings = async (updates: Partial<VisionSettings>) => {
    try {
      const updated = await apiService.updateVisionSettings(updates);
      if (visionStatus) {
        setVisionStatus({ ...visionStatus, settings: updated });
      }
      showNotification('Vision settings saved.', 'success');
    } catch (err: any) {
      showNotification(`Failed to update settings: ${err.message}`, 'error');
    }
  };

  return (
    <div className="flex-1 flex flex-col h-[calc(100vh-65px)] overflow-hidden bg-nova-dark/95 select-none p-4 relative">
      {/* Top Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-nova-border/70">
        <div className="flex items-center gap-3">
          <button
            onClick={onBackToDashboard}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-nova-surface/60 hover:bg-nova-surface border border-nova-border/70 text-slate-300 hover:text-nova-cyan text-xs font-semibold tracking-wider transition-all"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="font-display">DASHBOARD</span>
          </button>

          <div className="flex items-center gap-2">
            <Eye className="w-5 h-5 text-nova-cyan" />
            <h2 className="text-sm font-bold font-display tracking-wider text-slate-100 uppercase">
              VISION CENTER // MULTIMODAL SCREEN AWARENESS
            </h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-nova-cyan/20 text-nova-cyan border border-nova-cyan/40">
              v0.5
            </span>
          </div>
        </div>

        {/* Global Status Badges & Controls */}
        <div className="flex items-center gap-2 text-xs font-mono">
          {/* Active Engine Badge */}
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded bg-nova-surface/60 border border-nova-border/60 text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>{visionStatus?.active_engine || 'WINDOWS_MEDIA_OCR'}</span>
          </div>

          {/* Monitors Badge */}
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded bg-nova-surface/60 border border-nova-border/60 text-slate-300">
            <Monitor className="w-3.5 h-3.5 text-nova-cyan" />
            <span>{visionStatus?.monitors_count || 1} Display(s)</span>
          </div>

          {/* Purge Temporary Screenshots */}
          <button
            onClick={handleClearTemporaryCaptures}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-300 text-xs transition-colors"
            title="Purge all temporary screenshots from disk"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear Captures ({visionStatus?.temporary_captures_count || 0})</span>
          </button>

          {/* Settings Button */}
          <button
            onClick={() => setIsSettingsOpen(true)}
            className="p-1.5 rounded bg-nova-surface/60 hover:bg-nova-surface border border-nova-border/70 text-slate-300 hover:text-nova-cyan transition-colors"
            title="Vision Privacy & Capture Settings"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Notification Toast */}
      {notification && (
        <div className={`absolute top-16 right-6 z-50 px-3.5 py-2 rounded-md border text-xs font-mono shadow-xl flex items-center gap-2 animate-in fade-in slide-in-from-top-2 duration-150 ${
          notification.type === 'error'
            ? 'bg-rose-950/90 border-rose-500 text-rose-200'
            : notification.type === 'success'
            ? 'bg-emerald-950/90 border-emerald-500 text-emerald-200'
            : 'bg-nova-surface/90 border-nova-cyan text-slate-200'
        }`}>
          {notification.type === 'error' ? <AlertCircle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
          <span>{notification.message}</span>
        </div>
      )}

      {/* Main 2-Column Split Workspace */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-3.5 mt-3.5 min-h-0 overflow-y-auto custom-scrollbar">
        {/* Left Column (5 cols): Screen Preview & Window Awareness */}
        <div className="lg:col-span-5 flex flex-col gap-3.5 min-h-0">
          <div className="flex-1 min-h-[360px]">
            <ScreenPreviewPanel
              capture={currentCapture}
              isCapturing={isCapturing}
              onCapture={handleCapture}
              monitorsCount={visionStatus?.monitors_count || 1}
            />
          </div>
          <div className="flex-1 min-h-[300px]">
            <WindowAwarenessPanel
              activeWindow={visionStatus?.active_window || null}
              windows={windows}
              isLoading={isLoadingWindows}
              onRefresh={loadWindows}
            />
          </div>
        </div>

        {/* Right Column (7 cols): Visual Q&A & OCR Text Explorer */}
        <div className="lg:col-span-7 flex flex-col gap-3.5 min-h-0">
          <div className="flex-1 min-h-[340px]">
            <VisualQueryPanel
              onAnalyze={handleAnalyze}
              isAnalyzing={isAnalyzing}
              lastAnalysis={lastAnalysis}
              onSpeakText={onSpeakText}
            />
          </div>
          <div className="flex-1 min-h-[320px]">
            <OcrTextPanel
              ocrResult={currentOcr}
              isLoading={isLoadingOcr}
              onRunOcr={handleRunOcr}
            />
          </div>
        </div>
      </div>

      {/* Settings Modal */}
      {visionStatus?.settings && (
        <VisionSettingsModal
          isOpen={isSettingsOpen}
          onClose={() => setIsSettingsOpen(false)}
          settings={visionStatus.settings}
          onSave={handleSaveSettings}
          onClearCaptures={handleClearTemporaryCaptures}
          temporaryCount={visionStatus.temporary_captures_count}
        />
      )}
    </div>
  );
};
