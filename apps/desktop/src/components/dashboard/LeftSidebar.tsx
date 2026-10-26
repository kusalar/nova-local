import React from 'react';
import { 
  LayoutDashboard, 
  Cpu, 
  Bot, 
  CheckSquare, 
  Calendar, 
  Database, 
  MessageSquare, 
  BookOpen, 
  Wrench, 
  GitFork,
  Mic,
  Crosshair,
  Radio,
  Eye,
  Zap,
  BrainCircuit,
  ShieldCheck
} from 'lucide-react';
import { WaveformVisualizer } from '../common/WaveformVisualizer';
import { NovaState } from '../../types';

interface LeftSidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  assistantState: NovaState;
  onMicClick: () => void;
  onOpenChat: () => void;
  focusMode: boolean;
  setFocusMode: (val: boolean) => void;
  isVoiceRunning?: boolean;
  wakeWordEnabled?: boolean;
  activeWakePhrase?: string;
  audioLevel?: number;
}

export const LeftSidebar: React.FC<LeftSidebarProps> = ({
  activeTab,
  setActiveTab,
  assistantState,
  onMicClick,
  onOpenChat,
  focusMode,
  setFocusMode,
  isVoiceRunning = true,
  wakeWordEnabled = true,
  activeWakePhrase = 'Hey Jarvis',
  audioLevel = 0
}) => {
interface NavItem {
  id: string;
  label: string;
  icon: any;
  badge?: string | number;
}

const navItems: NavItem[] = [
  { id: 'command-center', label: 'Command Center', icon: LayoutDashboard },
  { id: 'operations', label: 'Operations & Tools', icon: Wrench },
  { id: 'vision', label: 'Vision Intelligence', icon: Eye },
  { id: 'agents', label: 'Agents & Workflows', icon: Bot },
  { id: 'automations', label: 'Automations & Routines', icon: Zap },
  { id: 'personalization', label: 'Personalization', icon: BrainCircuit },
  { id: 'memory', label: 'Memory & Knowledge', icon: Database },
  { id: 'reliability', label: 'System Reliability', icon: ShieldCheck },
  { id: 'conversations', label: 'Conversations', icon: MessageSquare },
];

  const isListening = assistantState === 'LISTENING';
  const isSpeaking = assistantState === 'SPEAKING';
  const isThinking = assistantState === 'THINKING';

  return (
    <aside className="w-56 flex-shrink-0 flex flex-col justify-between h-[calc(100vh-65px)] border-r border-nova-border/70 bg-nova-dark/80 backdrop-blur-md p-3 select-none">
      {/* Navigation List */}
      <nav className="space-y-1 overflow-y-auto pr-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;

          return (
            <button
              key={item.id}
              onClick={() => {
                setActiveTab(item.id);
                if (item.id === 'conversations') onOpenChat();
              }}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-xs font-semibold tracking-wide transition-all ${
                isActive
                  ? 'bg-nova-surface border border-nova-cyan/50 text-nova-cyan shadow-[0_0_12px_rgba(0,240,255,0.2)]'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-nova-surface/50 border border-transparent'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <Icon className={`w-4 h-4 ${isActive ? 'text-nova-cyan' : 'text-slate-400'}`} />
                <span className="font-display tracking-wider">{item.label}</span>
              </div>

              {item.badge !== undefined && (
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono ${
                  isActive 
                    ? 'bg-nova-cyan/20 text-nova-cyan border border-nova-cyan/40' 
                    : 'bg-slate-800 text-slate-400'
                }`}>
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom Voice Status Block */}
      <div className="hud-panel p-3 flex flex-col items-center mt-3 border-nova-cyan/25">
        <div className="w-full flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-1.5">
            <Radio className={`w-3 h-3 ${isVoiceRunning ? 'text-nova-cyan animate-pulse' : 'text-slate-500'}`} />
            <span className="text-[10px] font-mono tracking-widest text-nova-cyanDim uppercase">
              VOICE PIPELINE
            </span>
          </div>
          <span className={`text-[9px] font-mono px-1.5 py-0.2 rounded ${
            isListening 
              ? 'bg-teal-950/80 text-nova-teal border border-nova-teal/40 animate-pulse'
              : isSpeaking
              ? 'bg-blue-950/80 text-nova-cyan border border-nova-cyan/40'
              : isVoiceRunning
              ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/30'
              : 'bg-slate-800 text-slate-500'
          }`}>
            {isListening ? 'LISTENING' : isSpeaking ? 'SPEAKING' : isVoiceRunning ? 'ONLINE' : 'STANDBY'}
          </span>
        </div>

        {/* Live Audio Waveform (Driven by real microphone energy) */}
        <div className="w-full flex justify-center py-1">
          <WaveformVisualizer 
            active={isListening || isSpeaking || isVoiceRunning} 
            color={isListening ? '#00ffd5' : isSpeaking ? '#38bdf8' : '#00f0ff'} 
            barsCount={16}
            amplitude={audioLevel}
          />
        </div>

        <span className="text-[11px] font-mono text-slate-300 mt-1 mb-1 text-center">
          {isListening 
            ? 'Listening to user...' 
            : isThinking
            ? 'Processing query...'
            : isSpeaking 
            ? 'Piper TTS transmitting...' 
            : isThinking
            ? 'Thinking...'
            : wakeWordEnabled 
            ? `Wake Word: "${activeWakePhrase}"`
            : 'Push-to-talk'}
        </span>

        {/* Circular Glowing Microphone Button */}
        <button
          onClick={onMicClick}
          className={`relative w-14 h-14 rounded-full flex items-center justify-center transition-all duration-300 ${
            isListening 
              ? 'bg-nova-teal/20 border-2 border-nova-teal shadow-[0_0_20px_#00ffd5]' 
              : 'bg-nova-surface border border-nova-cyan/40 hover:border-nova-cyan shadow-nova-cyan'
          }`}
          title={wakeWordEnabled ? 'Tap to speak (wake word also active)' : 'Push-to-talk: microphone opens only while listening'}
        >
          {isListening && (
            <div className="absolute inset-0 rounded-full border border-nova-teal animate-ping opacity-60" />
          )}
          <Mic className={`w-6 h-6 ${isListening ? 'text-nova-teal' : 'text-nova-cyan'}`} />
        </button>

        <span className="text-[10px] font-mono text-nova-textDim mt-1.5">
          {isListening ? 'Speaking now...' : 'Tap to Speak'}
        </span>

        {/* Focus Mode Pill */}
        <button
          onClick={() => setFocusMode(!focusMode)}
          className={`w-full mt-2.5 flex items-center justify-center gap-1.5 py-1.5 rounded-full text-[11px] font-display font-semibold tracking-wider transition-all border ${
            focusMode
              ? 'bg-nova-cyan/20 border-nova-cyan text-white shadow-nova-cyan'
              : 'bg-nova-surface/60 border-nova-border/70 text-slate-400 hover:text-slate-200'
          }`}
        >
          <Crosshair className="w-3.5 h-3.5 text-nova-cyan" />
          <span>{focusMode ? 'Focus Active' : 'Focus Mode'}</span>
        </button>
      </div>
    </aside>
  );
};
