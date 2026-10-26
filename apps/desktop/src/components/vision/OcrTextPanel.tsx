import React, { useState } from 'react';
import { 
  FileText, 
  Copy, 
  Check, 
  ShieldCheck, 
  Clock, 
  Search,
  Hash,
  Sparkles
} from 'lucide-react';
import { OcrResult } from '../../types';

interface OcrTextPanelProps {
  ocrResult: OcrResult | null;
  isLoading: boolean;
  onRunOcr: () => void;
}

export const OcrTextPanel: React.FC<OcrTextPanelProps> = ({
  ocrResult,
  isLoading,
  onRunOcr
}) => {
  const [copied, setCopied] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'formatted' | 'lines'>('formatted');

  const handleCopy = () => {
    if (!ocrResult?.full_text) return;
    navigator.clipboard.writeText(ocrResult.full_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const filteredLines = ocrResult?.lines.filter(l => 
    !searchQuery || l.text.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  return (
    <div className="bg-nova-surface/70 border border-nova-border/70 rounded-lg p-4 flex flex-col h-full shadow-[0_4px_20px_rgba(0,0,0,0.3)]">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-nova-border/50">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-nova-cyan" />
          <span className="text-xs font-semibold font-display tracking-wider text-slate-200">
            LOCAL OCR TEXT INTELLIGENCE
          </span>
        </div>

        <div className="flex items-center gap-2">
          {ocrResult && (
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 text-[11px] font-mono text-slate-300 hover:text-nova-cyan px-2 py-0.5 rounded bg-nova-dark/60 border border-nova-border/60 transition-colors"
            >
              {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
              <span>{copied ? 'Copied' : 'Copy Text'}</span>
            </button>
          )}

          <button
            onClick={onRunOcr}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-2.5 py-1 bg-nova-cyan/20 hover:bg-nova-cyan/30 text-nova-cyan border border-nova-cyan/50 rounded text-xs font-medium tracking-wide transition-all disabled:opacity-50"
          >
            <span>{isLoading ? 'Extracting...' : 'Extract OCR'}</span>
          </button>
        </div>
      </div>

      {/* Stats Ribbon */}
      {ocrResult && (
        <div className="grid grid-cols-4 gap-2 mt-3 p-2 bg-nova-dark/80 border border-nova-border/60 rounded text-[11px] font-mono">
          <div className="text-center border-r border-nova-border/40">
            <span className="text-slate-500 block text-[10px]">WORDS</span>
            <strong className="text-slate-200">{ocrResult.total_words}</strong>
          </div>
          <div className="text-center border-r border-nova-border/40">
            <span className="text-slate-500 block text-[10px]">LINES</span>
            <strong className="text-slate-200">{ocrResult.total_lines}</strong>
          </div>
          <div className="text-center border-r border-nova-border/40">
            <span className="text-slate-500 block text-[10px]">SPEED</span>
            <strong className="text-nova-cyan">{ocrResult.duration_ms} ms</strong>
          </div>
          <div className="text-center">
            <span className="text-slate-500 block text-[10px]">REDACTED</span>
            <strong className={ocrResult.redacted_count > 0 ? "text-amber-400" : "text-emerald-400"}>
              {ocrResult.redacted_count}
            </strong>
          </div>
        </div>
      )}

      {/* Filter and View Mode */}
      {ocrResult && (
        <div className="flex items-center justify-between gap-2 mt-2">
          <div className="relative flex-1">
            <Search className="w-3 h-3 text-slate-500 absolute left-2 top-2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter extracted words..."
              className="w-full bg-nova-dark/70 border border-nova-border/60 rounded pl-7 pr-2 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-nova-cyan font-mono"
            />
          </div>
          <div className="flex items-center gap-1 bg-nova-dark/60 border border-nova-border/60 rounded p-0.5 text-[10px] font-mono">
            <button
              onClick={() => setViewMode('formatted')}
              className={`px-2 py-0.5 rounded ${viewMode === 'formatted' ? 'bg-nova-cyan/20 text-nova-cyan' : 'text-slate-400'}`}
            >
              Paragraphs
            </button>
            <button
              onClick={() => setViewMode('lines')}
              className={`px-2 py-0.5 rounded ${viewMode === 'lines' ? 'bg-nova-cyan/20 text-nova-cyan' : 'text-slate-400'}`}
            >
              Boxes ({filteredLines.length})
            </button>
          </div>
        </div>
      )}

      {/* Content Area */}
      <div className="flex-1 min-h-[220px] mt-2 bg-nova-dark/60 border border-nova-border/50 rounded p-3 overflow-y-auto font-mono text-xs text-slate-200 custom-scrollbar select-text">
        {ocrResult ? (
          viewMode === 'formatted' ? (
            <div className="whitespace-pre-wrap leading-relaxed select-text">
              {ocrResult.full_text || '[No text extracted]'}
            </div>
          ) : (
            <div className="space-y-1.5">
              {filteredLines.map((l, i) => (
                <div key={i} className="p-1.5 bg-nova-dark/80 border border-nova-border/40 rounded flex items-start justify-between gap-2">
                  <span className="text-slate-100 flex-1">{l.text}</span>
                  <span className="text-[10px] text-slate-500 whitespace-nowrap">
                    [{l.x}, {l.y}, {l.width}x{l.height}]
                  </span>
                </div>
              ))}
            </div>
          )
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center text-slate-500">
            <Sparkles className="w-8 h-8 text-slate-600 mb-2" />
            <p className="text-xs">OCR Analysis Idle</p>
            <p className="text-[11px] text-slate-600 mt-0.5">
              Run capture or click "Extract OCR" to read on-screen text locally.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
