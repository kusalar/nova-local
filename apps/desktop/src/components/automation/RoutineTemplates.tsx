import React from 'react';
import { Sparkles, Plus, Clock, ShieldCheck, Activity } from 'lucide-react';
import { RoutineTemplate } from '../../types';

interface RoutineTemplatesProps {
  templates: RoutineTemplate[];
  onUseTemplate: (template: RoutineTemplate) => void;
}

export const RoutineTemplates: React.FC<RoutineTemplatesProps> = ({
  templates,
  onUseTemplate,
}) => {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between pb-2 border-b border-cyan-500/20">
        <div>
          <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            Curated Routine Templates
          </h3>
          <p className="text-xs text-slate-400 font-mono">
            Pre-configured proactive intelligence routines for productivity and health monitoring.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {templates.map(tpl => (
          <div
            key={tpl.id}
            className="p-4 rounded-lg bg-slate-900/60 border border-cyan-500/20 hover:border-cyan-400/50 transition-all flex flex-col justify-between space-y-3 group"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
                  {tpl.category}
                </span>
                <span className="text-[10px] font-mono text-slate-400">
                  Level: {tpl.autonomy_level}
                </span>
              </div>
              <h4 className="text-sm font-bold text-slate-100 mt-2 group-hover:text-cyan-300 transition-colors">
                {tpl.name}
              </h4>
              <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                {tpl.description}
              </p>
            </div>

            <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between">
              <span className="text-[10px] font-mono text-slate-400 flex items-center gap-1">
                <Clock className="w-3 h-3 text-cyan-400" />
                {tpl.trigger_config.trigger_type}
                {tpl.trigger_config.schedule?.time_of_day && ` @ ${tpl.trigger_config.schedule.time_of_day}`}
              </span>
              <button
                onClick={() => onUseTemplate(tpl)}
                className="px-3 py-1 text-xs font-mono uppercase bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 rounded hover:bg-cyan-500 hover:text-slate-950 font-semibold transition-all flex items-center gap-1"
              >
                <Plus className="w-3 h-3" />
                Use Routine
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
