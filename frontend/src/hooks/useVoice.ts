import { useState, useCallback, useEffect } from 'react';
import {
  classifyError,
  createVoiceError,
  retryWithBackoff,
  handleApiError,
  checkBrowserSupport,
  type VoiceErrorType
} from '@/lib/voice-error-handler';

export interface VoiceMessage {
  type: 'voice_input' | 'voice_output' | 'text_input' | 'text_output';
  content: string;
  audioUrl?: string;
  transcript?: string;
  language?: 'en' | 'ta' | 'hi';
  duration?: number;
  timestamp: string;
}

export interface VoicePreferences {
  enabled: boolean;
  language: 'en' | 'ta' | 'hi';
  autoPlay: boolean;
  showTranscripts: boolean;
}

export interface UseVoiceReturn {
  isRecording: boolean;
  isPlaying: boolean;
  currentLanguage: 'en' | 'ta' | 'hi';
  preferences: VoicePreferences;
  voiceMessages: VoiceMessage[];
  error: string | null;
  
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<Blob | null>;
  playVoiceMessage: (audioUrl: string) => Promise<void>;
  pausePlayback: () => void;
  setLanguage: (language: 'en' | 'ta' | 'hi') => void;
  toggleVoiceMode: () => void;
  sendVoiceMessage: (audioBlob: Blob, duration: number) => Promise<VoiceMessage | null>;
  addVoiceMessage: (message: VoiceMessage) => void;
  clearError: () => void;
}

export function useVoice(): UseVoiceReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentLanguage, setCurrentLanguage] = useState<'en' | 'ta' | 'hi'>(() => {
    // Load language preference from localStorage
    const saved = localStorage.getItem('voiceLanguage');
    return (saved as 'en' | 'ta' | 'hi') || 'en';
  });
  
  const [preferences, setPreferences] = useState<VoicePreferences>({
    enabled: true,
    language: currentLanguage,
    autoPlay: true,
    showTranscripts: true,
  });

  const [voiceMessages, setVoiceMessages] = useState<VoiceMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [browserSupported, setBrowserSupported] = useState(true);

  // Check browser support on mount
  useEffect(() => {
    const { supported, issues } = checkBrowserSupport();
    setBrowserSupported(supported);
    if (!supported) {
      setError(`Voice features not supported: ${issues.join(', ')}`);
    }
  }, []);

  // Load preferences from localStorage on mount
  useEffect(() => {
    const savedPreferences = localStorage.getItem('voicePreferences');
    if (savedPreferences) {
      try {
        setPreferences(JSON.parse(savedPreferences));
      } catch (e) {
        console.error('Failed to load voice preferences:', e);
      }
    }
  }, []);

  // Update language and persist
  const setLanguage = useCallback((language: 'en' | 'ta' | 'hi') => {
    setCurrentLanguage(language);
    localStorage.setItem('voiceLanguage', language);
    setPreferences(prev => ({ ...prev, language }));
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const startRecording = useCallback(async () => {
    try {
      if (!browserSupported) {
        throw createVoiceError('unsupported_browser', currentLanguage);
      }
      setError(null);
      setIsRecording(true);
    } catch (err) {
      const voiceError = err instanceof Error
        ? createVoiceError(classifyError(err), currentLanguage, err)
        : createVoiceError('recording_failed', currentLanguage);
      setError(voiceError.userMessage);
      setIsRecording(false);
    }
  }, [browserSupported, currentLanguage]);

  const stopRecording = useCallback(async (): Promise<Blob | null> => {
    try {
      setIsRecording(false);
      return null; // Actual blob returned from VoiceRecorder component
    } catch (err) {
      const voiceError = err instanceof Error
        ? createVoiceError(classifyError(err), currentLanguage, err)
        : createVoiceError('recording_failed', currentLanguage);
      setError(voiceError.userMessage);
      return null;
    }
  }, [currentLanguage]);

  const playVoiceMessage = useCallback(async (audioUrl: string) => {
    try {
      setError(null);
      setIsPlaying(true);
      // Actual playback handled by VoicePlayer component
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Playback failed';
      setError(errorMsg);
      setIsPlaying(false);
    }
  }, []);

  const pausePlayback = useCallback(() => {
    setIsPlaying(false);
  }, []);

  const toggleVoiceMode = useCallback(() => {
    setPreferences(prev => ({
      ...prev,
      enabled: !prev.enabled,
    }));
    localStorage.setItem('voicePreferences', JSON.stringify({
      ...preferences,
      enabled: !preferences.enabled,
    }));
  }, [preferences]);

  const sendVoiceMessage = useCallback(async (audioBlob: Blob, duration: number): Promise<VoiceMessage | null> => {
    try {
      setError(null);
      
      // Retry logic for network issues
      const response = await retryWithBackoff(async () => {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'voice-message.webm');
        formData.append('language', currentLanguage);

        const resp = await fetch('/api/voice/speak', {
          method: 'POST',
          body: formData,
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('authToken') || ''}`,
          },
        });

        if (!resp.ok) {
          const errorType = handleApiError(resp.status);
          throw createVoiceError(errorType, currentLanguage);
        }

        return resp;
      }, 3);

      if (!response.ok) {
        throw new Error('Voice request failed after retries');
      }

      // Get response as audio stream with headers
      const audioBuffer = await response.arrayBuffer();
      const transcript = response.headers.get('X-Transcript') || '';
      const reply = response.headers.get('X-Reply') || '';
      const responseLanguage = response.headers.get('X-Language') as 'en' | 'ta' | 'hi' || currentLanguage;

      // Create blob URL for audio
      const audioBlob = new Blob([audioBuffer], { type: 'audio/wav' });
      const audioUrl = URL.createObjectURL(audioBlob);

      const voiceMessage: VoiceMessage = {
        type: 'voice_input',
        content: decodeURIComponent(transcript),
        audioUrl,
        transcript: decodeURIComponent(transcript),
        language: currentLanguage,
        duration,
        timestamp: new Date().toISOString(),
      };

      // Add response message
      const responseMessage: VoiceMessage = {
        type: 'voice_output',
        content: decodeURIComponent(reply),
        audioUrl,
        transcript: decodeURIComponent(reply),
        language: responseLanguage,
        duration: undefined,
        timestamp: new Date().toISOString(),
      };

      setVoiceMessages(prev => [...prev, voiceMessage, responseMessage]);

      return voiceMessage;
    } catch (err) {
      const voiceError = err instanceof Error
        ? createVoiceError(classifyError(err), currentLanguage, err)
        : createVoiceError('unknown', currentLanguage);
      setError(voiceError.userMessage);
      return null;
    }
  }, [currentLanguage]);

  const addVoiceMessage = useCallback((message: VoiceMessage) => {
    setVoiceMessages(prev => [...prev, message]);
  }, []);

  return {
    isRecording,
    isPlaying,
    currentLanguage,
    preferences,
    voiceMessages,
    error,
    startRecording,
    stopRecording,
    playVoiceMessage,
    pausePlayback,
    setLanguage,
    toggleVoiceMode,
    sendVoiceMessage,
    addVoiceMessage,
    clearError,
  };
}
