const rateLimit = require('express-rate-limit');

exports.loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 min window
  max: 5,
  message: { error: 'Too many login attempts, try again in 15 minutes.' },
  standardHeaders: true,
  legacyHeaders: false,
});

exports.signupLimiter = rateLimit({
  windowMs: 60 * 60 * 1000, // 1 hour window
  max: 10,
  message: { error: 'Too many accounts created, try again later.' },
});