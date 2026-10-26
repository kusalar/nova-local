import { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/api';
import { ChatMessage, NovaState } from '../types';

export function useChat(onStateChange?: (state: NovaState, msg?: string) => void) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [voiceEnabled, setVoiceEnabled] = useState<boolean>(true);

  // Load persistent history on mount
  const loadHistory = useCallback(async () => {
    try {
      const data = await apiService.getChatHistory('default');
      if (data && data.messages) {
        setMessages(data.messages);
      }
    } catch (err: any) {
      console.warn('Could not load chat history:', err);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  // Voice speech synthesis
  const speakText = useCallback((text: string) => {
    if (!voiceEnabled || !('speechSynthesis' in window)) return;
    try {
      window.speechSynthesis.cancel();
      // Clean markdown symbols for cleaner speech
      const clean = text.replace(/[*#`_>-]/g, '').trim();
      const utterance = new SpeechSynthesisUtterance(clean);
      utterance.rate = 1.05;
      utterance.pitch = 0.95;

      utterance.onstart = () => {
        setIsSpeaking(true);
        onStateChange?.('SPEAKING', 'NOVA VOCAL SYNTHESIS ACTIVE');
      };
      utterance.onend = () => {
        setIsSpeaking(false);
        onStateChange?.('IDLE', 'NOVA SYSTEM ONLINE');
      };
      utterance.onerror = () => {
        setIsSpeaking(false);
        onStateChange?.('IDLE', 'NOVA SYSTEM ONLINE');
      };

      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn('Speech synthesis error:', e);
    }
  }, [voiceEnabled, onStateChange]);

  const sendMessage = async (text: string, overrideModel?: string) => {
    if (!text.trim() || isLoading) return;

    const userMsg: ChatMessage = {
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString()
    };

    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);
    setError(null);
    onStateChange?.('THINKING', 'PROCESSING NEURAL INFERENCE');

    try {
      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: '',
        model: overrideModel,
        timestamp: new Date().toLocaleTimeString()
      };
      setMessages(prev => [...prev, assistantMsg]);

      let assembled = '';
      let sawToken = false;
      const result = await apiService.sendChatStream(
        text,
        messages,
        overrideModel,
        (token) => {
          assembled += token;
          if (!sawToken) {
            sawToken = true;
            onStateChange?.('SPEAKING', 'STREAMING RESPONSE');
          }
          setMessages(prev => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last && last.role === 'assistant') {
              next[next.length - 1] = { ...last, content: assembled };
            }
            return next;
          });
        }
      );

      if (result.success !== false && assembled) {
        onStateChange?.('SPEAKING', 'TRANSMITTING RESPONSE');
        speakText(assembled);
      } else if (!assembled) {
        onStateChange?.('ERROR', 'AI ENGINE NOTICE');
      }
    } catch (err: any) {
      const errMsg = err?.message || 'Failed to communicate with NOVA Core';
      setError(errMsg);
      onStateChange?.('ERROR', 'CONNECTION FAULT');
      setMessages(prev => {
        const next = [...prev];
        const last = next[next.length - 1];
        const errContent = `System Error: ${errMsg}. Verify that the backend is running.`;
        if (last && last.role === 'assistant' && !last.content) {
          next[next.length - 1] = { ...last, content: errContent };
          return next;
        }
        return [
          ...next,
          {
            role: 'assistant',
            content: errContent,
            timestamp: new Date().toLocaleTimeString()
          }
        ];
      });
    } finally {
      setIsLoading(false);
    }
  };

  const clearMessages = async () => {
    try {
      await apiService.clearChatHistory('default');
      setMessages([]);
      onStateChange?.('IDLE', 'MEMORY REINITIALIZED');
    } catch (err: any) {
      console.error('Failed to clear messages:', err);
    }
  };

  const stopSpeaking = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      onStateChange?.('IDLE', 'NOVA SYSTEM ONLINE');
    }
  };

  return {
    messages,
    isLoading,
    isSpeaking,
    voiceEnabled,
    setVoiceEnabled,
    error,
    sendMessage,
    clearMessages,
    stopSpeaking,
    reloadHistory: loadHistory
  };
}
