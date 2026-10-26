import React from 'react';
import { Plus, Calendar, Mic, Play } from 'lucide-react';

interface QuickCommandsProps {
  onStartChat?: () => void;
  onVoiceClick?: () => void;
  onNewTask?: () => void;
}

export const QuickCommands: React.FC<QuickCommandsProps> = ({
  onStartChat,
  onVoiceClick,
  onNewTask
}) => {
  const commands = [
    { label: 'Start New Task', icon: Plus, onClick: onNewTask },
    { label: 'Open Calendar', icon: Calendar, onClick: () => {} },
    { label: 'Start Voice Chat', icon: Mic, onClick: onVoiceClick },
    { label: 'Run Workflow', icon: Play, onClick: onStartChat },
  ];

  return (
    <div className="hud-panel p-3.5 flex flex-col justify-between h-full">
      <div className="flex items-center justify-between mb-2">
        <span className="font-display font-bold text-xs tracking-widest text-nova-cyan uppercase">
          QUICK COMMANDS
        </span>
      </div>

      <div className="space-y-1.5 flex-1 flex flex-col justify-between">
        {commands.map((cmd, idx) => {
          const Icon = cmd.icon;
          return (
            <button
              key={idx}
              onClick={cmd.onClick}
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded bg-nova-surface/80 border border-nova-border/60 hover:border-nova-cyan hover:shadow-nova-cyan transition-all text-left group"
            >
              <div className="p-1 rounded bg-nova-cyan/10 border border-nova-cyan/30 text-nova-cyan group-hover:scale-110 transition-transform">
                <Icon className="w-3.5 h-3.5" />
              </div>
              <span className="font-display font-semibold text-xs text-slate-200 group-hover:text-nova-cyan transition-colors">
                {cmd.label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
