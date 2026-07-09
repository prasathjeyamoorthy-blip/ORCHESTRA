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
    # NOTE: Do NOT add --disable-web-security or --disable-features=IsolateOrigins
    # Those flags break cross-origin iframes (reCAPTCHA loads from google.com in
    # a sandboxed iframe — killing isolation prevents it from loading entirely).
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
    // Hide webdriver flag — primary automation detection signal
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

    // Fake plugin list (real browsers always have plugins)
    Object.defineProperty(navigator, 'plugins', {
        get: () => {
            const arr = [
                { name: 'Chrome PDF Plugin' },
                { name: 'Chrome PDF Viewer' },
                { name: 'Native Client' },
            ];
            arr.__proto__ = PluginArray.prototype;
            return arr;
        }
    });

    // Fake languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en']
    });

    // Full chrome object (reCAPTCHA checks window.chrome.app)
    window.chrome = {
        app: {
            isInstalled: false,
            InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' },
            RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' },
        },
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
    };

    // Fix Notification permission probe (used by reCAPTCHA)
    const _origQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : _origQuery(parameters)
    );

    // Remove automation-related properties from navigator
    delete navigator.__proto__.webdriver;
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
