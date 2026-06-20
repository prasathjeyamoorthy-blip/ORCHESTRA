# PAN Auth Integration Plan

## Steps (Completed: ✅ | Pending: ⏳)

✅ **Step 1:** Create TODO_AUTH.md

✅ **Step 2:** Update supa.py - add auth_id param to save_document

✅ **Step 3:** app.py 
   - Import supabase.auth
   - Add POST /api/signup(email, password) → auth.sign_up → return auth_id=user.id
   - Update /api/verify: require 'auth_id' form field → pass to save_document

✅ **Step 4:** templates/index.html
   - Add email/password inputs + Signup button
   - On signup success → store auth_id → enable upload form → append auth_id to FormData

⏳ **Step 5:** Test full flow
   - python app.py
   - localhost:5000 → signup → upload → check DB "documents" has auth_id + data

⏳ **Step 5:** Test full flow
   - python app.py
   - localhost:5000 → signup → upload → check DB "documents" has auth_id + data

⏳ **Step 6:** Complete

## Notes
- Use supabase.auth.sign_up (email/password)
- Frontend: 2-step UI (signup first, then verify)
- DB assumes "auth_id" column exists (Supabase handles)
- Error handling for auth failures
