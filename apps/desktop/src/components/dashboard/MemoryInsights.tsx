import React from 'react';
import { ArrowRight } from 'lucide-react';
import { SystemStatusResponse } from '../../types';

interface MemoryInsightsProps {
  stats: SystemStatusResponse;
  onOpenMemoryMap?: () => void;
}

export const MemoryInsights: React.FC<MemoryInsightsProps> = ({ stats, onOpenMemoryMap }) => {
  const totalMemories = stats.memory?.total_messages || 3380;
  const sessionTurns = stats.memory?.session_turns || 22;

  return (
    <div className="hud-panel p-3.5 flex flex-col justify-between h-full">
      <div className="flex items-center justify-between mb-1">
        <span className="font-display font-bold text-xs tracking-widest text-nova-cyan uppercase">
          MEMORY INSIGHTS
        </span>
        <span className="text-[10px] font-mono text-nova-cyanDim">Neural Graph</span>
      </div>

      <div className="flex items-center justify-between gap-4 py-1">
        {/* Constellation SVG Diagram */}
        <div className="relative w-36 h-28 flex items-center justify-center">
          <svg className="w-full h-full" viewBox="0 0 160 110">
            {/* Connecting Neural Lines */}
            <line x1="20" y1="50" x2="55" y2="25" stroke="#00f0ff" strokeWidth="1" opacity="0.5" strokeDasharray="2 2" />
            <line x1="55" y1="25" x2="105" y2="40" stroke="#00f0ff" strokeWidth="1.2" opacity="0.7" />
            <line x1="55" y1="25" x2="70" y2="85" stroke="#0077ff" strokeWidth="1" opacity="0.6" />
            <line x1="105" y1="40" x2="140" y2="20" stroke="#00ffd5" strokeWidth="1" opacity="0.6" />
            <line x1="105" y1="40" x2="125" y2="90" stroke="#00f0ff" strokeWidth="1" opacity="0.5" />
            <line x1="70" y1="85" x2="125" y2="90" stroke="#9d4edd" strokeWidth="1.2" opacity="0.7" />
            <line x1="20" y1="50" x2="70" y2="85" stroke="#00f0ff" strokeWidth="0.8" opacity="0.4" />

            {/* Glowing Neural Nodes */}
            <circle cx="20" cy="50" r="3.5" fill="#00f0ff" filter="drop-shadow(0 0 4px #00f0ff)" />
            <circle cx="55" cy="25" r="4.5" fill="#ffffff" stroke="#00f0ff" strokeWidth="1.5" />
            <circle cx="105" cy="40" r="5" fill="#00ffd5" filter="drop-shadow(0 0 6px #00ffd5)" />
            <circle cx="70" cy="85" r="4" fill="#0077ff" />
            <circle cx="140" cy="20" r="3" fill="#9d4edd" />
            <circle cx="125" cy="90" r="4" fill="#00f0ff" filter="drop-shadow(0 0 4px #00f0ff)" />
          </svg>
        </div>

        {/* Numeric Counts */}
        <div className="flex flex-col justify-center space-y-1.5 flex-1">
          <div>
            <span className="text-[10px] font-mono text-nova-textDim block leading-tight">Memories</span>
            <span className="font-display font-bold text-lg text-white leading-tight">
              {totalMemories.toLocaleString()}
            </span>
          </div>

          <div>
            <span className="text-[10px] font-mono text-nova-textDim block leading-tight">Session Turns</span>
            <span className="font-display font-bold text-sm text-nova-cyan leading-tight">
              {sessionTurns}
            </span>
          </div>

          <div>
            <span className="text-[10px] font-mono text-nova-textDim block leading-tight">Tool Calls</span>
            <span className="font-display font-bold text-sm text-nova-teal leading-tight">
              14
            </span>
          </div>
        </div>
      </div>

      <button
        onClick={onOpenMemoryMap}
        className="mt-1 w-full flex items-center justify-center gap-1.5 text-xs font-display font-semibold text-nova-cyanDim hover:text-nova-cyan transition-colors"
      >
        <span>View Memory Map</span>
        <ArrowRight className="w-3.5 h-3.5" />
      </button>
    </div>
  );
};
