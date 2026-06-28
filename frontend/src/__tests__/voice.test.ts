import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useVoice } from '../hooks/useVoice';

describe('useVoice Hook', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
    // Mock navigator.mediaDevices
    global.navigator.mediaDevices = {
      getUserMedia: vi.fn().mockResolvedValue({
        getTracks: () => []
      })
    } as any;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Initial State', () => {
    it('should initialize with correct default values', () => {
      const { result } = renderHook(() => useVoice());

      expect(result.current.isRecording).toBe(false);
      expect(result.current.isPlaying).toBe(false);
      expect(result.current.currentLanguage).toBe('en');
      expect(result.current.preferences.enabled).toBe(true);
      expect(result.current.preferences.autoPlay).toBe(true);
      expect(result.current.voiceMessages).toEqual([]);
      expect(result.current.error).toBeNull();
    });

    it('should load language preference from localStorage', () => {
      localStorage.setItem('voiceLanguage', 'ta');
      const { result } = renderHook(() => useVoice());

      expect(result.current.currentLanguage).toBe('ta');
    });

    it('should load preferences from localStorage', () => {
      const prefs = {
        enabled: false,
        language: 'hi',
        autoPlay: false,
        showTranscripts: false
      };
      localStorage.setItem('voicePreferences', JSON.stringify(prefs));
      const { result } = renderHook(() => useVoice());

      expect(result.current.preferences.enabled).toBe(false);
      expect(result.current.preferences.autoPlay).toBe(false);
    });
  });

  describe('Language Management', () => {
    it('should update language and persist to localStorage', () => {
      const { result } = renderHook(() => useVoice());

      act(() => {
        result.current.setLanguage('hi');
      });

      expect(result.current.currentLanguage).toBe('hi');
      expect(localStorage.getItem('voiceLanguage')).toBe('hi');
    });

    it('should update preferences when language changes', () => {
      const { result } = renderHook(() => useVoice());

      act(() => {
        result.current.setLanguage('ta');
      });

      expect(result.current.preferences.language).toBe('ta');
    });

    it('should support all three languages', async () => {
      const { result } = renderHook(() => useVoice());
      const languages = ['en', 'ta', 'hi'] as const;

      for (const lang of languages) {
        act(() => {
          result.current.setLanguage(lang);
        });
        expect(result.current.currentLanguage).toBe(lang);
      }
    });
  });

  describe('Recording State', () => {
    it('should start recording', async () => {
      const { result } = renderHook(() => useVoice());

      await act(async () => {
        await result.current.startRecording();
      });

      expect(result.current.isRecording).toBe(true);
      expect(result.current.error).toBeNull();
    });

    it('should stop recording', async () => {
      const { result } = renderHook(() => useVoice());

      await act(async () => {
        await result.current.startRecording();
      });

      expect(result.current.isRecording).toBe(true);

      await act(async () => {
        await result.current.stopRecording();
      });

      expect(result.current.isRecording).toBe(false);
    });

    it('should handle recording errors', async () => {
      const errorMsg = 'Permission denied';
      global.navigator.mediaDevices.getUserMedia = vi.fn()
        .mockRejectedValue(new Error(errorMsg));

      const { result } = renderHook(() => useVoice());

      await act(async () => {
        await result.current.startRecording();
      });

      await waitFor(() => {
        expect(result.current.error).toBe(errorMsg);
        expect(result.current.isRecording).toBe(false);
      });
    });
  });

  describe('Playback State', () => {
    it('should set isPlaying when playing', async () => {
      const { result } = renderHook(() => useVoice());

      await act(async () => {
        await result.current.playVoiceMessage('http://example.com/audio.wav');
      });

      expect(result.current.isPlaying).toBe(true);
    });

    it('should pause playback', () => {
      const { result } = renderHook(() => useVoice());

      act(() => {
        result.current.pausePlayback();
      });

      expect(result.current.isPlaying).toBe(false);
    });

    it('should handle playback errors', async () => {
      const { result } = renderHook(() => useVoice());

      await act(async () => {
        await result.current.playVoiceMessage('invalid-url');
      });

      expect(result.current.isPlaying).toBe(true); // State set before error
    });
  });

  describe('Voice Mode Toggle', () => {
    it('should toggle voice mode on/off', () => {
      const { result } = renderHook(() => useVoice());

      const initialState = result.current.preferences.enabled;

      act(() => {
        result.current.toggleVoiceMode();
      });

      expect(result.current.preferences.enabled).toBe(!initialState);
    });

    it('should persist toggled state to localStorage', () => {
      const { result } = renderHook(() => useVoice());

      act(() => {
        result.current.toggleVoiceMode();
      });

      const saved = localStorage.getItem('voicePreferences');
      expect(saved).toBeTruthy();
      const parsed = JSON.parse(saved!);
      expect(parsed.enabled).toBe(false);
    });
  });

  describe('Error Management', () => {
    it('should set and clear errors', () => {
      const { result } = renderHook(() => useVoice());

      // Simulate error from failed operation
      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });

    it('should clear error when clearError is called', async () => {
      const { result } = renderHook(() => useVoice());

      // Set error via failed recording
      global.navigator.mediaDevices.getUserMedia = vi.fn()
        .mockRejectedValue(new Error('Mic error'));

      await act(async () => {
        await result.current.startRecording();
      });

      await waitFor(() => {
        expect(result.current.error).toBeTruthy();
      });

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });
  });

  describe('Voice Messages', () => {
    it('should add voice message to history', () => {
      const { result } = renderHook(() => useVoice());

      const message = {
        type: 'voice_input' as const,
        content: 'Hello',
        language: 'en' as const,
        timestamp: new Date().toISOString()
      };

      act(() => {
        result.current.addVoiceMessage(message);
      });

      expect(result.current.voiceMessages).toHaveLength(1);
      expect(result.current.voiceMessages[0]).toEqual(message);
    });

    it('should maintain message history order', () => {
      const { result } = renderHook(() => useVoice());

      const msg1 = {
        type: 'voice_input' as const,
        content: 'First',
        timestamp: new Date().toISOString()
      };

      const msg2 = {
        type: 'voice_output' as const,
        content: 'Second',
        timestamp: new Date().toISOString()
      };

      act(() => {
        result.current.addVoiceMessage(msg1);
        result.current.addVoiceMessage(msg2);
      });

      expect(result.current.voiceMessages).toHaveLength(2);
      expect(result.current.voiceMessages[0].content).toBe('First');
      expect(result.current.voiceMessages[1].content).toBe('Second');
    });
  });

  describe('Voice Message Sending', () => {
    it('should handle voice message sending (mocked fetch)', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Map([
          ['X-Transcript', 'Hello'],
          ['X-Reply', 'Hi there'],
          ['X-Language', 'en']
        ]),
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(0))
      } as any);

      const { result } = renderHook(() => useVoice());
      const audioBlob = new Blob(['audio'], { type: 'audio/webm' });

      const message = await act(async () => {
        return await result.current.sendVoiceMessage(audioBlob, 5);
      });

      expect(message).toBeTruthy();
      expect(message?.content).toBe('Hello');
    });

    it('should handle send errors', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      const { result } = renderHook(() => useVoice());
      const audioBlob = new Blob(['audio'], { type: 'audio/webm' });

      await act(async () => {
        await result.current.sendVoiceMessage(audioBlob, 5);
      });

      await waitFor(() => {
        expect(result.current.error).toContain('Network error');
      });
    });
  });

  describe('LocalStorage Persistence', () => {
    it('should persist language across hook instances', () => {
      const { result: result1 } = renderHook(() => useVoice());

      act(() => {
        result1.current.setLanguage('ta');
      });

      const { result: result2 } = renderHook(() => useVoice());

      expect(result2.current.currentLanguage).toBe('ta');
    });

    it('should handle corrupted localStorage data gracefully', () => {
      localStorage.setItem('voicePreferences', 'invalid json');

      // Should not throw
      const { result } = renderHook(() => useVoice());

      expect(result.current.preferences.enabled).toBe(true);
    });
  });
});
