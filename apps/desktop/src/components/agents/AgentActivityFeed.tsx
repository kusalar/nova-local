import React from 'react';
import { 
  Activity, 
  Bot, 
  CheckCircle2, 
  Clock, 
  XCircle, 
  ShieldAlert, 
  Sparkles,
  MessageSquare
} from 'lucide-react';
import { WorkflowEvent, WorkflowEventType } from '../../types';

interface AgentActivityFeedProps {
  events: WorkflowEvent[];
  isLoading?: boolean;
}

export const AgentActivityFeed: React.FC<AgentActivityFeedProps> = ({
  events,
  isLoading
}) => {
  const getEventIcon = (type: WorkflowEventType) => {
    switch (type) {
      case 'workflow_started':
      case 'workflow_completed':
        return <Sparkles className="w-3.5 h-3.5 text-cyan-400" />;
      case 'step_started':
        return <Clock className="w-3.5 h-3.5 text-amber-400" />;
      case 'step_completed':
      case 'step_approved':
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
      case 'step_failed':
      case 'workflow_failed':
      case 'step_rejected':
        return <XCircle className="w-3.5 h-3.5 text-rose-400" />;
      case 'step_waiting_approval':
        return <ShieldAlert className="w-3.5 h-3.5 text-purple-400" />;
      case 'agent_message':
        return <MessageSquare className="w-3.5 h-3.5 text-blue-400" />;
      default:
        return <Activity className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  return (
    <div className="hud-panel p-3.5 rounded-lg border border-slate-800 bg-slate-900/50 flex flex-col gap-2.5">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <h4 className="text-xs font-mono font-semibold text-slate-300 uppercase flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          Agent Audit & Telemetry Events
        </h4>
        <span className="text-[10px] font-mono text-slate-500">
          {events.length} Events
        </span>
      </div>

      {isLoading ? (
        <div className="text-center py-4 text-xs font-mono text-slate-500">
          Loading audit events...
        </div>
      ) : events.length === 0 ? (
        <div className="text-center py-6 text-xs font-mono text-slate-500">
          No events recorded for this workflow yet.
        </div>
      ) : (
        <div className="space-y-2 max-h-60 overflow-y-auto custom-scrollbar pr-1">
          {events.map((event) => (
            <div
              key={event.event_id}
              className="p-2 rounded bg-slate-950/70 border border-slate-800/80 text-xs flex items-start gap-2.5"
            >
              <div className="p-1 rounded bg-slate-900 border border-slate-800 shrink-0 mt-0.5">
                {getEventIcon(event.event_type)}
              </div>

              <div className="flex-1 space-y-0.5">
                <div className="flex items-center justify-between gap-2 text-[10px] font-mono">
                  <div className="flex items-center gap-1.5">
                    {event.agent_role && (
                      <span className="text-cyan-400 uppercase font-bold">
                        [{event.agent_role}]
                      </span>
                    )}
                    {event.step_id !== undefined && (
                      <span className="text-slate-400">
                        Step #{event.step_id}
                      </span>
                    )}
                  </div>
                  <span className="text-slate-500">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </span>
                </div>

                <p className="text-xs text-slate-300 leading-snug">
                  {event.message}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
