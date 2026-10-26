import React, { useState, useEffect } from 'react';
import { Search, LayoutGrid, Bell, Settings, ShieldCheck, User, Eye } from 'lucide-react';

interface TopNavProps {
  onOpenSettings?: () => void;
  onOpenChat?: () => void;
  systemStatusText?: string;
  isBackendConnected?: boolean;
}

export const TopNav: React.FC<TopNavProps> = ({
  onOpenSettings,
  onOpenChat,
  systemStatusText = 'OPTIMAL',
  isBackendConnected = true
}) => {
  const [currentTime, setCurrentTime] = useState<Date>(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const formattedDate = currentTime.toLocaleDateString('en-US', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  });

  const formattedTime = currentTime.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true
  }).toLowerCase();

  return (
    <header className="w-full flex items-center justify-between px-6 py-3 border-b border-nova-border bg-nova-dark/90 backdrop-blur-md z-30 select-none">
      {/* Brand & System Status */}
      <div className="flex items-center gap-4">
        {/* Glowing Emblem */}
        <div className="relative flex items-center justify-center w-10 h-10 rounded-lg bg-nova-surface border border-nova-cyan/40 shadow-nova-cyan group cursor-pointer" onClick={onOpenChat}>
          <div className="w-5 h-5 rounded-full border border-nova-cyan animate-spin-slow flex items-center justify-center">
            <div className="w-2 h-2 rounded-full bg-nova-cyan shadow-[0_0_8px_#00f0ff]" />
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display font-black text-lg tracking-[0.2em] text-white">
              NOVA
            </h1>
            <span className="font-display font-semibold text-xs tracking-widest text-nova-cyanDim">
              COMMAND CENTER
            </span>
          </div>

          <div className="flex items-center gap-2 mt-0.5">
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-500/30 text-[10px] font-mono text-emerald-400">
              <span className={`w-1.5 h-1.5 rounded-full ${isBackendConnected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
              <span>SYSTEM STATUS • {isBackendConnected ? systemStatusText : 'BACKEND OFFLINE'}</span>
            </div>
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-cyan-950/60 border border-cyan-500/30 text-[10px] font-mono text-cyan-400">
              <Eye className="w-3 h-3 text-nova-cyan" />
              <span>VISION v0.5 ACTIVE</span>
            </div>
          </div>
        </div>
      </div>

      {/* Center Holographic Clock */}
      <div className="flex flex-col items-center justify-center">
        <span className="text-[11px] font-mono tracking-widest text-nova-cyanDim uppercase">
          {formattedDate}
        </span>
        <span className="font-display font-black text-2xl tracking-[0.15em] text-nova-cyan text-glow-cyan leading-none mt-0.5">
          {formattedTime}
        </span>
      </div>

      {/* Right Controls: Search, Quick Actions, Profile */}
      <div className="flex items-center gap-3">
        {/* Search Bar */}
        <div className="relative hidden md:flex items-center">
          <Search className="w-3.5 h-3.5 text-nova-cyanDim absolute left-3 pointer-events-none" />
          <input
            type="text"
            placeholder="Search directives..."
            className="w-48 lg:w-56 pl-9 pr-3 py-1.5 rounded-md bg-nova-surface/80 border border-nova-border text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-nova-cyan focus:shadow-nova-cyan transition-all font-mono"
            onKeyDown={(e) => {
              if (e.key === 'Enter') onOpenChat?.();
            }}
          />
        </div>

        {/* Action Icons */}
        <div className="flex items-center gap-1 border-l border-nova-border/60 pl-3">
          <button 
            className="p-2 rounded-md hover:bg-nova-surface text-slate-400 hover:text-nova-cyan transition-colors"
            title="Overview Grid"
          >
            <LayoutGrid className="w-4 h-4" />
          </button>

          <button 
            onClick={onOpenChat}
            className="p-2 rounded-md hover:bg-nova-surface text-slate-400 hover:text-nova-cyan transition-colors relative"
            title="Notifications & Feed"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-nova-cyan animate-pulse shadow-[0_0_6px_#00f0ff]" />
          </button>

          <button 
            onClick={onOpenSettings}
            className="p-2 rounded-md hover:bg-nova-surface text-slate-400 hover:text-nova-cyan transition-colors"
            title="Settings"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>

        {/* Commander Pill */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-nova-surface border border-nova-border/80 text-xs">
          <div className="w-5 h-5 rounded-full bg-nova-cyan/20 border border-nova-cyan/50 flex items-center justify-center text-nova-cyan">
            <User className="w-3 h-3" />
          </div>
          <div className="flex flex-col text-left">
            <span className="text-[9px] text-nova-textDim leading-tight">Operator</span>
            <span className="font-display font-semibold text-slate-200 leading-tight">Commander</span>
          </div>
        </div>
      </div>
    </header>
  );
};
