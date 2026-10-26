import React from 'react';

interface HudGaugeProps {
  label: string;
  value: number; // 0 - 100
  color?: string; // hex or rgb
  glowColor?: string;
  subtext?: string;
}

export const HudGauge: React.FC<HudGaugeProps> = ({
  label,
  value,
  color = '#00f0ff',
  glowColor = 'rgba(0, 240, 255, 0.4)',
  subtext
}) => {
  const radius = 38;
  const stroke = 6;
  const normalizedRadius = radius - stroke * 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const strokeDashoffset = circumference - (Math.min(Math.max(value, 0), 100) / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center p-2 relative group">
      <div className="relative w-24 h-24 flex items-center justify-center">
        {/* Glow backdrop */}
        <div 
          className="absolute inset-0 rounded-full blur-md opacity-25 group-hover:opacity-40 transition-opacity"
          style={{ background: glowColor }}
        />
        
        <svg height={radius * 2} width={radius * 2} className="rotate-[-90deg]">
          {/* Background circle */}
          <circle
            stroke="rgba(0, 240, 255, 0.12)"
            fill="transparent"
            strokeWidth={stroke}
            r={normalizedRadius}
            cx={radius}
            cy={radius}
          />
          {/* Progress circle */}
          <circle
            stroke={color}
            fill="transparent"
            strokeWidth={stroke}
            strokeDasharray={`${circumference} ${circumference}`}
            style={{ strokeDashoffset, transition: 'stroke-dashoffset 0.8s ease-in-out' }}
            strokeLinecap="round"
            r={normalizedRadius}
            cx={radius}
            cy={radius}
          />
        </svg>

        {/* Center Percentage Display */}
        <div className="absolute flex flex-col items-center justify-center">
          <span className="font-display font-bold text-lg text-white tracking-wider">
            {Math.round(value)}%
          </span>
        </div>
      </div>

      <span className="mt-1 font-display font-semibold text-xs tracking-widest text-slate-300 uppercase">
        {label}
      </span>
      {subtext && (
        <span className="text-[10px] text-nova-textDim tracking-tight">
          {subtext}
        </span>
      )}
    </div>
  );
};
