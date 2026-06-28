import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  createVoiceError,
  classifyError,
  retryWithBackoff,
  checkBrowserSupport,
  handleApiError
} from '../lib/voice-error-handler';
import {
  voiceAnalytics,
  checkPerformanceThresholds,
  performanceThresholds
} from '../lib/voice-analytics';
import {
  voiceDegradationManager,
  voiceServiceBreaker
} from '../lib/voice-degradation';

/**
 * Comprehensive Voice Integration Tests
 * Tests error handling, analytics, degradation, and circuit breaker
 */

describe('Voice Error Handling', () => {
  it('should classify DOMException errors correctly', () => {
    const permissionError = new DOMException('Permission denied', 'NotAllowedError');
    expect(classifyError(permissionError)).toBe('microphone_denied');

    const notFoundError = new DOMException('Not found', 'NotFoundError');
    expect(classifyError(notFoundError)).toBe('microphone_not_found');

    const abortError = new DOMException('Aborted', 'AbortError');
    expect(classifyError(abortError)).toBe('recording_failed');
  });

  it('should classify Error objects correctly', () => {
    expect(classifyError(new Error('network error'))).toBe('network_error');
    expect(classifyError(new Error('timeout error'))).toBe('network_timeout');
    expect(classifyError(new Error('STT failed'))).toBe('stt_failed');
    expect(classifyError(new Error('TTS failed'))).toBe('tts_failed');
    expect(classifyError(new Error('invalid audio'))).toBe('invalid_audio');
    expect(classifyError(new Error('503 unavailable'))).toBe('service_unavailable');
  });

  it('should create voice errors with multilingual messages', () => {
    const error_en = createVoiceError('microphone_denied', 'en');
    expect(error_en.message).toContain('Microphone');

    const error_ta = createVoiceError('microphone_denied', 'ta');
    expect(error_ta.message.length > 0).toBe(true);

    const error_hi = createVoiceError('microphone_denied', 'hi');
    expect(error_hi.message.length > 0).toBe(true);
  });

  it('should handle API error codes', () => {
    expect(handleApiError(400)).toBe('invalid_audio');
    expect(handleApiError(403)).toBe('microphone_denied');
    expect(handleApiError(408)).toBe('network_timeout');
    expect(handleApiError(503)).toBe('service_unavailable');
    expect(handleApiError(500)).toBe('service_unavailable');
  });

  it('should mark errors as retryable or not', () => {
    const retryableError = createVoiceError('network_timeout');
    expect(retryableError.retryable).toBe(true);

    const notRetryableError = createVoiceError('unsupported_browser');
    expect(notRetryableError.retryable).toBe(false);
  });
});

describe('Retry with Backoff', () => {
  it('should retry and succeed', async () => {
    let attempts = 0;
    const fn = async () => {
      attempts++;
      if (attempts < 2) throw new Error('Try again');
      return 'success';
    };

    const result = await retryWithBackoff(fn, 3);
    expect(result).toBe('success');
    expect(attempts).toBe(2);
  });

  it('should exhaust retries and throw', async () => {
    let attempts = 0;
    const fn = async () => {
      attempts++;
      throw new Error('Always fails');
    };

    await expect(retryWithBackoff(fn, 3)).rejects.toThrow('Always fails');
    expect(attempts).toBe(3);
  });

  it('should call retry callback', async () => {
    const retryCallback = vi.fn();
    let attempts = 0;

    const fn = async () => {
      attempts++;
      if (attempts < 3) throw new Error('Retry');
      return 'success';
    };

    await retryWithBackoff(fn, 3, retryCallback);
    expect(retryCallback).toHaveBeenCalledTimes(2);
  });
});

describe('Browser Support', () => {
  beforeEach(() => {
    // Assume browser supports all features by default
    global.navigator.mediaDevices = { getUserMedia: () => {} } as any;
    (global as any).MediaRecorder = class {};
    (global as any).AudioContext = class {};
    (global as any).fetch = () => {};
  });

  it('should detect supported browser', () => {
    const { supported, issues } = checkBrowserSupport();
    expect(supported).toBe(true);
    expect(issues).toEqual([]);
  });

  it('should detect missing getUserMedia', () => {
    delete (global.navigator as any).mediaDevices;
    const { supported, issues } = checkBrowserSupport();
    expect(supported).toBe(false);
    expect(issues.some(i => i.includes('getUserMedia'))).toBe(true);
  });

  it('should detect missing MediaRecorder', () => {
    delete (global as any).MediaRecorder;
    const { supported, issues } = checkBrowserSupport();
    expect(supported).toBe(false);
    expect(issues.some(i => i.includes('MediaRecorder'))).toBe(true);
  });
});

describe('Voice Analytics', () => {
  beforeEach(() => {
    voiceAnalytics.clear();
  });

  it('should measure operation timing', () => {
    voiceAnalytics.startTimer('recording');
    
    // Simulate some time passing
    const start = Date.now();
    while (Date.now() - start < 100) {}
    
    const latency = voiceAnalytics.endTimer('recording');
    expect(latency).toBeGreaterThanOrEqual(100);
  });

  it('should track voice events', () => {
    voiceAnalytics.recordEvent({
      type: 'recording_start',
      timestamp: Date.now(),
      language: 'en'
    });

    voiceAnalytics.recordEvent({
      type: 'recording_stop',
      timestamp: Date.now(),
      language: 'en',
      duration: 5000
    });

    const events = voiceAnalytics.getEvents();
    expect(events).toHaveLength(2);
    expect(events[0].type).toBe('recording_start');
  });

  it('should update success rate', () => {
    voiceAnalytics.updateSuccessRate(true);
    voiceAnalytics.updateSuccessRate(true);
    voiceAnalytics.updateSuccessRate(false);

    const metrics = voiceAnalytics.getMetrics();
    expect(metrics.successRate).toBeLessThan(100);
    expect(metrics.errorRate).toBeGreaterThan(0);
  });

  it('should set audio quality', () => {
    voiceAnalytics.setAudioQuality(95);
    expect(voiceAnalytics.getMetrics().audioQuality).toBe(95);

    voiceAnalytics.setAudioQuality(150); // Out of range
    expect(voiceAnalytics.getMetrics().audioQuality).toBe(100);
  });

  it('should generate performance report', () => {
    voiceAnalytics.recordEvent({
      type: 'recording_start',
      timestamp: Date.now()
    });

    const report = voiceAnalytics.generateReport();
    expect(report).toContain('Voice Performance Report');
    expect(report).toContain('Session ID');
    expect(report).toContain('Generated');
  });

  it('should check performance thresholds', () => {
    const metrics = {
      recordingLatency: 100,
      audioProcessingTime: 50,
      voiceResponseLatency: 3000,
      playbackStartLatency: 100,
      sttLatency: 1000,
      ttsLatency: 1000,
      totalVoiceLatency: 4000,
      audioQuality: 95,
      successRate: 98,
      errorRate: 2,
      averageRecordingDuration: 5000
    };

    const check = checkPerformanceThresholds(metrics);
    expect(check.passed).toBe(true);
    expect(check.issues).toEqual([]);
  });

  it('should detect performance issues', () => {
    const metrics = {
      recordingLatency: 1000,         // Too slow
      audioProcessingTime: 50,
      voiceResponseLatency: 10000,    // Too slow
      playbackStartLatency: 100,
      sttLatency: 1000,
      ttsLatency: 1000,
      totalVoiceLatency: 15000,       // Too slow
      audioQuality: 60,               // Too low
      successRate: 90,                // Too low
      errorRate: 10,
      averageRecordingDuration: 5000
    };

    const check = checkPerformanceThresholds(metrics);
    expect(check.passed).toBe(false);
    expect(check.issues.length).toBeGreaterThan(0);
  });
});

describe('Voice Service Degradation', () => {
  beforeEach(() => {
    voiceDegradationManager.reset();
  });

  it('should start in full service mode', () => {
    const config = voiceDegradationManager.getConfig();
    expect(config.level).toBe('FULL_SERVICE');
    expect(config.sttEnabled).toBe(true);
    expect(config.ttsEnabled).toBe(true);
  });

  it('should degrade on high error rate', () => {
    // Simulate many errors
    for (let i = 0; i < 30; i++) {
      voiceDegradationManager.recordError();
    }

    const level = voiceDegradationManager.getLevel();
    expect(level).not.toBe('FULL_SERVICE');
  });

  it('should recover when errors decrease', () => {
    // First degrade
    for (let i = 0; i < 30; i++) {
      voiceDegradationManager.recordError();
    }
    expect(voiceDegradationManager.getLevel()).not.toBe('FULL_SERVICE');

    // Then record successes
    for (let i = 0; i < 100; i++) {
      voiceDegradationManager.recordSuccess(3000);
    }

    // Should eventually recover
    const level = voiceDegradationManager.getLevel();
    expect(['FULL_SERVICE', 'DEGRADED_SERVICE']).toContain(level);
  });

  it('should notify subscribers of level changes', () => {
    const callback = vi.fn();
    voiceDegradationManager.onDegradationChange(callback);

    voiceDegradationManager.setLevel('DEGRADED_SERVICE');
    expect(callback).toHaveBeenCalledWith('DEGRADED_SERVICE');
  });

  it('should track concurrent users', () => {
    voiceDegradationManager.setConcurrentUsers(50);
    expect(voiceDegradationManager.getMetrics().concurrentUsers).toBe(50);

    // High user load might degrade service
    voiceDegradationManager.setConcurrentUsers(150);
    // Should remain or degrade
  });

  it('should generate health report', () => {
    const report = voiceDegradationManager.getHealthReport();
    expect(report).toContain('Voice Service Health Report');
    expect(report).toContain('Current Level');
    expect(report).toContain('Error Rate');
  });
});

describe('Circuit Breaker', () => {
  beforeEach(() => {
    voiceServiceBreaker.reset();
  });

  it('should execute successful operations', async () => {
    const fn = vi.fn().mockResolvedValue('success');
    const result = await voiceServiceBreaker.execute(fn);

    expect(result).toBe('success');
    expect(fn).toHaveBeenCalled();
  });

  it('should track failures', async () => {
    const fn = vi.fn().mockRejectedValue(new Error('Failed'));

    for (let i = 0; i < 5; i++) {
      try {
        await voiceServiceBreaker.execute(fn);
      } catch (err) {
        // Expected
      }
    }

    expect(voiceServiceBreaker.getState()).toBe('OPEN');
  });

  it('should reject requests when open', async () => {
    const fn = vi.fn().mockRejectedValue(new Error('Failed'));

    // Open the circuit
    for (let i = 0; i < 5; i++) {
      try {
        await voiceServiceBreaker.execute(fn);
      } catch (err) {
        // Expected
      }
    }

    // Try to execute when open
    await expect(voiceServiceBreaker.execute(() => Promise.resolve('ok')))
      .rejects.toThrow('Circuit breaker is OPEN');
  });

  it('should attempt half-open state after timeout', async () => {
    const fn = vi.fn().mockRejectedValue(new Error('Failed'));

    // Open the circuit
    for (let i = 0; i < 5; i++) {
      try {
        await voiceServiceBreaker.execute(fn);
      } catch (err) {
        // Expected
      }
    }

    // Wait and attempt
    await new Promise(resolve => setTimeout(resolve, 100));

    const successFn = vi.fn().mockResolvedValue('recovered');
    const result = await voiceServiceBreaker.execute(successFn);

    expect(result).toBe('recovered');
    expect(voiceServiceBreaker.getState()).toBe('CLOSED');
  });

  it('should reset circuit breaker', () => {
    expect(voiceServiceBreaker.getState()).toBe('CLOSED');

    voiceServiceBreaker.reset();
    expect(voiceServiceBreaker.getState()).toBe('CLOSED');
  });
});

describe('End-to-End Voice Pipeline', () => {
  beforeEach(() => {
    voiceAnalytics.clear();
    voiceDegradationManager.reset();
    voiceServiceBreaker.reset();
  });

  it('should track complete voice message pipeline', async () => {
    // Start recording
    voiceAnalytics.startTimer('recording');
    await new Promise(r => setTimeout(r, 100));
    voiceAnalytics.endTimer('recording');

    // Audio processing
    voiceAnalytics.startTimer('audio_processing');
    await new Promise(r => setTimeout(r, 50));
    voiceAnalytics.endTimer('audio_processing');

    // Send and receive
    voiceAnalytics.startTimer('voice_response');
    voiceServiceBreaker.execute(() => {
      voiceDegradationManager.recordSuccess(2000);
      return Promise.resolve({ text: 'response' });
    });
    await new Promise(r => setTimeout(r, 2000));
    voiceAnalytics.endTimer('voice_response');

    // Check metrics
    const metrics = voiceAnalytics.getMetrics();
    expect(metrics.recordingLatency).toBeGreaterThan(0);
    expect(metrics.audioProcessingTime).toBeGreaterThan(0);
    expect(metrics.voiceResponseLatency).toBeGreaterThan(0);
  });

  it('should handle errors gracefully in pipeline', async () => {
    const fn = async () => {
      throw new Error('Pipeline error');
    };

    try {
      await voiceServiceBreaker.execute(fn);
    } catch (err) {
      voiceDegradationManager.recordError();
      voiceAnalytics.recordEvent({
        type: 'error',
        timestamp: Date.now(),
        errorType: 'pipeline_error'
      });
    }

    const metrics = voiceAnalytics.getMetrics();
    expect(metrics.errorRate).toBeGreaterThan(0);
  });
});
