import { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/api';
import { AiStatusResponse } from '../types';

const defaultAiStatus: AiStatusResponse = {
  online: false,
  provider: 'Ollama (Local)',
  endpoint: 'http://localhost:11434',
  available_models: [],
  active_model: 'qwen2.5:1.5b',
  model_ready: false,
  message: 'Interrogating local neural engine...'
};

export function useAiStatus(pollingIntervalMs: number = 5000) {
  const [status, setStatus] = useState<AiStatusResponse>(defaultAiStatus);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await apiService.getAiStatus();
      setStatus(res);
    } catch (err: any) {
      setStatus(prev => ({
        ...prev,
        online: false,
        message: 'Neural daemon disconnected. Start Ollama service on localhost:11434.'
      }));
    } finally {
      setLoading(false);
    }
  }, []);

  const changeModel = async (modelName: string) => {
    try {
      await apiService.selectModel(modelName);
      setStatus(prev => ({ ...prev, active_model: modelName }));
      return true;
    } catch {
      return false;
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, pollingIntervalMs);
    return () => clearInterval(interval);
  }, [fetchStatus, pollingIntervalMs]);

  return { status, loading, changeModel, refresh: fetchStatus };
}
