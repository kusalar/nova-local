import React, { useState } from 'react';
import { 
  HelpCircle, 
  Send, 
  Sparkles, 
  CheckCircle2, 
  Volume2, 
  Layers, 
  Clock, 
  Bot,
  BrainCircuit,
  Terminal
} from 'lucide-react';
import { VisualAnalysisResponse, CaptureTarget } from '../../types';

interface VisualQueryPanelProps {
  onAnalyze: (prompt: string, target: CaptureTarget) => void;
  isAnalyzing: boolean;
  lastAnalysis: VisualAnalysisResponse | null;
  onSpeakText?: (text: string) => void;
}

const QUICK_PROMPTS = [
  "What is currently open on my screen?",
  "Read the error message.",
  "What does this dialog box say?",
  "Summarize the visible content.",
  "Which application am I using?",
  "Can you explain this code?",
  "What is wrong with this screenshot?"
];

export const VisualQueryPanel: React.FC<VisualQueryPanelProps> = ({
  onAnalyze,
  isAnalyzing,
  lastAnalysis,
  onSpeakText
}) => {
  const [prompt, setPrompt] = useState('');
  const [target, setTarget] = useState<CaptureTarget>('PRIMARY');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isAnalyzing) return;
    onAnalyze(prompt.trim(), target);
  };

  const handleQuickPromptClick = (qp: string) => {
    setPrompt(qp);
    onAnalyze(qp, target);
  };

  return (
    <div className="bg-nova-surface/70 border border-nova-border/70 rounded-lg p-4 flex flex-col h-full shadow-[0_4px_20px_rgba(0,0,0,0.3)]">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-nova-border/50">
        <div className="flex items-center gap-2">
          <BrainCircuit className="w-4 h-4 text-nova-cyan" />
          <span className="text-xs font-semibold font-display tracking-wider text-slate-200">
            VISUAL QUESTION ANSWERING
          </span>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={target}
            onChange={(e) => setTarget(e.target.value as CaptureTarget)}
            className="bg-nova-dark/80 border border-nova-border/80 rounded px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-nova-cyan font-mono"
          >
            <option value="PRIMARY">Target: Primary Screen</option>
            <option value="ACTIVE_WINDOW">Target: Active Window</option>
          </select>
        </div>
      </div>

      {/* Quick Prompts Carousel */}
      <div className="mt-3 flex items-center gap-1.5 overflow-x-auto pb-1.5 custom-scrollbar">
        {QUICK_PROMPTS.map((qp, idx) => (
          <button
            key={idx}
            onClick={() => handleQuickPromptClick(qp)}
            disabled={isAnalyzing}
            className="whitespace-nowrap px-2.5 py-1 bg-nova-dark/80 hover:bg-nova-cyan/20 border border-nova-border/60 hover:border-nova-cyan/40 text-[11px] font-mono text-slate-300 rounded transition-all disabled:opacity-50"
          >
            {qp}
          </button>
        ))}
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="mt-2.5 flex items-center gap-2">
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Ask a visual question about your desktop..."
          className="flex-1 bg-nova-dark/80 border border-nova-border/80 rounded px-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-nova-cyan font-mono"
        />
        <button
          type="submit"
          disabled={!prompt.trim() || isAnalyzing}
          className="flex items-center gap-1.5 px-4 py-2 bg-nova-cyan/20 hover:bg-nova-cyan/30 text-nova-cyan border border-nova-cyan/50 rounded text-xs font-semibold tracking-wide transition-all disabled:opacity-50"
        >
          <Send className={`w-3.5 h-3.5 ${isAnalyzing ? 'animate-pulse' : ''}`} />
          <span>{isAnalyzing ? 'Thinking...' : 'Analyze'}</span>
        </button>
      </form>

      {/* Answer Output Card */}
      <div className="flex-1 min-h-[220px] mt-3 bg-nova-dark/80 border border-nova-border/60 rounded p-3 overflow-y-auto flex flex-col justify-between custom-scrollbar select-text">
        {lastAnalysis ? (
          <div>
            {/* Header tags */}
            <div className="flex flex-wrap items-center justify-between gap-2 pb-2 mb-2 border-b border-nova-border/40 text-[11px] font-mono">
              <div className="flex items-center gap-2 text-nova-cyan">
                <Bot className="w-3.5 h-3.5" />
                <span>Model: {lastAnalysis.model_used}</span>
                <span>•</span>
                <span className="text-slate-400">{lastAnalysis.vision_mode}</span>
              </div>
              <div className="flex items-center gap-3 text-slate-400">
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" /> {lastAnalysis.duration_ms} ms
                </span>
                {onSpeakText && (
                  <button
                    onClick={() => onSpeakText(lastAnalysis.answer)}
                    className="p-1 hover:text-nova-cyan text-slate-400 transition-colors"
                    title="Speak answer via Piper TTS"
                  >
                    <Volume2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

            {/* Answer Text */}
            <div className="text-xs text-slate-100 whitespace-pre-wrap leading-relaxed select-text font-sans">
              {lastAnalysis.answer}
            </div>

            {/* Project Context Badge */}
            {lastAnalysis.project_context && (
              <div className="mt-3 p-2 bg-nova-cyan/10 border border-nova-cyan/30 rounded text-[11px] font-mono text-nova-cyan">
                <div className="font-semibold flex items-center gap-1 mb-1">
                  <Layers className="w-3 h-3" /> Associated Project Memory Correlated:
                </div>
                <div className="text-slate-300 text-[10px] whitespace-pre-wrap">
                  {lastAnalysis.project_context}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 py-6">
            <Sparkles className="w-8 h-8 text-slate-600 mb-2" />
            <p className="text-xs">Visual Neural Intelligence Ready</p>
            <p className="text-[11px] text-slate-600 max-w-sm mt-0.5">
              Ask anything about what is currently open on your screen. NOVA will inspect active windows, perform local OCR, and answer grounded in context.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
