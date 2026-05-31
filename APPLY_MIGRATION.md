# How to Apply the User Profiles Migration

## Quick Start

### Option 1: Using Supabase CLI (Recommended)
```bash
# Navigate to project root
cd /path/to/PAN_APP

# Apply all pending migrations
supabase db push

# Verify migration applied
supabase db diff
```

### Option 2: Manual SQL Execution
If you don't have Supabase CLI installed:

1. **Open Supabase Dashboard**
   - Go to https://app.supabase.com
   - Select your project
   - Navigate to SQL Editor

2. **Copy Migration SQL**
   - Open `supabase/migrations/20240104000000_add_user_profiles.sql`
   - Copy the entire contents

3. **Execute SQL**
   - Paste into SQL Editor
   - Click "Run" button
   - Verify success message

4. **Verify Table Created**
   ```sql
   SELECT * FROM user_profiles LIMIT 1;
   ```
   Should return empty result (no error)

---

## Verification Steps

### 1. Check Table Exists
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name = 'user_profiles';
```
**Expected:** Returns 1 row with `user_profiles`

### 2. Check Columns
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'user_profiles'
ORDER BY ordinal_position;
```
**Expected:** Shows all columns (id, user_id, full_name, etc.)

### 3. Check RLS Enabled
```sql
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE tablename = 'user_profiles';
```
**Expected:** `rowsecurity = true`

### 4. Check Policies
```sql
SELECT policyname, cmd 
FROM pg_policies 
WHERE tablename = 'user_profiles';
```
**Expected:** 4 policies (SELECT, INSERT, UPDATE, DELETE)

### 5. Check Trigger
```sql
SELECT trigger_name 
FROM information_schema.triggers 
WHERE event_object_table = 'user_profiles';
```
**Expected:** `update_user_profiles_updated_at`

---

## Restart Services

After applying migration:

### 1. Restart RAG Server
```bash
cd pan-rag
./restart.sh
# OR manually:
# pkill -f "uvicorn main:app"
# uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Restart Backend Server
```bash
cd auth-app/backend
# Stop current process (Ctrl+C)
npm start
# OR
node server.js
```

### 3. Verify Services Running
```bash
# Check RAG server
curl http://localhost:8000/api/health

# Check backend
curl http://localhost:3000/api/health
```

---

## Test the Integration

### Quick Test
1. Log in to your app
2. Open browser console (F12)
3. Start a chat: "I want to apply for PAN"
4. Complete the flow with test data:
   - Name: Test User
   - Mother's name: Test Mother
   - Email: test@example.com
   - Income: 500000
5. Confirm details
6. Check database:
   ```sql
   SELECT * FROM user_profiles 
   WHERE email = 'test@example.com';
   ```
7. Start new session
8. Say "I want to apply for PAN" again
9. **Expected:** Details should be prefilled

---

## Troubleshooting

### Migration fails with "relation already exists"
**Solution:** Table already created, skip migration or drop first:
```sql
DROP TABLE IF EXISTS user_profiles CASCADE;
-- Then run migration again
```

### Permission denied errors
**Solution:** Check you're using service role key:
```sql
-- Test with service role
SELECT current_user;
-- Should show 'service_role' or 'postgres'
```

### RLS blocking inserts
**Solution:** Verify policies created:
```sql
-- Should return 4 rows
SELECT * FROM pg_policies WHERE tablename = 'user_profiles';
```

### Trigger not firing
**Solution:** Recreate trigger:
```sql
DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON user_profiles;
-- Then run trigger creation from migration
```

---

## Rollback (If Needed)

To undo the migration:

```sql
-- Drop table and all dependencies
DROP TABLE IF EXISTS user_profiles CASCADE;

-- Drop function
DROP FUNCTION IF EXISTS update_user_profile_updated_at() CASCADE;
```

Then restart services.

---

## Environment Variables

Ensure these are set in `pan-rag/.env`:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
```

**Note:** Use the **service role key**, not the anon key!

---

## Success Indicators

✅ Migration successful if:
- No SQL errors during execution
- Table appears in Supabase dashboard
- RLS policies visible in dashboard
- Test user profile saves correctly
- Prefill works in new session

---

## Next Steps After Migration

1. ✅ Apply migration
2. ✅ Restart services
3. ✅ Run test scenario
4. ✅ Verify profile saved
5. ✅ Test prefill in new session
6. ✅ Monitor logs for errors
7. ✅ Check performance metrics

---

**Ready to apply?** Follow Option 1 or Option 2 above!
