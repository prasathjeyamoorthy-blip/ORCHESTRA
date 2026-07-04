"""Configuration constants for PAN card application automation."""
import os
from dotenv import load_dotenv
load_dotenv()

# Timing configuration
DEFAULT_DELAY_MS = 600

# Browser configuration
BROWSER_ARGS = [
    '--disable-blink-features=AutomationControlled',
    '--disable-dev-shm-usage',
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-web-security',
    '--disable-features=IsolateOrigins,site-per-process',
    '--allow-running-insecure-content',
    '--disable-features=VizDisplayCompositor'
]

BROWSER_VIEWPORT = {'width': 1366, 'height': 768}

BROWSER_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'

BROWSER_CONTEXT_CONFIG = {
    'locale': 'en-US',
    'timezone_id': 'Asia/Kolkata',
    'permissions': ['geolocation'],
    'geolocation': {
        'latitude': float(os.getenv("GEO_LAT", "20.5937")),
        'longitude': float(os.getenv("GEO_LON", "78.9629")),
    },
    'color_scheme': 'light',
    'extra_http_headers': {
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Upgrade-Insecure-Requests': '1'
    }
}

STEALTH_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
    
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5]
    });
    
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en']
    });
    
    window.chrome = {
        runtime: {}
    };
    
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
"""

# URLs
PAN_REGISTRATION_URL = "https://onlineservices.proteantech.in/paam/endUserRegisterContact.html"

# File paths
TEMP_AUDIO_FILES = ["captcha_audio.mp3", "captcha_audio.wav"]

# Document type mappings
PROOF_DOCUMENTS = {
    'aadhaar': "AADHAAR Card issued by the",
    'birth_certificate': "Birth Certificate"
}

VERIFIER_OPTIONS = {
    'self': "Self"
}

# Form defaults — these are portal UI defaults, not user data
DEFAULT_COUNTRY_CODE = "IND"
DEFAULT_STATE_CODE = ""   # Set dynamically from user's Aadhaar state
DEFAULT_ISD_CODE = "91"
DEFAULT_ISD_LABEL = "INDIA (91)"
