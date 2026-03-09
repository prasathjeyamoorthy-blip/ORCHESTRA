import React, { useState, useEffect, useRef } from 'react';

export default function AutomationModal({ isOpen, eventData, onSubmit }) {
  const [inputValue, setInputValue] = useState("");
  const [cacheBuster, setCacheBuster] = useState("");
  const [multiInputValues, setMultiInputValues] = useState({});

  // Reset input when new event arrives
  useEffect(() => {
    setInputValue("");
    setMultiInputValues({});
    if (eventData) {
      setCacheBuster(Date.now().toString());
      if (eventData.type === 'REQUEST_MISSING_DETAILS' && eventData.missing_fields) {
        const initialMulti = {};
        eventData.missing_fields.forEach(f => initialMulti[f] = "");
        setMultiInputValues(initialMulti);
      }
    }
  }, [eventData]);

  if (!isOpen || !eventData) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (eventData.type === 'REQUEST_MISSING_DETAILS') {
      // Validate all fields are filled
      const allFilled = Object.values(multiInputValues).every(val => val.trim() !== "");
      if (!allFilled) return;
      onSubmit(multiInputValues);
    } else {
      if (!inputValue.trim()) return;
      onSubmit(inputValue);
    }
  };

  const handleMultiChange = (field, value) => {
    setMultiInputValues(prev => ({ ...prev, [field]: value }));
  };

  return (
    <div className="automation-modal-overlay" style={overlayStyle}>
      <div className="automation-modal-content" style={contentStyle}>
        <div className="modal-header" style={headerStyle}>
          <h2>Action Required</h2>
        </div>
        
        <div className="modal-body" style={bodyStyle}>
          <p>{eventData.message}</p>
          
          {eventData.type === 'REQUEST_CAPTCHA' && (
            <div style={imageContainerStyle}>
              {/* Add timestamp query param to bypass browser caching of the captcha image */}
               <img 
                 src={`http://localhost:8000/automation/captcha?t=${cacheBuster}`} 
                 alt="Captcha" 
                 style={captchaImageStyle}
               />
            </div>
          )}

          {eventData.type === 'REQUEST_MISSING_DETAILS' ? (
            <form onSubmit={handleSubmit} style={{...formStyle, flexDirection: 'column', alignItems: 'stretch'}}>
              {eventData.missing_fields?.map((field, idx) => (
                <div key={idx} style={{marginBottom: '10px', display: 'flex', flexDirection: 'column'}}>
                  <label style={{fontSize: '12px', marginBottom: '4px', color: '#BBB'}}>{field}</label>
                  <input 
                    type="text" 
                    value={multiInputValues[field] || ""}
                    onChange={(e) => handleMultiChange(field, e.target.value)}
                    placeholder={`Enter ${field}`}
                    style={inputStyle}
                    autoFocus={idx === 0}
                  />
                </div>
              ))}
              <button type="submit" style={{...btnStyle, marginTop: '10px'}}>Submit Details</button>
            </form>
          ) : (
            <form onSubmit={handleSubmit} style={formStyle}>
              <input 
                type="text" 
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder={
                  eventData.type === 'REQUEST_CAPTCHA' ? "Enter Captcha" :
                  eventData.type === 'REQUEST_OTP'     ? "Enter OTP" :
                  eventData.type === 'REQUEST_RESUME'  ? "Type anything to continue..." :
                  "Enter value"
                }
                style={inputStyle}
                autoFocus
              />
              <button type="submit" style={btnStyle}>
                {eventData.type === 'REQUEST_RESUME' ? "Continue" : "Submit"}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

// Inline Styles for quick integration
const overlayStyle = {
  position: 'fixed',
  top: 0, left: 0, right: 0, bottom: 0,
  backgroundColor: 'rgba(0,0,0,0.7)',
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  zIndex: 9999
};

const contentStyle = {
  backgroundColor: '#1E1E1E',
  borderRadius: '12px',
  width: '400px',
  boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
  overflow: 'hidden',
  color: '#FFFFFF',
  fontFamily: 'Inter, sans-serif'
};

const headerStyle = {
  backgroundColor: '#2D2D2D',
  padding: '16px 20px',
  borderBottom: '1px solid #333'
};

const bodyStyle = {
  padding: '24px 20px'
};

const imageContainerStyle = {
  backgroundColor: '#FFF',
  padding: '10px',
  borderRadius: '4px',
  margin: '16px 0',
  textAlign: 'center'
};

const captchaImageStyle = {
  maxWidth: '100%',
  height: 'auto'
};

const formStyle = {
  display: 'flex',
  marginTop: '20px',
  gap: '10px'
};

const inputStyle = {
  flex: 1,
  padding: '12px 16px',
  borderRadius: '6px',
  border: '1px solid #444',
  backgroundColor: '#2D2D2D',
  color: '#FFF',
  fontSize: '16px'
};

const btnStyle = {
  padding: '12px 24px',
  backgroundColor: '#4DABF7',
  color: '#000',
  border: 'none',
  borderRadius: '6px',
  fontWeight: 'bold',
  cursor: 'pointer',
  fontSize: '16px'
};
