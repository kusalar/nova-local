import React, { useState, useRef, useEffect } from 'react';
import { 
  X, 
  Send, 
  Trash2, 
  Volume2, 
  VolumeX, 
  Cpu, 
  AlertTriangle, 
  Sparkles, 
  Terminal,
  Bot,
  User,
  RefreshCw
} from 'lucide-react';
import { ChatMessage, NovaState, AiStatusResponse } from '../../types';

interface ChatConsoleModalProps {
  isOpen: boolean;
  onClose: () => void;
  messages: ChatMessage[];
  isLoading: boolean;
  onSendMessage: (msg: string, model?: string) => void;
  onClearMessages: () => void;
  assistantState: NovaState;
  aiStatus: AiStatusResponse;
  onChangeModel: (model: string) => void;
  voiceEnabled: boolean;
  onToggleVoice: () => void;
}

export const ChatConsoleModal: React.FC<ChatConsoleModalProps> = ({
  isOpen,
  onClose,
  messages,
  isLoading,
  onSendMessage,
  onClearMessages,
  assistantState,
  aiStatus,
  onChangeModel,
  voiceEnabled,
  onToggleVoice,
}) => {
  const [inputText, setInputText] = useState('');
  const [selectedModel, setSelectedModel] = useState(aiStatus.active_model || 'qwen2.5:1.5b');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (aiStatus.active_model) {
      setSelectedModel(aiStatus.active_model);
    }
  }, [aiStatus.active_model]);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen, isLoading]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isLoading) return;
    onSendMessage(inputText.trim(), selectedModel);
    setInputText('');
  };

  const promptSuggestions = [
    'System diagnostic status report',
    'Summarize current mission timeline',
    'How do I run Qwen 2.5 on Ollama?',
    'Perform neural memory audit'
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div 
        className="hud-panel w-full max-w-3xl h-[85vh] flex flex-col overflow-hidden border-nova-cyan/40 shadow-nova-orb relative"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-nova-border bg-nova-dark/90">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-nova-surface border border-nova-cyan/50 flex items-center justify-center text-nova-cyan shadow-nova-cyan">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-display font-bold text-sm tracking-wider text-white">
                  NOVA AI CONSOLE
                </h2>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-nova-cyan/15 text-nova-cyan border border-nova-cyan/30">
                  {assistantState}
                </span>
              </div>
              <p className="text-[10px] font-mono text-nova-textDim">
                Neural Operational Virtual Assistant • Windows v0.1
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Model Selector */}
            <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-nova-surface border border-nova-border text-xs font-mono">
              <Cpu className="w-3.5 h-3.5 text-nova-cyan" />
              <select
                value={selectedModel}
                onChange={(e) => {
                  setSelectedModel(e.target.value);
                  onChangeModel(e.target.value);
                }}
                className="bg-transparent text-slate-200 text-xs focus:outline-none cursor-pointer"
              >
                {aiStatus.available_models.length > 0 ? (
                  aiStatus.available_models.map((m) => (
                    <option key={m} value={m} className="bg-nova-dark text-slate-200">
                      {m}
                    </option>
                  ))
                ) : (
                  <>
                    <option value="qwen2.5:1.5b" className="bg-nova-dark text-slate-200">
                      qwen2.5:1.5b (Default)
                    </option>
                    <option value="llama3.2:1b" className="bg-nova-dark text-slate-200">
                      llama3.2:1b
                    </option>
                    <option value="llama3:8b" className="bg-nova-dark text-slate-200">
                      llama3:8b
                    </option>
                  </>
                )}
              </select>
            </div>

            {/* Voice Toggle */}
            <button
              onClick={onToggleVoice}
              className={`p-2 rounded border transition-colors ${
                voiceEnabled 
                  ? 'bg-nova-cyan/20 border-nova-cyan text-nova-cyan' 
                  : 'bg-nova-surface border-nova-border text-slate-400'
              }`}
              title={voiceEnabled ? 'Vocal synthesis enabled' : 'Vocal synthesis muted'}
            >
              {voiceEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
            </button>

            {/* Clear History */}
            <button
              onClick={onClearMessages}
              className="p-2 rounded bg-nova-surface border border-nova-border text-slate-400 hover:text-rose-400 hover:border-rose-500/40 transition-colors"
              title="Clear conversation"
            >
              <Trash2 className="w-4 h-4" />
            </button>

            {/* Close */}
            <button
              onClick={onClose}
              className="p-2 rounded bg-nova-surface border border-nova-border text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Ollama Status Alert Banner if disconnected */}
        {!aiStatus.online && (
          <div className="flex items-center justify-between px-4 py-2 bg-amber-950/40 border-b border-amber-500/30 text-amber-300 text-xs font-mono">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
              <span>
                Ollama service is offline on {aiStatus.endpoint}. Start Ollama or run <code className="px-1 py-0.5 rounded bg-black/40 text-nova-cyan">ollama serve</code> to enable local AI inference.
              </span>
            </div>
            <button
              onClick={() => onChangeModel(selectedModel)}
              className="flex items-center gap-1 text-[11px] underline text-nova-cyan hover:text-white"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Retry</span>
            </button>
          </div>
        )}

        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-3">
              <div className="w-16 h-16 rounded-full bg-nova-surface border border-nova-cyan/40 shadow-nova-cyan flex items-center justify-center text-nova-cyan animate-pulse">
                <Sparkles className="w-8 h-8" />
              </div>
              <h3 className="font-display font-bold text-base text-white tracking-widest uppercase">
                NOVA NEURAL CHAT ONLINE
              </h3>
              <p className="text-xs text-slate-400 max-w-md font-mono">
                Directives sent here are dispatched to your local open-weight model in Ollama.
                All conversations are persistently stored in local SQLite memory.
              </p>
              
              {/* Quick suggestions */}
              <div className="flex flex-wrap gap-2 justify-center max-w-lg mt-3">
                {promptSuggestions.map((prompt, i) => (
                  <button
                    key={i}
                    onClick={() => onSendMessage(prompt, selectedModel)}
                    className="px-3 py-1.5 rounded-full bg-nova-surface/80 border border-nova-border/70 hover:border-nova-cyan text-xs text-slate-300 hover:text-nova-cyan transition-colors font-mono"
                  >
                    "{prompt}"
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, index) => {
              const isUser = msg.role === 'user';
              return (
                <div
                  key={index}
                  className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
                >
                  {!isUser && (
                    <div className="w-7 h-7 rounded bg-nova-surface border border-nova-cyan/40 flex items-center justify-center text-nova-cyan flex-shrink-0 mt-1">
                      <Bot className="w-4 h-4" />
                    </div>
                  )}

                  <div
                    className={`max-w-[80%] rounded-lg p-3 text-xs leading-relaxed ${
                      isUser
                        ? 'bg-nova-electric/25 border border-nova-electric/50 text-slate-100'
                        : 'bg-nova-surface/90 border border-nova-border text-slate-200'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3 mb-1 text-[9px] font-mono text-nova-textDim">
                      <span>{isUser ? 'Commander' : `NOVA (${msg.model || selectedModel})`}</span>
                      <span>{msg.timestamp || 'Just now'}</span>
                    </div>

                    <div className="whitespace-pre-wrap font-sans text-sm selection:bg-nova-cyan/30">
                      {msg.content}
                    </div>
                  </div>

                  {isUser && (
                    <div className="w-7 h-7 rounded bg-nova-electric/30 border border-nova-electric flex items-center justify-center text-white flex-shrink-0 mt-1">
                      <User className="w-4 h-4" />
                    </div>
                  )}
                </div>
              );
            })
          )}

          {/* Thinking Indicator */}
          {isLoading && (
            <div className="flex items-center gap-3">
              <div className="w-7 h-7 rounded bg-nova-surface border border-nova-cyan/40 flex items-center justify-center text-nova-cyan animate-spin">
                <RefreshCw className="w-4 h-4" />
              </div>
              <div className="px-3 py-2 rounded-lg bg-nova-surface border border-nova-border text-xs font-mono text-nova-cyan flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-nova-cyan animate-ping" />
                <span>PROCESSING NEURAL INFERENCE...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <form 
          onSubmit={handleSubmit}
          className="p-3 border-t border-nova-border bg-nova-dark/95 flex items-center gap-2"
        >
          <div className="relative flex-1">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Enter directive or ask NOVA a question..."
              className="w-full px-4 py-2.5 rounded-md bg-nova-surface border border-nova-border text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-nova-cyan focus:shadow-nova-cyan transition-all font-mono"
              disabled={isLoading}
            />
          </div>

          <button
            type="submit"
            disabled={!inputText.trim() || isLoading}
            className={`px-4 py-2.5 rounded-md flex items-center gap-2 font-display font-bold text-xs tracking-wider uppercase transition-all ${
              inputText.trim() && !isLoading
                ? 'bg-nova-cyan text-nova-dark hover:bg-white shadow-nova-cyan'
                : 'bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed'
            }`}
          >
            <span>Transmit</span>
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>
    </div>
  );
};
