import { useState, useRef, useEffect } from 'react';
import './voice-player.css';

export function VoicePlayer({ audioUrl, transcript, language = 'en', showTranscript = true }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const audioRef = useRef(null);

  useEffect(() => {
    const audio = new Audio(audioUrl);

    audio.onloadedmetadata = () => {
      setDuration(audio.duration);
    };

    audio.ontimeupdate = () => {
      setCurrentTime(audio.currentTime);
    };

    audio.onended = () => {
      setIsPlaying(false);
    };

    audio.onerror = (e) => {
      setError('Failed to load audio');
      console.error('Audio error:', e);
    };

    audioRef.current = audio;

    return () => {
      audio.pause();
    };
  }, [audioUrl]);

  const togglePlayback = async () => {
    if (!audioRef.current) return;

    try {
      setIsLoading(true);

      if (isPlaying) {
        audioRef.current.pause();
        setIsPlaying(false);
      } else {
        await audioRef.current.play();
        setIsPlaying(true);
      }
    } catch (err) {
      setError('Playback failed');
      console.error('Playback error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleProgressChange = (e) => {
    const newTime = parseFloat(e.target.value);
    if (audioRef.current) {
      audioRef.current.currentTime = newTime;
      setCurrentTime(newTime);
    }
  };

  const formatTime = (seconds) => {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const languageLabels = {
    en: 'English',
    ta: 'Tamil',
    hi: 'Hindi'
  };

  return (
    <div className="voice-player">
      <div className="player-header">
        <div className="language-badge">
          {languageLabels[language] || language}
        </div>
      </div>

      <div className="player-controls">
        <button
          onClick={togglePlayback}
          className={`play-button ${isPlaying ? 'playing' : ''} ${isLoading ? 'loading' : ''}`}
          disabled={isLoading || error}
          title={isPlaying ? 'Pause' : 'Play'}
        >
          {isLoading ? '⏳' : isPlaying ? '⏸️' : '▶️'}
        </button>

        <div className="progress-container">
          <input
            type="range"
            min="0"
            max={duration || 0}
            value={currentTime}
            onChange={handleProgressChange}
            className="progress-bar"
            disabled={!duration}
          />
          <div className="time-display">
            <span className="current-time">{formatTime(currentTime)}</span>
            <span className="duration">{formatTime(duration)}</span>
          </div>
        </div>
      </div>

      {error && (
        <div className="error-message">
          ⚠️ {error}
        </div>
      )}

      {showTranscript && transcript && (
        <div className="transcript-section">
          <p className="transcript-label">Transcript:</p>
          <p className="transcript-text">"{transcript}"</p>
        </div>
      )}
    </div>
  );
}
