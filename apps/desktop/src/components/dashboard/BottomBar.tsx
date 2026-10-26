import React from 'react';
import { MapPin, CloudSun, Wifi, Play, MessageSquare, Mic } from 'lucide-react';
import { WaveformVisualizer } from '../common/WaveformVisualizer';
import { NovaState } from '../../types';

interface BottomBarProps {
  assistantState: NovaState;
  onTalkClick: () => void;
  onExecutiveBriefing: () => void;
  audioLevel?: number;
  wakeWordEnabled?: boolean;
  activeWakePhrase?: string;
}

export const BottomBar: React.FC<BottomBarProps> = ({
  assistantState,
  onTalkClick,
  onExecutiveBriefing,
  audioLevel = 0,
  wakeWordEnabled = true,
  activeWakePhrase = 'Hey Jarvis'
}) => {
  const isListening = assistantState === 'LISTENING';
  const isSpeaking = assistantState === 'SPEAKING';
  const isThinking = assistantState === 'THINKING';

  return (
    <footer className="w-full flex items-center justify-between px-6 py-2 border-t border-nova-border/70 bg-nova-dark/95 backdrop-blur-md z-30 select-none">
      {/* Left Telemetry Badges */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-nova-surface/80 border border-nova-border/60 text-[10px] font-mono text-slate-300">
          <MapPin className="w-3 h-3 text-nova-cyan" />
          <span>Localhost / Windows 11</span>
        </div>

        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-nova-surface/80 border border-nova-border/60 text-[10px] font-mono text-slate-300">
          <CloudSun className="w-3 h-3 text-amber-400" />
          <span>Offline Pipeline</span>
        </div>

        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-nova-surface/80 border border-nova-border/60 text-[10px] font-mono text-slate-300">
          <Wifi className="w-3 h-3 text-emerald-400" />
          <span>Zero Cloud Latency</span>
        </div>
      </div>

      {/* Center Interactive Floating Pill: TALK TO NOVA */}
      <div 
        onClick={onTalkClick}
        className={`flex items-center gap-4 px-6 py-1.5 rounded-full border cursor-pointer transition-all duration-300 select-none group ${
          isListening 
            ? 'bg-nova-teal/20 border-nova-teal shadow-[0_0_20px_#00ffd5]'
            : isSpeaking
            ? 'bg-nova-electric/20 border-nova-cyan shadow-[0_0_20px_#00f0ff]'
            : 'bg-nova-surface/90 border-nova-cyan/50 hover:border-nova-cyan shadow-nova-cyan'
        }`}
      >
        <WaveformVisualizer 
          active={isListening || isSpeaking} 
          color={isListening ? '#00ffd5' : isSpeaking ? '#38bdf8' : '#00f0ff'} 
          barsCount={8} 
          amplitude={audioLevel}
        />

        <div className="flex flex-col items-center">
          <div className="flex items-center gap-1.5">
            <Mic className={`w-3 h-3 ${isListening ? 'text-nova-teal animate-pulse' : 'text-nova-cyan'}`} />
            <span className="font-display font-black text-xs tracking-[0.2em] text-white group-hover:text-nova-cyan transition-colors">
              {isListening 
                ? 'LISTENING TO MICROPHONE' 
                : isThinking
                ? 'THINKING...'
                : isSpeaking 
                ? 'PIPER TTS TRANSMITTING' 
                : 'TALK TO NOVA'}
            </span>
          </div>
          <span className="text-[9px] font-mono text-nova-cyanDim">
            {isListening 
              ? 'Listening for speech...' 
              : isSpeaking
              ? 'Click to interrupt vocal synthesis'
              : wakeWordEnabled 
              ? `Say "${activeWakePhrase}" or click to speak`
              : 'Click to start voice input'}
          </span>
        </div>

        <WaveformVisualizer 
          active={isListening || isSpeaking} 
          color={isListening ? '#00ffd5' : isSpeaking ? '#38bdf8' : '#00f0ff'} 
          barsCount={8} 
          amplitude={audioLevel}
        />
      </div>

      {/* Right Executive Briefing Trigger */}
      <div className="flex items-center gap-2">
        <button
          onClick={onExecutiveBriefing}
          className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-nova-surface border border-nova-cyan/40 hover:border-nova-cyan hover:shadow-nova-cyan text-xs font-display font-semibold text-slate-200 hover:text-white transition-all"
        >
          <Play className="w-3 h-3 text-nova-cyan" />
          <span>Executive Briefing</span>
        </button>
      </div>
    </footer>
  );
};
