import React from 'react';
import { ScheduleConfig, ScheduleType } from '../../types';

interface AutomationScheduleProps {
  schedule: ScheduleConfig;
  onChange: (schedule: ScheduleConfig) => void;
}

const DAYS_OF_WEEK = [
  { id: 0, label: 'Mon' },
  { id: 1, label: 'Tue' },
  { id: 2, label: 'Wed' },
  { id: 3, label: 'Thu' },
  { id: 4, label: 'Fri' },
  { id: 5, label: 'Sat' },
  { id: 6, label: 'Sun' },
];

export const AutomationSchedule: React.FC<AutomationScheduleProps> = ({
  schedule,
  onChange,
}) => {
  const handleTypeChange = (type: ScheduleType) => {
    onChange({
      ...schedule,
      schedule_type: type,
    });
  };

  const toggleDay = (dayId: number) => {
    const current = schedule.days_of_week || [];
    const next = current.includes(dayId)
      ? current.filter(d => d !== dayId)
      : [...current, dayId].sort();
    onChange({ ...schedule, days_of_week: next });
  };

  return (
    <div className="space-y-4 p-4 bg-slate-900/60 rounded-lg border border-cyan-500/20">
      <div className="flex items-center justify-between">
        <label className="text-xs font-mono uppercase tracking-wider text-cyan-400">
          Schedule Configuration
        </label>
        <div className="flex space-x-1">
          {(['DAILY', 'WEEKLY', 'RECURRING', 'ONCE'] as ScheduleType[]).map(st => (
            <button
              key={st}
              type="button"
              onClick={() => handleTypeChange(st)}
              className={`px-2 py-0.5 text-[10px] font-mono uppercase rounded transition-colors ${
                schedule.schedule_type === st
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                  : 'text-slate-400 hover:text-cyan-300 hover:bg-slate-800'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Time of Day */}
      {(schedule.schedule_type === 'DAILY' || schedule.schedule_type === 'WEEKLY') && (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1">Execution Time (HH:MM)</label>
            <input
              type="time"
              value={schedule.time_of_day || '08:00'}
              onChange={e => onChange({ ...schedule, time_of_day: e.target.value })}
              className="w-full bg-slate-950/80 border border-slate-700 rounded px-3 py-1.5 text-sm text-cyan-400 font-mono focus:border-cyan-400 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1">Timezone</label>
            <input
              type="text"
              value={schedule.timezone || 'UTC'}
              onChange={e => onChange({ ...schedule, timezone: e.target.value })}
              placeholder="e.g. UTC, Asia/Kolkata, America/New_York"
              className="w-full bg-slate-950/80 border border-slate-700 rounded px-3 py-1.5 text-sm text-slate-200 font-mono focus:border-cyan-400 focus:outline-none"
            />
          </div>
        </div>
      )}

      {/* Days of Week (for Weekly) */}
      {schedule.schedule_type === 'WEEKLY' && (
        <div>
          <label className="block text-xs font-mono text-slate-300 mb-2">Active Days</label>
          <div className="flex space-x-2">
            {DAYS_OF_WEEK.map(d => {
              const active = (schedule.days_of_week || []).includes(d.id);
              return (
                <button
                  key={d.id}
                  type="button"
                  onClick={() => toggleDay(d.id)}
                  className={`flex-1 py-1 text-xs font-mono rounded transition-colors ${
                    active
                      ? 'bg-cyan-500 text-slate-950 font-bold shadow-md shadow-cyan-500/20'
                      : 'bg-slate-800/80 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {d.label}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Recurring Interval */}
      {schedule.schedule_type === 'RECURRING' && (
        <div>
          <label className="block text-xs font-mono text-slate-300 mb-1">
            Interval (Seconds)
          </label>
          <input
            type="number"
            min={60}
            step={60}
            value={schedule.interval_seconds || 3600}
            onChange={e => onChange({ ...schedule, interval_seconds: parseInt(e.target.value) || 3600 })}
            className="w-full bg-slate-950/80 border border-slate-700 rounded px-3 py-1.5 text-sm text-cyan-400 font-mono focus:border-cyan-400 focus:outline-none"
          />
          <p className="text-[10px] text-slate-500 font-mono mt-1">
            E.g. 1800 for 30 minutes, 3600 for 1 hour.
          </p>
        </div>
      )}
    </div>
  );
};
