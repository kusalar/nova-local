import { useState, useEffect, useCallback, useRef } from 'react';
import { apiService } from '../services/api';
import { VoiceStatusResponse, AudioDevice, NovaState } from '../types';

interface UseVoiceProps {
  onStateChange?: (state: NovaState, msg?: string) => void;
  onSpeechRecognized?: (text: string) => void;
  onAssistantSpoke?: (text: string, model?: string) => void;
}

export function useVoice({
  onStateChange,
  onSpeechRecognized,
  onAssistantSpoke
}: UseVoiceProps = {}) {
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatusResponse | null>(null);
  const [isVoiceRunning, setIsVoiceRunning] = useState<boolean>(false);
  const [wakeWordEnabled, setWakeWordEnabled] = useState<boolean>(true);
  const [isListening, setIsListening] = useState<boolean>(false);
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [isThinking, setIsThinking] = useState<boolean>(false);
  const [audioLevel, setAudioLevel] = useState<number>(0.0);
  const [lastRecognizedText, setLastRecognizedText] = useState<string>('');
  const [partialTranscript, setPartialTranscript] = useState<string>('');
  const [devices, setDevices] = useState<{ inputs: AudioDevice[]; outputs: AudioDevice[] }>({
    inputs: [],
    outputs: []
  });
  const [permissionError, setPermissionError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);

  // Keep latest callbacks in ref to avoid re-triggering WebSocket connections on parent re-render
  const callbacksRef = useRef({ onStateChange, onSpeechRecognized, onAssistantSpoke });
  useEffect(() => {
    callbacksRef.current = { onStateChange, onSpeechRecognized, onAssistantSpoke };
  }, [onStateChange, onSpeechRecognized, onAssistantSpoke]);

  // Poll voice REST status & audio devices
  const refreshStatus = useCallback(async () => {
    try {
      const status = await apiService.getVoiceStatus();
      setVoiceStatus(status);
      setIsVoiceRunning(status.running);
      setWakeWordEnabled(status.wake_word_enabled);
    } catch (e) {
      console.warn('Could not query voice status:', e);
    }
  }, []);

  const refreshDevices = useCallback(async () => {
    try {
      const devs = await apiService.getAudioDevices();
      setDevices(devs);
    } catch (e) {
      console.warn('Could not query audio devices:', e);
    }
  }, []);

  // Check browser/webview microphone permission
  const verifyBrowserMicrophonePermission = useCallback(async (): Promise<boolean> => {
    if (typeof navigator !== 'undefined' && navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        // Immediately release stream tracks to avoid keeping mic locked in browser
        stream.getTracks().forEach((track) => track.stop());
        setPermissionError(null);
        return true;
      } catch (err: any) {
        console.warn('[NOVA Voice] Browser getUserMedia permission check:', err);
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
          setPermissionError('Microphone permission denied by browser/system.');
          callbacksRef.current.onStateChange?.('ERROR', 'MICROPHONE PERMISSION DENIED');
          return false;
        }
      }
    }
    return true;
  }, []);

  // WebSocket Connection
  const connectWebSocket = useCallback(() => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const host = window.location.hostname || '127.0.0.1';
    const wsUrl = `ws://${host}:8000/api/voice/ws`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[NOVA Voice Boundary] WebSocket connected to', wsUrl);
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const { type, data } = payload;
        const callbacks = callbacksRef.current;

        switch (type) {
          case 'connected':
            if (data?.status) {
              setVoiceStatus(data.status);
              setIsVoiceRunning(data.status.running);
              setWakeWordEnabled(data.status.wake_word_enabled);
            }
            break;

          case 'wake_word_detected':
            console.log('[NOVA Voice] Wake word activated:', data);
            setPartialTranscript('');
            callbacks.onStateChange?.('LISTENING', `WAKE WORD DETECTED (${data.phrase || 'Hey NOVA'})`);
            setIsListening(true);
            break;

          case 'listening_started':
            setIsListening(true);
            setPartialTranscript('');
            const devName = data?.device ? ` (${data.device})` : '';
            callbacks.onStateChange?.('LISTENING', `LISTENING TO MICROPHONE${devName}`);
            break;

          case 'listening_stopped':
            setIsListening(false);
            break;

          case 'partial_speech':
            if (data.partial) {
              setPartialTranscript(data.partial);
              callbacks.onStateChange?.('LISTENING', `HEARING: "${data.partial}"`);
            }
            break;

          case 'speech_recognized':
            setIsListening(false);
            setPartialTranscript('');
            if (data.text) {
              setLastRecognizedText(data.text);
              callbacks.onSpeechRecognized?.(data.text);
            }
            break;

          case 'no_speech_detected':
            setIsListening(false);
            setPartialTranscript('');
            callbacks.onStateChange?.('IDLE', 'NO SPEECH DETECTED');
            break;

          case 'thinking_started':
            setIsListening(false);
            setIsThinking(true);
            callbacks.onStateChange?.('THINKING', 'PROCESSING VOCAL DIRECTIVE');
            break;

          case 'token_delta':
            setIsThinking(false);
            if (data.content) {
              callbacks.onStateChange?.('SPEAKING', 'STREAMING RESPONSE');
            }
            break;

          case 'speaking_started':
            setIsThinking(false);
            setIsSpeaking(true);
            callbacks.onStateChange?.('SPEAKING', data.partial ? 'STREAMING RESPONSE' : 'PIPER VOCAL TRANSMISSION ACTIVE');
            if (data.text && !data.partial) {
              callbacks.onAssistantSpoke?.(data.text, data.model);
            }
            break;

          case 'speaking_finished':
            setIsSpeaking(false);
            callbacks.onStateChange?.('IDLE', 'NOVA SYSTEM ONLINE');
            break;

          case 'audio_level':
            // Real RMS from physical microphone (scaled for visualizer)
            if (typeof data.rms === 'number') {
              setAudioLevel(Math.min(1.0, data.rms * 6));
            }
            break;

          case 'voice_error':
            console.error('[NOVA Voice Error]', data);
            setIsListening(false);
            setPartialTranscript('');
            let errMsg = data.message || 'VOICE PIPELINE ERROR';
            if (data.code === 'PERMISSION_DENIED') errMsg = 'MIC PERMISSION DENIED IN OS';
            else if (data.code === 'MICROPHONE_MUTED') errMsg = 'MIC MUTED IN WINDOWS';
            else if (data.code === 'NO_MICROPHONE_DETECTED') errMsg = 'NO MIC HARDWARE DETECTED';
            else if (data.code === 'AUDIO_CAPTURE_FAILED') errMsg = 'AUDIO CAPTURE FAILED';
            callbacks.onStateChange?.('ERROR', errMsg);
            break;

          case 'voice_notice':
            console.info('[NOVA Voice Notice]', data.message);
            break;

          case 'voice_status':
            setIsVoiceRunning(!!data.running);
            break;

          default:
            break;
        }
      } catch (err) {
        console.warn('Failed parsing voice WebSocket message:', err);
      }
    };

    ws.onclose = () => {
      console.log('[NOVA Voice] WebSocket disconnected, retrying in 3s...');
      reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = (err) => {
      console.warn('[NOVA Voice] WebSocket error:', err);
    };
  }, []);

  useEffect(() => {
    refreshStatus();
    refreshDevices();
    connectWebSocket();

    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connectWebSocket, refreshStatus, refreshDevices]);

  // Action methods
  const triggerListen = useCallback(async () => {
    try {
      // First verify browser permission if available
      const hasPerm = await verifyBrowserMicrophonePermission();
      if (!hasPerm) return;

      // Note: We do NOT optimistically set isListening=true here.
      // We wait for the backend 'listening_started' WebSocket event to ensure capture actually started.
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ action: 'trigger_listen' }));
      } else {
        const res = await apiService.triggerListen();
        if (res.success) {
          setIsListening(true);
          onStateChange?.('LISTENING', 'LISTENING TO MICROPHONE INPUT');
        }
      }
    } catch (e: any) {
      console.error('Failed to trigger listen:', e);
      onStateChange?.('ERROR', 'COULD NOT OPEN MICROPHONE');
    }
  }, [onStateChange, verifyBrowserMicrophonePermission]);

  const stopListen = useCallback(async () => {
    try {
      setIsListening(false);
      setPartialTranscript('');
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ action: 'stop_listen' }));
      } else {
        await apiService.stopListen();
      }
      onStateChange?.('IDLE', 'NOVA SYSTEM ONLINE');
    } catch (e) {
      console.error('Failed to stop listening:', e);
    }
  }, [onStateChange]);

  const stopSpeaking = useCallback(async () => {
    setIsSpeaking(false);
    setIsThinking(false);
    onStateChange?.('IDLE', 'NOVA SYSTEM ONLINE');
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'cancel_inference' }));
    }
  }, [onStateChange]);

  const toggleVoiceRunning = useCallback(async () => {
    try {
      if (isVoiceRunning) {
        await apiService.stopVoicePipeline();
        setIsVoiceRunning(false);
        setIsListening(false);
        setIsSpeaking(false);
        onStateChange?.('IDLE', 'VOICE ENGINE STANDBY');
      } else {
        const res = await apiService.startVoicePipeline();
        if (res.success) {
          setIsVoiceRunning(true);
          onStateChange?.('IDLE', 'VOICE ENGINE ONLINE');
        }
      }
      refreshStatus();
    } catch (e) {
      console.error('Failed toggling voice:', e);
    }
  }, [isVoiceRunning, onStateChange, refreshStatus]);

  const toggleWakeWord = useCallback(async () => {
    try {
      const nextVal = !wakeWordEnabled;
      await apiService.updateVoiceSettings({ wake_word_enabled: nextVal });
      setWakeWordEnabled(nextVal);
      refreshStatus();
    } catch (e) {
      console.error('Failed toggling wake word:', e);
    }
  }, [wakeWordEnabled, refreshStatus]);

  const updateSettings = useCallback(async (settingsPayload: any) => {
    try {
      const res = await apiService.updateVoiceSettings(settingsPayload);
      if (res.success) {
        setVoiceStatus(res.settings);
        setWakeWordEnabled(res.settings.wake_word_enabled);
        setIsVoiceRunning(res.settings.running);
      }
      return true;
    } catch (e) {
      console.error('Failed updating voice settings:', e);
      return false;
    }
  }, []);

  return {
    voiceStatus,
    isVoiceRunning,
    wakeWordEnabled,
    activeWakePhrase: voiceStatus?.wake_word?.wake_phrase || 'Hey Jarvis',
    isListening,
    isSpeaking,
    isThinking,
    audioLevel,
    lastRecognizedText,
    partialTranscript,
    permissionError,
    devices,
    triggerListen,
    stopListen,
    stopSpeaking,
    toggleVoiceRunning,
    toggleWakeWord,
    updateSettings,
    refreshStatus,
    refreshDevices
  };
}
