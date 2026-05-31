# Supabase Package Installation Fix ✅

## Error
```
ModuleNotFoundError: No module named 'supabase'
```

**Location:** `pan-rag/agent/user_profile.py` line 9

**Cause:** The `supabase` Python package was not installed in the pan-rag virtual environment.

---

## Solution

### 1. Installed Supabase Package
```bash
cd pan-rag
uv pip install supabase
```

**Result:** Successfully installed supabase v2.29.0 and dependencies:
- supabase==2.29.0
- supabase-auth==2.29.0
- supabase-functions==2.29.0
- storage3==2.29.0
- postgrest==2.29.0
- realtime==2.29.0
- And 13 other dependencies

### 2. Added to requirements.txt
Added `supabase` to `pan-rag/requirements.txt` under the Memory section so it's tracked for future installations.

---

## Verification

### Import Test
```bash
cd pan-rag
.venv/bin/python -c "from agent.user_profile import prefill_flow_from_profile, save_flow_to_profile; print('✅ Import successful')"
```
**Result:** ✅ Import successful

### Routes Test
```bash
cd pan-rag
.venv/bin/python -c "from api.routes import router; print('✅ Routes import successful')"
```
**Result:** ✅ Routes import successful

---

## Why This Happened

The pan-rag project uses `uv` for package management (indicated by `uv.lock` file). When we created the new `user_profile.py` module that imports `supabase`, the package wasn't in the environment yet because:

1. The module was newly created
2. The dependency wasn't in requirements.txt
3. The package wasn't installed in the virtual environment

---

## Next Steps

### 1. Restart RAG Server
```bash
cd pan-rag
./restart.sh
```

Or manually:
```bash
cd pan-rag
pkill -f "uvicorn main:app"
.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Verify Server Starts
```bash
curl http://localhost:8000/api/health
```
**Expected:** `{"status":"ok"}`

### 3. Test Profile Integration
1. Log in to your app
2. Complete a PAN application
3. Check if profile is saved to database
4. Start new session and verify prefill works

---

## For Future Installations

If setting up on a new machine:

```bash
cd pan-rag

# Install all dependencies (including supabase)
uv pip install -r requirements.txt

# Or if using pip
pip install -r requirements.txt
```

---

## Package Details

**Supabase Python Client v2.29.0**
- Official Python client for Supabase
- Provides: Database, Auth, Storage, Realtime, Functions
- Used for: User profile persistence in `user_profiles` table

**Dependencies Installed:**
- `supabase` - Main client
- `supabase-auth` - Authentication
- `supabase-functions` - Edge functions
- `storage3` - File storage
- `postgrest` - PostgreSQL REST API
- `realtime` - Real-time subscriptions
- `pyjwt` - JWT token handling
- `cryptography` - Encryption utilities

---

## Troubleshooting

### If import still fails after installation
```bash
# Verify supabase is installed
cd pan-rag
.venv/bin/python -c "import supabase; print(supabase.__version__)"
```

### If uv command not found
```bash
# Install uv first
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or use pip instead
pip install -r requirements.txt
```

### If virtual environment issues
```bash
# Recreate virtual environment
cd pan-rag
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Files Modified

```
✅ pan-rag/requirements.txt - Added supabase dependency
✅ pan-rag/.venv/ - Installed supabase package
```

---

**Status:** ✅ Fixed - Server Ready to Start
**Date:** 2026-04-30
**Package:** supabase==2.29.0
