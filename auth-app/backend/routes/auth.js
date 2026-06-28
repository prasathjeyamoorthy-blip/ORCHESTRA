const router = require('express').Router();
const { createClient } = require('@supabase/supabase-js');
const { loginLimiter, signupLimiter } = require('../middleware/rateLimiter');

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_ANON_KEY
);

// ── PHONE OTP — SEND ─────────────────────────────────────────────────────────
// Triggers Supabase to send a 6-digit SMS OTP to the given phone number.
// Phone must be in E.164 format: +919876543210
router.post('/send-otp', loginLimiter, async (req, res) => {
  const { phone } = req.body;

  if (!phone || !/^\+[1-9]\d{6,14}$/.test(phone.trim())) {
    return res.status(400).json({ error: 'Phone number must be in E.164 format (e.g. +919876543210).' });
  }

  const { error } = await supabase.auth.signInWithOtp({ phone: phone.trim() });
  if (error) return res.status(400).json({ error: error.message });

  return res.json({ message: 'OTP sent.' });
});

// ── PHONE OTP — VERIFY ────────────────────────────────────────────────────────
// Verifies the 6-digit SMS OTP and sets httpOnly session cookies on success.
router.post('/verify-otp', loginLimiter, async (req, res) => {
  const { phone, token } = req.body;

  if (!phone || !token) {
    return res.status(400).json({ error: 'Phone and token are required.' });
  }
  if (!/^\d{6}$/.test(token.trim())) {
    return res.status(400).json({ error: 'Token must be a 6-digit number.' });
  }

  const { data, error } = await supabase.auth.verifyOtp({
    phone: phone.trim(),
    token: token.trim(),
    type: 'sms',
  });

  if (error || !data?.session) {
    return res.status(401).json({ error: error?.message ?? 'OTP verification failed.' });
  }

  // Set httpOnly session cookies so all /api/* routes work immediately
  const secure = process.env.NODE_ENV === 'production';
  res.cookie('access_token', data.session.access_token, {
    httpOnly: true, secure, sameSite: 'strict',
    maxAge: 60 * 60 * 1000,
  });
  res.cookie('refresh_token', data.session.refresh_token, {
    httpOnly: true, secure, sameSite: 'strict',
    maxAge: 7 * 24 * 60 * 60 * 1000,
  });

  return res.json({
    message: 'Phone verified.',
    session: {
      access_token: data.session.access_token,
      refresh_token: data.session.refresh_token,
    },
    user: {
      id: data.user.id,
      email: data.user.email,
      phone: data.user.phone,
      display_name: data.user.user_metadata?.display_name,
    },
  });
});

// ── SIGNUP ────────────────────────────────────────────────────────────────────
router.post('/signup', signupLimiter, async (req, res) => {
  const { email, password, display_name } = req.body;

  if (!email || !password)
    return res.status(400).json({ error: 'Email and password are required.' });
  if (password.length < 8)
    return res.status(400).json({ error: 'Password must be at least 8 characters.' });

  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: { display_name },
    },
  });

  if (error) {
    // error.code is the reliable check; message fallback for older SDK versions
    if (error.code === 'user_already_exists' || error.message.toLowerCase().includes('already registered')) {
      return res.status(409).json({ error: 'An account with this email already exists.' });
    }
    return res.status(400).json({ error: error.message });
  }

  // When email confirmation is OFF, Supabase silently returns a fake user
  // (identities array is empty) instead of an error for duplicate emails
  if (!data?.user?.identities?.length) {
    return res.status(409).json({ error: 'An account with this email already exists.' });
  }

  // Auto sign-in since email verification is disabled
  const { data: loginData, error: loginError } = await supabase.auth.signInWithPassword({ email, password });
  if (loginError) return res.status(400).json({ error: loginError.message });

  res.cookie('access_token', loginData.session.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    maxAge: 60 * 60 * 1000,
  });
  res.cookie('refresh_token', loginData.session.refresh_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    maxAge: 7 * 24 * 60 * 60 * 1000,
  });

  return res.json({
    message: 'Account created successfully.',
    session: {
      access_token: loginData.session.access_token,
      refresh_token: loginData.session.refresh_token,
    },
    user: {
      id: loginData.user.id,
      email: loginData.user.email,
      display_name: loginData.user.user_metadata?.display_name,
    },
  });
});

// ── LOGIN ─────────────────────────────────────────────────────────────────────
router.post('/login', loginLimiter, async (req, res) => {
  const { email, password } = req.body;

  if (!email || !password)
    return res.status(400).json({ error: 'Email and password are required.' });

  const { data, error } = await supabase.auth.signInWithPassword({ email, password });

  if (error) return res.status(401).json({ error: error.message });

  res.cookie('access_token', data.session.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    maxAge: 60 * 60 * 1000,
  });
  res.cookie('refresh_token', data.session.refresh_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    maxAge: 7 * 24 * 60 * 60 * 1000,
  });

  return res.json({
    message: 'Logged in.',
    session: {
      access_token: data.session.access_token,
      refresh_token: data.session.refresh_token,
    },
    user: {
      id: data.user.id,
      email: data.user.email,
      display_name: data.user.user_metadata?.display_name,
    },
  });
});

// ── REFRESH ───────────────────────────────────────────────────────────────────
router.post('/refresh', async (req, res) => {
  const token = req.cookies.refresh_token;
  if (!token) return res.status(401).json({ error: 'No refresh token.' });

  const { data, error } = await supabase.auth.refreshSession({ refresh_token: token });

  if (error) return res.status(401).json({ error: 'Session expired, please log in again.' });

  res.cookie('access_token', data.session.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    maxAge: 60 * 60 * 1000,
  });
  res.cookie('refresh_token', data.session.refresh_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    maxAge: 7 * 24 * 60 * 60 * 1000,
  });

  return res.json({ message: 'Token refreshed.' });
});

// ── SYNC SESSION (called after Supabase client-side login) ───────────────────
// Sets httpOnly cookies from the Supabase tokens so backend routes work
router.post('/sync-session', async (req, res) => {
  const { access_token, refresh_token } = req.body;
  if (!access_token || !refresh_token)
    return res.status(400).json({ error: 'Tokens required.' });

  // Verify the token is genuine before setting cookies
  const { data, error } = await supabase.auth.getUser(access_token);
  if (error || !data.user)
    return res.status(401).json({ error: 'Invalid token.' });

  const secure = process.env.NODE_ENV === 'production';
  res.cookie('access_token', access_token, {
    httpOnly: true, secure, sameSite: 'strict',
    maxAge: 60 * 60 * 1000,
  });
  res.cookie('refresh_token', refresh_token, {
    httpOnly: true, secure, sameSite: 'strict',
    maxAge: 7 * 24 * 60 * 60 * 1000,
  });

  return res.json({ ok: true });
});

// ── LOGOUT ────────────────────────────────────────────────────────────────────
router.post('/logout', async (req, res) => {
  const token = req.cookies.access_token;

  if (token) {
    const userSupabase = createClient(
      process.env.SUPABASE_URL,
      process.env.SUPABASE_ANON_KEY,
      { global: { headers: { Authorization: `Bearer ${token}` } } }
    );
    await userSupabase.auth.signOut();
  }

  res.clearCookie('access_token');
  res.clearCookie('refresh_token');
  return res.json({ message: 'Logged out.' });
});

// ── GET PROFILE ───────────────────────────────────────────────────────────────
router.get('/profile', async (req, res) => {
  const token = req.cookies.access_token;
  if (!token) return res.status(401).json({ error: 'Not authenticated.' });

  const { data, error } = await supabase.auth.getUser(token);
  if (error) return res.status(401).json({ error: 'Invalid session.' });

  const adminSupabase = createClient(
    process.env.SUPABASE_URL,
    process.env.SUPABASE_SERVICE_KEY
  );
  const { data: profile } = await adminSupabase
    .from('profiles')
    .select('*')
    .eq('id', data.user.id)
    .single();

  return res.json({ user: data.user, profile });
});

module.exports = router;
