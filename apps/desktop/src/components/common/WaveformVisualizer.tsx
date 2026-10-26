import React from 'react';

interface WaveformVisualizerProps {
  active?: boolean;
  color?: string;
  barsCount?: number;
  height?: number;
  amplitude?: number; // 0.0 to 1.0 real RMS amplitude
}

export const WaveformVisualizer: React.FC<WaveformVisualizerProps> = ({
  active = true,
  color = '#00f0ff',
  barsCount = 18,
  height = 24,
  amplitude = 0
}) => {
  const delays = [0.1, 0.4, 0.2, 0.6, 0.3, 0.5, 0.15, 0.45, 0.25, 0.55, 0.35, 0.1, 0.4, 0.2, 0.5, 0.3, 0.6, 0.2];

  return (
    <div className="flex items-center gap-[2px] h-6 px-1">
      {Array.from({ length: barsCount }).map((_, i) => {
        const delay = delays[i % delays.length];
        const boost = amplitude > 0.02 ? amplitude * 22 * (0.6 + Math.sin(i * 0.9) * 0.4) : 0;
        const barHeight = active 
          ? Math.min(height, Math.max(4, Math.sin(i * 0.8) * 8 + 8 + boost))
          : 4;

        return (
          <div
            key={i}
            className="w-[2px] rounded-full transition-all duration-150"
            style={{
              height: `${barHeight}px`,
              backgroundColor: color,
              boxShadow: active ? `0 0 8px ${color}` : 'none',
              animation: (active && amplitude <= 0.02) ? `pulse 1.${(i % 5) + 2}s ease-in-out infinite` : 'none',
              animationDelay: `${delay}s`,
              opacity: active ? (amplitude > 0.02 ? 1.0 : 0.85) : 0.25
            }}
          />
        );
      })}
    </div>
  );
};
