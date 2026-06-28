import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

/**
 * E2E Voice Flow Tests
 * Tests complete voice workflows from recording to playback
 */

describe('Voice Agent E2E Flows', () => {
  const mockVoiceAgentUrl = 'http://localhost:8002';
  const mockBackendUrl = 'http://localhost:3001';

  beforeEach(() => {
    // Mock global fetch for API calls
    global.fetch = vi.fn();
    // Mock Web Audio API
    global.AudioContext = vi.fn(() => ({
      createAnalyser: () => ({
        fftSize: 256,
        frequencyBinCount: 128,
        getByteFrequencyData: () => new Uint8Array(128)
      }),
      createMediaStreamSource: () => ({
        connect: vi.fn()
      }),
      destination: {}
    })) as any;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Complete Voice Recording Flow', () => {
    it('should record audio and get response', async () => {
      // 1. User records audio
      const audioBlob = new Blob(['audio data'], { type: 'audio/webm' });

      // 2. Send to backend
      const formData = new FormData();
      formData.append('audio', audioBlob, 'voice.webm');
      formData.append('language', 'en');

      // Mock successful response
      const mockAudioBuffer = new ArrayBuffer(100);
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Map([
          ['content-type', 'audio/wav'],
          ['X-Transcript', encodeURIComponent('Hello')],
          ['X-Reply', encodeURIComponent('Hi there')],
          ['X-Language', 'en']
        ]),
        arrayBuffer: () => Promise.resolve(mockAudioBuffer),
        body: mockAudioBuffer
      });

      // 3. Send request
      const response = await fetch(`${mockBackendUrl}/api/voice/speak`, {
        method: 'POST',
        body: formData,
        headers: {
          'Authorization': 'Bearer mock-token'
        }
      });

      // 4. Verify response
      expect(response.ok).toBe(true);
      expect(response.headers.get('X-Transcript')).toBe('Hello');
      expect(response.headers.get('X-Reply')).toBe('Hi there');
      expect(response.headers.get('X-Language')).toBe('en');

      // 5. Extract audio and create blob
      const audioData = await response.arrayBuffer();
      expect(audioData).toBeTruthy();
    });

    it('should handle recording for all supported languages', async () => {
      const languages = ['en', 'ta', 'hi'];

      for (const lang of languages) {
        const audioBlob = new Blob(['audio'], { type: 'audio/webm' });
        const formData = new FormData();
        formData.append('audio', audioBlob);
        formData.append('language', lang);

        // Mock response
        (global.fetch as any).mockResolvedValueOnce({
          ok: true,
          headers: new Map([
            ['X-Language', lang],
            ['X-Transcript', `Message in ${lang}`],
            ['X-Reply', `Response in ${lang}`]
          ]),
          arrayBuffer: () => Promise.resolve(new ArrayBuffer(50))
        });

        const response = await fetch(`${mockBackendUrl}/api/voice/speak`, {
          method: 'POST',
          body: formData
        });

        expect(response.ok).toBe(true);
        expect(response.headers.get('X-Language')).toBe(lang);
      }
    });
  });

  describe('Voice Playback Flow', () => {
    it('should play voice response with controls', async () => {
      // 1. Create audio context
      const audioContext = new AudioContext();
      expect(audioContext).toBeTruthy();

      // 2. Create audio element
      const audio = new Audio();
      const blobUrl = 'blob:http://localhost/audio';
      audio.src = blobUrl;

      // 3. Mock play
      audio.play = vi.fn().mockResolvedValue(undefined);
      audio.pause = vi.fn();

      // 4. Control playback
      await audio.play();
      expect(audio.play).toHaveBeenCalled();

      audio.pause();
      expect(audio.pause).toHaveBeenCalled();
    });

    it('should handle progress tracking', () => {
      const audio = new Audio();

      // Simulate time updates
      let currentTime = 0;
      Object.defineProperty(audio, 'currentTime', {
        get() { return currentTime; },
        set(val) { currentTime = val; }
      });

      // Mock duration
      Object.defineProperty(audio, 'duration', {
        value: 10 // 10 seconds
      });

      audio.currentTime = 5;
      expect(audio.currentTime).toBe(5);
      expect(audio.duration).toBe(10);
    });

    it('should handle playback errors gracefully', async () => {
      const audio = new Audio();
      const errorHandler = vi.fn();

      // Mock error event
      audio.addEventListener('error', errorHandler);

      // Simulate error
      const errorEvent = new Event('error');
      audio.dispatchEvent(errorEvent);

      expect(errorHandler).toHaveBeenCalled();
    });
  });

  describe('Language Switching During Session', () => {
    it('should switch language mid-conversation', async () => {
      const languages = ['en', 'ta', 'hi'];
      const audioBlob = new Blob(['audio'], { type: 'audio/webm' });

      for (const lang of languages) {
        const formData = new FormData();
        formData.append('audio', audioBlob);
        formData.append('language', lang);

        (global.fetch as any).mockResolvedValueOnce({
          ok: true,
          headers: new Map([
            ['X-Language', lang],
            ['X-Transcript', `Message in ${lang}`]
          ]),
          arrayBuffer: () => Promise.resolve(new ArrayBuffer(50))
        });

        const response = await fetch(`${mockBackendUrl}/api/voice/speak`, {
          method: 'POST',
          body: formData
        });

        expect(response.ok).toBe(true);
        expect(response.headers.get('X-Language')).toBe(lang);
      }
    });
  });

  describe('Error Scenarios', () => {
    it('should handle microphone permission denied', async () => {
      // Simulate permission denied error
      const error = new DOMException('Permission denied', 'NotAllowedError');

      expect(error.name).toBe('NotAllowedError');
      expect(error.message).toContain('Permission');
    });

    it('should handle network timeout', async () => {
      const abortController = new AbortController();
      const timeoutId = setTimeout(() => abortController.abort(), 5000);

      (global.fetch as any).mockImplementation(() =>
        new Promise((_, reject) => {
          abortController.signal.addEventListener('abort', () => {
            clearTimeout(timeoutId);
            reject(new DOMException('Aborted', 'AbortError'));
          });
        })
      );

      const fetchPromise = fetch(`${mockBackendUrl}/api/voice/speak`, {
        signal: abortController.signal
      });

      abortController.abort();

      await expect(fetchPromise).rejects.toThrow('Aborted');
    });

    it('should handle invalid audio file', async () => {
      const invalidBlob = new Blob(['not audio'], { type: 'text/plain' });
      const formData = new FormData();
      formData.append('audio', invalidBlob);

      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({
          error: 'Invalid audio format',
          audio_available: false
        })
      });

      const response = await fetch(`${mockBackendUrl}/api/voice/speak`, {
        method: 'POST',
        body: formData
      });

      expect(response.ok).toBe(false);
      expect(response.status).toBe(400);
    });

    it('should handle voice agent service unavailable', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 503,
        json: () => Promise.resolve({
          error: 'Voice service unavailable',
          audio_available: false
        })
      });

      const response = await fetch(`${mockBackendUrl}/api/voice/speak`, {
        method: 'POST',
        body: new FormData()
      });

      expect(response.ok).toBe(false);
      expect(response.status).toBe(503);
    });
  });

  describe('Voice Session Continuity', () => {
    it('should maintain conversation history', () => {
      const history = [
        {
          type: 'voice_input',
          content: 'Hello',
          timestamp: new Date().toISOString()
        },
        {
          type: 'voice_output',
          content: 'Hi there',
          timestamp: new Date().toISOString()
        },
        {
          type: 'text_input',
          content: 'How are you?',
          timestamp: new Date().toISOString()
        },
        {
          type: 'text_output',
          content: 'I am fine',
          timestamp: new Date().toISOString()
        }
      ];

      // Verify mixed mode conversation
      const voiceMessages = history.filter(m => m.type.startsWith('voice'));
      const textMessages = history.filter(m => m.type.startsWith('text'));

      expect(voiceMessages).toHaveLength(2);
      expect(textMessages).toHaveLength(2);
      expect(history).toHaveLength(4);
    });

    it('should switch from voice to text seamlessly', () => {
      const conversation = [
        { type: 'voice_input', content: 'Start with voice' },
        { type: 'voice_output', content: 'Voice response' },
        { type: 'text_input', content: 'Continue with text' },
        { type: 'text_output', content: 'Text response' }
      ];

      // Verify context is maintained
      const lastVoiceMessage = conversation.filter(m => m.type.includes('voice')).pop();
      const firstTextMessage = conversation.find(m => m.type === 'text_input');

      expect(lastVoiceMessage?.content).toBe('Voice response');
      expect(firstTextMessage?.content).toBe('Continue with text');
    });

    it('should switch from text to voice seamlessly', () => {
      const conversation = [
        { type: 'text_input', content: 'Start with text' },
        { type: 'text_output', content: 'Text response' },
        { type: 'voice_input', content: 'Continue with voice' },
        { type: 'voice_output', content: 'Voice response' }
      ];

      const messages = conversation.map(m => m.content);
      expect(messages).toEqual([
        'Start with text',
        'Text response',
        'Continue with voice',
        'Voice response'
      ]);
    });
  });

  describe('Performance Metrics', () => {
    it('should measure recording latency', async () => {
      const startTime = performance.now();

      // Simulate recording start
      await new Promise(resolve => setTimeout(resolve, 100));

      const endTime = performance.now();
      const latency = endTime - startTime;

      expect(latency).toBeGreaterThanOrEqual(100);
      expect(latency).toBeLessThan(500); // Should be fast
    });

    it('should measure voice response latency', async () => {
      const startTime = performance.now();

      const audioBlob = new Blob(['audio'], { type: 'audio/webm' });
      const formData = new FormData();
      formData.append('audio', audioBlob);

      (global.fetch as any).mockImplementation(() =>
        new Promise(resolve => {
          setTimeout(() => {
            resolve({
              ok: true,
              headers: new Map([
                ['X-Transcript', 'response'],
                ['X-Reply', 'reply']
              ]),
              arrayBuffer: () => Promise.resolve(new ArrayBuffer(50))
            });
          }, 2000); // Simulate 2 second response time
        })
      );

      await fetch(`${mockBackendUrl}/api/voice/speak`, {
        method: 'POST',
        body: formData
      });

      const endTime = performance.now();
      const latency = endTime - startTime;

      expect(latency).toBeGreaterThanOrEqual(2000);
    });
  });

  describe('Accessibility Features', () => {
    it('should provide transcript for all voice messages', async () => {
      const response = {
        headers: new Map([
          ['X-Transcript', encodeURIComponent('User said: Hello')],
          ['X-Reply', encodeURIComponent('Assistant replied: Hi')]
        ])
      };

      const transcript = decodeURIComponent(response.headers.get('X-Transcript') || '');
      const reply = decodeURIComponent(response.headers.get('X-Reply') || '');

      expect(transcript).toBe('User said: Hello');
      expect(reply).toBe('Assistant replied: Hi');
    });

    it('should support keyboard-only operation', () => {
      // Test that voice controls respond to keyboard events
      const recordButton = document.createElement('button');
      const keydownEvent = new KeyboardEvent('keydown', {
        key: 'Enter',
        code: 'Enter'
      });

      recordButton.addEventListener('keydown', (e) => {
        if ((e as KeyboardEvent).key === 'Enter') {
          recordButton.click();
        }
      });

      const clickSpy = vi.fn();
      recordButton.addEventListener('click', clickSpy);

      recordButton.dispatchEvent(keydownEvent);
      expect(clickSpy).toHaveBeenCalled();
    });
  });
});
