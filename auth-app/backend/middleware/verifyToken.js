const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_ANON_KEY
);

module.exports = async (req, res, next) => {
  // Accept token from httpOnly cookie (browser) OR Authorization header (API clients)
  let token = req.cookies.access_token;
  if (!token) {
    const authHeader = req.headers.authorization;
    if (authHeader && authHeader.startsWith('Bearer ')) {
      token = authHeader.slice(7).trim();
    }
  }

  if (!token) return res.status(401).json({ error: 'Not authenticated.' });

  // Try the access token first
  const { data, error } = await supabase.auth.getUser(token);
  if (!error) {
    req.user = data.user;
    return next();
  }

  // Access token expired — try refreshing with the refresh token (cookie only)
  const refreshToken = req.cookies.refresh_token;
  if (!refreshToken) return res.status(401).json({ error: 'Session expired.' });

  const { data: refreshData, error: refreshError } = await supabase.auth.refreshSession({
    refresh_token: refreshToken,
  });

  if (refreshError || !refreshData?.session) {
    return res.status(401).json({ error: 'Session expired.' });
  }

  // Set new cookies
  const secure = process.env.NODE_ENV === 'production';
  res.cookie('access_token', refreshData.session.access_token, {
    httpOnly: true, secure, sameSite: 'strict',
    maxAge: 60 * 60 * 1000,
  });
  res.cookie('refresh_token', refreshData.session.refresh_token, {
    httpOnly: true, secure, sameSite: 'strict',
    maxAge: 7 * 24 * 60 * 60 * 1000,
  });

  req.user = refreshData.user;
  next();
};
