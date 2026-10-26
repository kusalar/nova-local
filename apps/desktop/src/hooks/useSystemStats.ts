import { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/api';
import { SystemStatusResponse } from '../types';

const defaultStats: SystemStatusResponse = {
  status: 'optimal',
  telemetry: {
    cpu: { percent: 14.8, core_count: 8, physical_cores: 4 },
    ram: { percent: 54.2, used_gb: 8.7, total_gb: 16.0, available_gb: 7.3 },
    disk: { percent: 42.0, used_gb: 215.4, total_gb: 512.0 },
    battery: { has_battery: true, percent: 98, is_plugged: true, status: 'A/C Connected' },
    system: { os: 'Windows', release: '11', machine: 'x86_64', node: 'NOVA-CORE', uptime_hours: 6.4 }
  },
  assistant: {
    state: 'IDLE',
    status_message: 'NOVA SYSTEM ONLINE',
    timestamp: new Date().toISOString()
  },
  memory: {
    total_messages: 3380,
    session_turns: 22,
    db_path: 'nova_memory.db'
  }
};

export function useSystemStats(pollingIntervalMs: number = 3000) {
  const [data, setData] = useState<SystemStatusResponse>(defaultStats);
  const [isBackendConnected, setIsBackendConnected] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      const result = await apiService.getSystemStatus();
      setData(result);
      setIsBackendConnected(true);
      setError(null);
    } catch (err: any) {
      setIsBackendConnected(false);
      setError(err?.message || 'Backend unreachable');
    }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, pollingIntervalMs);
    return () => clearInterval(interval);
  }, [fetchStats, pollingIntervalMs]);

  return { data, isBackendConnected, error, refresh: fetchStats };
}
