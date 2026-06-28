import { useState, useRef, useEffect } from 'react';
import './voice-recorder.css';

export function VoiceRecorder({ onRecordingComplete, language = 'en', isEnabled = true }) {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0);
  const [error, setError] = useState(null);

  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const timerRef = useRef(null);
  const chunksRef = useRef([]);

  const startRecording = async () => {
    try {
      setError(null);

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      // Set up audio analysis for visual feedback
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;

      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);

      // Create MediaRecorder for WebM format
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' });
        onRecordingComplete(audioBlob, recordingTime);

        // Clean up
        stream.getTracks().forEach(track => track.stop());
        setRecordingTime(0);
      };

      mediaRecorder.start();
      setIsRecording(true);

      // Start recording timer and audio level monitoring
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);

        // Update audio level visualization
        if (analyserRef.current) {
          const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
          analyserRef.current.getByteFrequencyData(dataArray);
          const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
          setAudioLevel(average / 255);
        }
      }, 100);

    } catch (err) {
      setError(err.message);
      console.error('Recording error:', err);
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);

      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }
  };

  useEffect(() => {
    // Cleanup on unmount
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      if (mediaRecorderRef.current && isRecording) {
        mediaRecorderRef.current.stop();
      }
    };
  }, [isRecording]);

  if (!isEnabled) {
    return null;
  }

  return (
    <div className="voice-recorder">
      <button
        onClick={isRecording ? stopRecording : startRecording}
        className={`voice-button ${isRecording ? 'recording' : ''}`}
        title={isRecording ? 'Stop recording' : 'Start recording'}
        disabled={!isEnabled}
      >
        <span className="voice-icon">🎤</span>
        <span className="voice-label">{isRecording ? 'Stop' : 'Voice'}</span>
      </button>

      {isRecording && (
        <div className="recording-indicator">
          <div className="waveform">
            {Array.from({ length: 12 }).map((_, i) => (
              <div
                key={i}
                className="waveform-bar"
                style={{
                  height: `${Math.sin(i + audioLevel * 10) * 50 + 50}%`,
                  animationDelay: `${i * 50}ms`
                }}
              />
            ))}
          </div>
          <span className="recording-time">{recordingTime}s</span>
        </div>
      )}

      {error && (
        <div className="error-message">
          ⚠️ {error}
        </div>
      )}
    </div>
  );
}
