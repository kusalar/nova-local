import React from 'react';
import { ChevronDown, ArrowRight } from 'lucide-react';

export const MissionTimeline: React.FC = () => {
  const events = [
    {
      time: '09:30 am',
      title: 'Daily Standup',
      status: 'Done',
      statusColor: 'text-slate-400',
      dotColor: 'bg-emerald-400',
    },
    {
      time: '12:00 pm',
      title: 'Finalize HUD panel spacing',
      status: 'In 42 min',
      statusColor: 'text-nova-cyan',
      dotColor: 'bg-nova-cyan',
    },
    {
      time: '02:00 pm',
      title: 'Deep-work block: Voice pipeline',
      status: 'In 2h 42m',
      statusColor: 'text-nova-teal',
      dotColor: 'bg-nova-teal',
    },
    {
      time: '04:30 pm',
      title: 'Design Review — Command Center V1',
      status: 'In 5h 12m',
      statusColor: 'text-slate-400',
      dotColor: 'bg-blue-400',
    },
  ];

  return (
    <div className="hud-panel p-3.5 flex flex-col justify-between h-full">
      <div className="flex items-center justify-between mb-2">
        <span className="font-display font-bold text-xs tracking-widest text-nova-cyan uppercase">
          MISSION TIMELINE
        </span>
        <button className="flex items-center gap-1 px-2 py-0.5 rounded bg-nova-surface border border-nova-border text-[10px] font-mono text-slate-300">
          <span>Today</span>
          <ChevronDown className="w-3 h-3 text-nova-cyan" />
        </button>
      </div>

      <div className="space-y-2 flex-1">
        {events.map((evt, idx) => (
          <div key={idx} className="flex items-center justify-between text-xs font-mono">
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-nova-textDim w-16">{evt.time}</span>
              <span className={`w-2 h-2 rounded-full ${evt.dotColor}`} />
              <span className="font-display font-semibold text-slate-200">{evt.title}</span>
            </div>
            <span className={`text-[10px] font-mono ${evt.statusColor}`}>
              {evt.status}
            </span>
          </div>
        ))}
      </div>

      <button className="mt-2 w-full flex items-center justify-center gap-1.5 text-xs font-display font-semibold text-nova-cyanDim hover:text-nova-cyan transition-colors">
        <span>View Full Schedule</span>
        <ArrowRight className="w-3.5 h-3.5" />
      </button>
    </div>
  );
};
