# PAN Card Application Automation

Automates PAN card form filling on the Protean Tech portal.

---

## Setup (One Time)

### 1. Create virtual environment

```bash
uv venv
```
Creates an isolated Python environment in `.venv/` folder.

### 2. Activate virtual environment

```bash
.venv\Scripts\activate
```
Activates the environment so packages install locally, not globally.

### 3. Install dependencies

```bash
uv pip install -r requirements.txt
```
Installs all required Python packages (playwright, whisper, etc).

### 4. Install browser

```bash
playwright install chromium
```
Downloads the Chromium browser that the script controls.

### 5. Install FFmpeg

Download from https://ffmpeg.org/download.html and place in `C:\ffmpeg\bin\` or add to PATH.

Needed to convert CAPTCHA audio from MP3 to WAV for transcription.

---

## Configure

### 1. Edit `data.json`

Fill in your personal details (name, aadhaar, address, etc).

### 2. Place documents in `docs/` folder

| File | What |
|------|------|
| `docs/jphoto.jpeg` | Passport photo |
| `docs/jsign.jpeg` | Signature scan |
| `docs/jaadhar (1).pdf` | Aadhaar PDF |
| `docs/jbirthcert.pdf` | Birth certificate PDF |

Update filenames in `data.json` if yours are different.

---

## Run

```bash
python main.py
```

Runs the full automation headlessly. When done, check:

- **Console** — prints the payment link
- **`payment_link.json`** — contains the payment URL
- **`payment_page_*.png`** — screenshot of payment page

Open the payment link in your browser to pay.

---

## File Structure

```
main.py             → Entry point, run this
config.py           → Settings (delays, URLs, browser config)
data_handler.py     → Loads data.json, saves payment_link.json
browser_manager.py  → Creates and configures the browser
captcha_solver.py   → Solves reCAPTCHA via audio transcription
form_filler.py      → Fills all form fields
workflow.py         → Orchestrates the full flow
data.json           → Your input data
docs/               → Your documents
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError` | Run `uv pip install -r requirements.txt` |
| Browser not found | Run `playwright install chromium` |
| FFmpeg not found | Install FFmpeg and add to PATH |
| CAPTCHA fails | Internet may be slow, try again |
