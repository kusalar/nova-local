import React from 'react';
import { Calendar, AlertTriangle, GitPullRequest, Moon, Activity, ArrowRight } from 'lucide-react';

interface LiveFeedProps {
  onOpenFeed?: () => void;
  cpuPercent?: number;
}

export const LiveFeed: React.FC<LiveFeedProps> = ({ onOpenFeed, cpuPercent = 15 }) => {
  const feedItems = [
    {
      title: 'Design review with the product team...',
      category: 'Meeting',
      tag: 'INFO',
      tagColor: 'bg-blue-950/80 text-blue-400 border-blue-500/40',
      icon: Calendar,
      iconColor: 'text-blue-400',
    },
    {
      title: '2 tasks are overdue — "Polish voice pipe..."',
      category: 'Overdue',
      tag: 'WARN',
      tagColor: 'bg-amber-950/80 text-amber-400 border-amber-500/40',
      icon: AlertTriangle,
      iconColor: 'text-amber-400',
    },
    {
      title: '3 pull requests are awaiting your review...',
      category: 'Github',
      tag: 'TIP',
      tagColor: 'bg-teal-950/80 text-teal-400 border-teal-500/40',
      icon: GitPullRequest,
      iconColor: 'text-teal-400',
    },
    {
      title: 'Your deep-work block is 2–4 PM. Notifications silenced.',
      category: 'Focus',
      tag: 'TIP',
      tagColor: 'bg-teal-950/80 text-teal-400 border-teal-500/40',
      icon: Moon,
      iconColor: 'text-teal-400',
    },
    {
      title: `CPU telemetry nominal at ${Math.round(cpuPercent)}%`,
      category: 'System load nominal',
      tag: 'LIVE',
      tagColor: 'bg-emerald-950/80 text-emerald-400 border-emerald-500/40',
      icon: Activity,
      iconColor: 'text-emerald-400',
    },
  ];

  return (
    <div className="hud-panel p-3.5 flex flex-col justify-between h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <span className="font-display font-bold text-xs tracking-widest text-nova-cyan uppercase">
          LIVE INTELLIGENCE FEED
        </span>
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-950/70 border border-emerald-500/40 text-[9px] font-mono text-emerald-400">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span>• LIVE</span>
        </div>
      </div>

      {/* Feed list */}
      <div className="space-y-1.5 flex-1 overflow-y-auto pr-0.5">
        {feedItems.map((item, idx) => {
          const Icon = item.icon;
          return (
            <div
              key={idx}
              className="p-2 rounded bg-nova-surface/60 border border-nova-border/50 hover:border-nova-cyan/50 transition-colors flex items-start justify-between gap-2"
            >
              <div className="flex items-start gap-2 min-w-0">
                <div className="p-1 rounded bg-nova-dark/60 border border-nova-border/40 mt-0.5">
                  <Icon className={`w-3.5 h-3.5 ${item.iconColor}`} />
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="font-display font-semibold text-xs text-slate-200 truncate">
                    {item.title}
                  </span>
                  <span className="text-[10px] font-mono text-nova-textDim">
                    {item.category}
                  </span>
                </div>
              </div>

              <span className={`px-1.5 py-0.5 rounded border text-[9px] font-mono font-bold flex-shrink-0 ${item.tagColor}`}>
                {item.tag}
              </span>
            </div>
          );
        })}
      </div>

      {/* Footer Link */}
      <button
        onClick={onOpenFeed}
        className="mt-2 w-full flex items-center justify-center gap-1.5 text-xs font-display font-semibold text-nova-cyanDim hover:text-nova-cyan transition-colors"
      >
        <span>View All Intelligence</span>
        <ArrowRight className="w-3.5 h-3.5" />
      </button>
    </div>
  );
};
