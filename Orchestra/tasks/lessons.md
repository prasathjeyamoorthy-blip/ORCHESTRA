# Lessons

- After winget installs ffmpeg, old shell sessions may not see PATH updates; solver-side explicit ffmpeg and ffprobe path discovery avoids WinError 2.
- reCAPTCHA challenge iframes can refresh mid-step; reacquiring iframe and retrying audio source fetch prevents ContextLostError races.
- Speech transcription can fail intermittently with UnknownValueError; reloading challenge and retrying improves reliability.
- For newly attached automation scripts, run py_compile first to catch immediate syntax blockers before runtime debugging.
- Do not force-set WERKZEUG_RUN_MAIN when embedding Flask app.run in a thread; it can trigger WERKZEUG_SERVER_FD KeyError.
