# Deployment Checklist

## Pre-Deployment Requirements

### Backend Setup
- [ ] Python 3.8+ installed
- [ ] Virtual environment created: `python -m venv .venv`
- [ ] Dependencies installed: `pip install -r pan_verification/requirements.txt`
- [ ] Environment variables configured in `.env`:
  - `NVIDIA_META_90B` - NVIDIA API key for vision model
  - `SUPABASE_URL` - Supabase project URL
  - `SUPABASE_KEY` - Supabase service key
  - `FLASK_ENV` - Set to 'production'

### Frontend Setup
- [ ] Node.js 16+ installed
- [ ] Dependencies installed: `npm install` in frontend directory
- [ ] Environment variables configured in `frontend/.env`:
  - `VITE_SUPABASE_URL`
  - `VITE_SUPABASE_ANON_KEY`
  - `VITE_API_BASE_URL` - Backend API endpoint

### Database Setup
- [ ] Supabase project created
- [ ] Tables created: `users`, `persons`, `documents`
- [ ] Foreign key constraints configured
- [ ] Authentication enabled

## Build & Testing

### Backend Testing
```bash
cd pan_verification
pytest tests/  # Run unit tests
python app.py  # Run local server on http://localhost:5000
```

### Frontend Testing
```bash
cd frontend
npm run dev   # Development server on http://localhost:5173
npm run build # Production build to dist/
```

### API Testing
- [ ] `/api/verify` - Document upload and extraction
- [ ] `/api/confirm_save` - User-verified document save
- [ ] `/api/get_person_docs` - Document retrieval
- [ ] `/api/update_document` - Document update

## Deployment to Production

### Frontend Deployment (Vercel, Netlify, or similar)
1. Build production bundle: `npm run build`
2. Deploy `dist/` folder
3. Configure environment variables
4. Test all routes and API calls

### Backend Deployment (AWS EC2, DigitalOcean, or similar)
1. Install Python dependencies: `pip install -r requirements.txt`
2. Set environment variables
3. Run with production server (Gunicorn/uWSGI):
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```
4. Configure nginx as reverse proxy
5. Enable HTTPS/SSL certificate

### Database Migration
1. Backup existing Supabase data
2. Run schema migrations (if any)
3. Verify foreign key constraints
4. Test data integrity

## Post-Deployment Verification

- [ ] Frontend loads without errors
- [ ] API endpoints respond correctly
- [ ] Authentication works
- [ ] Document upload and extraction works
- [ ] Data displays correctly in UI
- [ ] Missing fields form works
- [ ] Consent review screen displays all data
- [ ] Final save works and data persists
- [ ] CORS headers configured correctly
- [ ] Error handling works gracefully

## Monitoring

- [ ] Set up error logging
- [ ] Monitor API response times
- [ ] Track failed document uploads
- [ ] Monitor database storage usage
- [ ] Set up alerts for critical errors

## Rollback Plan

If issues arise:
1. Revert to last known good deployment
2. Check error logs for issues
3. Fix and redeploy
4. Verify fixes with manual testing before production

## Security Checklist

- [ ] API keys not exposed in frontend
- [ ] Environment variables not committed to git
- [ ] HTTPS enabled in production
- [ ] CORS properly configured
- [ ] Input validation on all endpoints
- [ ] Rate limiting enabled
- [ ] Database backups configured
