import React, { useState } from 'react';
import { Download, ShieldCheck, Copy, Check, FileText } from 'lucide-react';
import { apiService } from '../../services/api';

export const DiagnosticExport: React.FC = () => {
  const [includeLogs, setIncludeLogs] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [copied, setCopied] = useState(false);
  const [lastExport, setLastExport] = useState<any | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const handleExport = async (format: 'download' | 'copy') => {
    try {
      setIsExporting(true);
      setStatusMessage(null);
      const data = await apiService.exportDiagnostics(includeLogs);
      setLastExport(data);

      const jsonString = JSON.stringify(data, null, 2);

      if (format === 'copy') {
        await navigator.clipboard.writeText(jsonString);
        setCopied(true);
        setTimeout(() => setCopied(false), 2500);
        setStatusMessage('Sanitized diagnostic bundle copied to clipboard.');
      } else {
        const blob = new Blob([jsonString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `nova-diagnostics-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        setStatusMessage('Diagnostic package downloaded successfully.');
      }
    } catch (err: any) {
      setStatusMessage(`Export failed: ${err.message || 'Unknown error'}`);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-sm">
      <div className="flex items-center gap-2 mb-2">
        <FileText className="w-5 h-5 text-cyan-400" />
        <h3 className="text-base font-semibold text-slate-100">Sanitized Diagnostic Export</h3>
      </div>
      <p className="text-xs text-slate-400 mb-4">
        Generate an anonymized JSON snapshot of NOVA's runtime health, resource metrics, database status, and subsystem states.
      </p>

      {/* Privacy Guarantee Box */}
      <div className="p-3.5 mb-5 rounded-lg bg-emerald-950/20 border border-emerald-900/50 flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-300">
          <span className="font-semibold text-emerald-300">Privacy & Redaction Guarantee: </span>
          All API keys, tokens, session IDs, private memory contents, raw audio transcripts, and sensitive Windows user paths (e.g. usernames, home directories) are automatically stripped and defanged before export.
        </div>
      </div>

      {/* Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 py-3 border-t border-b border-slate-800">
        <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-slate-100 select-none">
          <input
            type="checkbox"
            checked={includeLogs}
            onChange={(e) => setIncludeLogs(e.target.checked)}
            className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-0 focus:ring-offset-0"
          />
          Include recent error ring buffer entries (anonymized)
        </label>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <button
            onClick={() => handleExport('copy')}
            disabled={isExporting}
            className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors disabled:opacity-50"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? 'Copied!' : 'Copy JSON'}
          </button>

          <button
            onClick={() => handleExport('download')}
            disabled={isExporting}
            className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-medium bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg shadow-cyan-900/30 transition-colors disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5" />
            {isExporting ? 'Generating...' : 'Download Export'}
          </button>
        </div>
      </div>

      {statusMessage && (
        <div className="mt-3 text-xs text-cyan-300 font-mono bg-cyan-950/30 p-2 rounded border border-cyan-800/40">
          {statusMessage}
        </div>
      )}

      {/* Preview Summary */}
      {lastExport && (
        <div className="mt-4 pt-3 border-t border-slate-800/60">
          <h4 className="text-xs font-semibold text-slate-400 mb-2">Snapshot Metadata Preview</h4>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono">
            <div className="p-2 bg-slate-950/60 rounded border border-slate-800">
              <span className="text-slate-500 block">Version</span>
              <span className="text-slate-200">{lastExport.app_version}</span>
            </div>
            <div className="p-2 bg-slate-950/60 rounded border border-slate-800">
              <span className="text-slate-500 block">Subsystems</span>
              <span className="text-slate-200">{lastExport.subsystems_count || 10}</span>
            </div>
            <div className="p-2 bg-slate-950/60 rounded border border-slate-800">
              <span className="text-slate-500 block">Sanitized</span>
              <span className="text-emerald-400">{String(lastExport.redacted_for_privacy)}</span>
            </div>
            <div className="p-2 bg-slate-950/60 rounded border border-slate-800">
              <span className="text-slate-500 block">Timestamp</span>
              <span className="text-slate-200">
                {new Date(lastExport.timestamp).toLocaleTimeString()}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
