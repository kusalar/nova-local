import React from 'react';
import { HudGauge } from '../common/HudGauge';
import { SystemStatusResponse } from '../../types';
import { BatteryCharging, Battery, HardDrive } from 'lucide-react';

interface SystemMonitorProps {
  stats: SystemStatusResponse;
}

export const SystemMonitor: React.FC<SystemMonitorProps> = ({ stats }) => {
  const telemetry = stats.telemetry;
  const cpu = telemetry?.cpu?.percent ?? 15;
  const ram = telemetry?.ram?.percent ?? 54;
  const disk = telemetry?.disk?.percent ?? 40;
  const battery = telemetry?.battery;

  return (
    <div className="hud-panel p-3.5 flex flex-col justify-between h-full">
      <div className="flex items-center justify-between mb-1">
        <span className="font-display font-bold text-xs tracking-widest text-nova-cyan uppercase">
          SYSTEM MONITOR
        </span>
        {battery?.has_battery && (
          <div className="flex items-center gap-1 text-[10px] font-mono text-nova-cyanDim">
            {battery.is_plugged ? (
              <BatteryCharging className="w-3.5 h-3.5 text-emerald-400" />
            ) : (
              <Battery className="w-3.5 h-3.5 text-nova-cyan" />
            )}
            <span>{battery.percent}%</span>
          </div>
        )}
      </div>

      {/* 3 Circular Radial Gauges */}
      <div className="flex items-center justify-around py-1">
        <HudGauge 
          label="CPU" 
          value={cpu} 
          color="#00f0ff" 
          glowColor="rgba(0, 240, 255, 0.4)"
          subtext={`${telemetry?.cpu?.core_count || 8} Cores`}
        />
        <HudGauge 
          label="RAM" 
          value={ram} 
          color="#00ffd5" 
          glowColor="rgba(0, 255, 213, 0.4)"
          subtext={`${telemetry?.ram?.used_gb || 8.7} / ${telemetry?.ram?.total_gb || 16} GB`}
        />
        <HudGauge 
          label="DISK" 
          value={disk} 
          color="#0077ff" 
          glowColor="rgba(0, 119, 255, 0.4)"
          subtext={`${telemetry?.disk?.used_gb || 215} GB Used`}
        />
      </div>

      <div className="pt-2 border-t border-nova-border/30 flex items-center justify-between text-[10px] font-mono text-nova-textDim">
        <span>OS: {telemetry?.system?.os} {telemetry?.system?.release}</span>
        <span>Uptime: {telemetry?.system?.uptime_hours || 6.4}h</span>
      </div>
    </div>
  );
};
