import React, { useState } from 'react';
import { 
  Camera, 
  Monitor, 
  AppWindow, 
  Maximize2, 
  RefreshCw, 
  FileText, 
  HardDrive,
  Eye,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { CaptureMetadata, CaptureTarget, ImageFormat } from '../../types';

interface ScreenPreviewPanelProps {
  capture: CaptureMetadata | null;
  isCapturing: boolean;
  onCapture: (target: CaptureTarget, monitorIndex?: number, format?: ImageFormat) => void;
  monitorsCount: number;
}

export const ScreenPreviewPanel: React.FC<ScreenPreviewPanelProps> = ({
  capture,
  isCapturing,
  onCapture,
  monitorsCount
}) => {
  const [selectedTarget, setSelectedTarget] = useState<CaptureTarget>('PRIMARY');
  const [selectedMonitor, setSelectedMonitor] = useState<number>(0);
  const [format, setFormat] = useState<ImageFormat>('PNG');

  const handleCaptureClick = () => {
    onCapture(
      selectedTarget,
      selectedTarget === 'MONITOR_INDEX' ? selectedMonitor : undefined,
      format
    );
  };

  return (
    <div className="bg-nova-surface/70 border border-nova-border/70 rounded-lg p-4 flex flex-col h-full shadow-[0_4px_20px_rgba(0,0,0,0.3)]">
      {/* Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-nova-border/50">
        <div className="flex items-center gap-2">
          <Camera className="w-4 h-4 text-nova-cyan" />
          <span className="text-xs font-semibold font-display tracking-wider text-slate-200">
            OPTICAL ACQUISITION
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Target Selector */}
          <select
            value={selectedTarget}
            onChange={(e) => setSelectedTarget(e.target.value as CaptureTarget)}
            className="bg-nova-dark/80 border border-nova-border/80 rounded px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-nova-cyan font-mono"
          >
            <option value="PRIMARY">Primary Screen</option>
            <option value="ACTIVE_WINDOW">Active Window</option>
            <option value="ALL_MONITORS">All Displays ({monitorsCount})</option>
            {monitorsCount > 1 && <option value="MONITOR_INDEX">Select Monitor...</option>}
          </select>

          {selectedTarget === 'MONITOR_INDEX' && (
            <select
              value={selectedMonitor}
              onChange={(e) => setSelectedMonitor(Number(e.target.value))}
              className="bg-nova-dark/80 border border-nova-border/80 rounded px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-nova-cyan font-mono"
            >
              {Array.from({ length: monitorsCount }).map((_, i) => (
                <option key={i} value={i}>Display #{i + 1}</option>
              ))}
            </select>
          )}

          {/* Format Selector */}
          <select
            value={format}
            onChange={(e) => setFormat(e.target.value as ImageFormat)}
            className="bg-nova-dark/80 border border-nova-border/80 rounded px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-nova-cyan font-mono"
          >
            <option value="PNG">PNG (Lossless)</option>
            <option value="JPEG">JPEG (Compressed)</option>
          </select>

          {/* Trigger Button */}
          <button
            onClick={handleCaptureClick}
            disabled={isCapturing}
            className="flex items-center gap-1.5 px-3 py-1 bg-nova-cyan/20 hover:bg-nova-cyan/30 text-nova-cyan border border-nova-cyan/50 rounded text-xs font-medium tracking-wide transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isCapturing ? 'animate-spin' : ''}`} />
            <span>{isCapturing ? 'Capturing...' : 'Capture Now'}</span>
          </button>
        </div>
      </div>

      {/* Preview Area */}
      <div className="flex-1 min-h-[300px] mt-3 bg-nova-dark/60 border border-nova-border/50 rounded flex flex-col items-center justify-center relative overflow-hidden group">
        {capture?.base64_preview ? (
          <div className="w-full h-full flex flex-col items-center justify-center p-2 relative">
            <img
              src={capture.base64_preview}
              alt="Screen Preview"
              className="max-h-[340px] max-w-full object-contain rounded border border-nova-border/30 shadow-md"
            />
            {/* Metadata overlay on hover */}
            <div className="absolute bottom-3 left-3 right-3 bg-nova-dark/90 backdrop-blur-md border border-nova-border/80 rounded p-2 text-[11px] text-slate-300 flex items-center justify-between font-mono">
              <div className="flex items-center gap-3">
                <span>Res: <strong className="text-nova-cyan">{capture.width}x{capture.height}</strong></span>
                <span>Orig: {capture.original_width}x{capture.original_height}</span>
                <span>Size: {(capture.file_size_bytes / 1024).toFixed(1)} KB</span>
              </div>
              <div className="text-slate-400">
                {new Date(capture.timestamp).toLocaleTimeString()}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center p-6 text-center text-slate-400">
            <Monitor className="w-12 h-12 text-slate-600 mb-2 stroke-[1.5]" />
            <p className="text-xs font-medium text-slate-300">No Active Screen Capture</p>
            <p className="text-[11px] text-slate-500 max-w-xs mt-1">
              Select a target above and click "Capture Now" or ask NOVA via voice to inspect your desktop.
            </p>
          </div>
        )}
      </div>

      {/* Target details footer */}
      {capture && (
        <div className="mt-3 pt-2 border-t border-nova-border/40 flex items-center justify-between text-[11px] text-slate-400 font-mono">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Target: <strong className="text-slate-200">{capture.target}</strong></span>
          </div>
          {capture.window_info && (
            <div className="truncate max-w-[280px]">
              Active: <strong className="text-slate-200">{capture.window_info.app_name}</strong> - "{capture.window_info.title}"
            </div>
          )}
        </div>
      )}
    </div>
  );
};
