import { useState } from 'react';
import './voice-language-selector.css';

export function VoiceLanguageSelector({ currentLanguage = 'en', onLanguageChange }) {
  const [isOpen, setIsOpen] = useState(false);

  const languages = [
    { 
      code: 'en', 
      name: 'English', 
      nativeName: 'English',
      icon: '🇬🇧'
    },
    { 
      code: 'ta', 
      name: 'Tamil', 
      nativeName: 'தமிழ்',
      icon: '🇮🇳'
    },
    { 
      code: 'hi', 
      name: 'Hindi', 
      nativeName: 'हिन्दी',
      icon: '🇮🇳'
    }
  ];

  const currentLang = languages.find(l => l.code === currentLanguage) || languages[0];

  const handleLanguageSelect = (code) => {
    onLanguageChange(code);
    setIsOpen(false);
    
    // Save preference to localStorage
    localStorage.setItem('voiceLanguage', code);
  };

  return (
    <div className="voice-language-selector">
      <div className="selector-label">
        <span className="label-text">🗣️ Voice Language:</span>
      </div>

      <div className="language-dropdown">
        <button
          className="language-button"
          onClick={() => setIsOpen(!isOpen)}
          title="Select voice language"
        >
          <span className="language-icon">{currentLang.icon}</span>
          <span className="language-native">{currentLang.nativeName}</span>
          <span className="language-name">({currentLang.name})</span>
          <span className="dropdown-arrow">▼</span>
        </button>

        {isOpen && (
          <div className="language-menu">
            {languages.map(lang => (
              <button
                key={lang.code}
                className={`language-option ${currentLanguage === lang.code ? 'active' : ''}`}
                onClick={() => handleLanguageSelect(lang.code)}
              >
                <span className="option-icon">{lang.icon}</span>
                <span className="option-native">{lang.nativeName}</span>
                <span className="option-name">{lang.name}</span>
                {currentLanguage === lang.code && <span className="checkmark">✓</span>}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
