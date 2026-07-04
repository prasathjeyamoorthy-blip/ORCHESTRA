"""CAPTCHA solving functionality."""

import os
import re
import requests
import whisper
from pydub import AudioSegment
from pydub.utils import which
from playwright.sync_api import Page
from config import TEMP_AUDIO_FILES

AudioSegment.converter = which("ffmpeg") or r"C:\ffmpeg\bin\ffmpeg.exe"

# Whisper model is loaded lazily and cached at module level so it is
# only loaded into memory once, even across multiple CAPTCHA attempts.
_WHISPER_MODEL = None


def get_whisper_model(model_name: str = "small"):
    """Return a cached Whisper model, loading it only on first use."""
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        print(f"[*] Loading Whisper model '{model_name}' (first use only)...")
        _WHISPER_MODEL = whisper.load_model(model_name)
    return _WHISPER_MODEL


class CaptchaSolver:
    """Handles reCAPTCHA solving using audio challenge."""
    
    def __init__(self, page: Page):
        self.page = page
        self.mp3_path = TEMP_AUDIO_FILES[0]
        self.wav_path = TEMP_AUDIO_FILES[1]
    
    def solve(self) -> bool:
        """Attempt to solve reCAPTCHA. Returns True if successful."""
        try:
            self._click_checkbox()
            self._switch_to_audio()
            audio_url = self._get_audio_url()
            
            if not audio_url:
                raise Exception("Could not find audio download link")
            
            captcha_text = self._transcribe_audio(audio_url)
            self._submit_answer(captcha_text)
            
            return True
        
        except Exception as e:
            print(f"[+] Captcha skipped or passed: {e}")
            return False
        
        finally:
            self._cleanup_temp_files()
    
    def _click_checkbox(self) -> None:
        """Click the 'I'm not a robot' checkbox."""
        checkbox_frame = self.page.frame_locator("iframe[src*='recaptcha/enterprise/anchor']").first
        checkbox_frame.get_by_role("checkbox", name="I'm not a robot").wait_for(timeout=15000)
        self.page.wait_for_timeout(1500)
        checkbox_frame.get_by_role("checkbox", name="I'm not a robot").click()
        self.page.wait_for_timeout(3000)
    
    def _switch_to_audio(self) -> None:
        """Switch to audio challenge."""
        for frame in self.page.frames:
            if "bframe" in frame.url:
                try:
                    result = frame.evaluate("""
                        () => {
                            const btn = document.getElementById('recaptcha-audio-button');
                            if (btn) { btn.click(); return 'clicked'; }
                            return 'not found';
                        }
                    """)
                    print(f"[captcha] audio btn: {result}")
                    if "clicked" in result:
                        break
                except Exception:
                    continue
        self.page.wait_for_timeout(2000)
    
    def _get_audio_url(self) -> str:
        """Get the audio challenge download URL."""
        audio_src = None
        for frame in self.page.frames:
            if "bframe" in frame.url:
                try:
                    frame.wait_for_selector(".rc-audiochallenge-tdownload-link", timeout=10000)
                    audio_src = frame.get_attribute(".rc-audiochallenge-tdownload-link", "href", timeout=5000)
                    if audio_src:
                        break
                except Exception:
                    continue
        return audio_src
    
    def _transcribe_audio(self, audio_url: str) -> str:
        """Download and transcribe audio challenge."""
        # Download audio
        with open(self.mp3_path, "wb") as f:
            f.write(requests.get(audio_url).content)
        print(f"[+] Audio downloaded: {self.mp3_path}")
        
        # Convert to WAV
        AudioSegment.from_mp3(self.mp3_path).export(self.wav_path, format="wav")
        
        # Transcribe using cached Whisper model (loaded only once)
        model = get_whisper_model("small")
        result = model.transcribe(self.wav_path, language="en", fp16=False)
        captcha_text = re.sub(r"[^a-z0-9 ]", "", result["text"].strip().lower()).strip()
        print(f"[captcha] Recognized: {captcha_text}")
        
        return captcha_text
    
    def _submit_answer(self, captcha_text: str) -> None:
        """Submit the captcha answer."""
        for frame in self.page.frames:
            if "bframe" in frame.url:
                try:
                    frame.fill("#audio-response", captcha_text, timeout=5000)
                    frame.click("#recaptcha-verify-button", timeout=5000)
                    break
                except Exception:
                    continue
        self.page.wait_for_timeout(3000)
    
    def _cleanup_temp_files(self) -> None:
        """Remove temporary audio files."""
        for file_path in [self.mp3_path, self.wav_path]:
            if os.path.exists(file_path):
                os.remove(file_path)
