# Login & Retrieve Docs Plan

## Steps

✅ **Step 1:** Create TODO_LOGIN.md

✅ **Step 2:** supa.py - add get_documents_by_auth(auth_id)

⏳ **Step 3:** app.py - /api/login (sign_in_with_password), /api/get_docs(auth_id)


⏳ **Step 3:** app.py - /api/login (sign_in_with_password), /api/get_docs(auth_id)

⏳ **Step 4:** templates/index.html - Login form, fetch docs, conditional upload/show

⏳ **Step 5:** Test: login with existing → see docs; new signup → upload → login → see

## Notes
- Login: supabase.auth.sign_in_with_password → auth_id
- get_docs: select * where auth_id
- UI: Auth tab (Login/Signup) → get auth_id → fetch docs → if has docs show JSON, else upload form
