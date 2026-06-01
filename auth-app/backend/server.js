require('dotenv').config();
const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const cookieParser = require('cookie-parser');
const authRoutes   = require('./routes/auth');
const uploadRoutes = require('./routes/uploads');
const chatRoutes   = require('./routes/chat');
const otpRoutes    = require('./routes/otp');

const app = express();

app.use(helmet());
app.use(cors({
  origin: process.env.CLIENT_URL,
  credentials: true,
}));
app.use(express.json());
app.use(cookieParser());

// ── Response timing middleware ────────────────────────────────────────────────
app.use((req, res, next) => {
  const start = process.hrtime.bigint()

  res.on('finish', () => {
    const ms = Number(process.hrtime.bigint() - start) / 1_000_000
    const color =
      res.statusCode >= 500 ? '\x1b[31m' :   // red
      res.statusCode >= 400 ? '\x1b[33m' :   // yellow
      res.statusCode >= 300 ? '\x1b[36m' :   // cyan
                              '\x1b[32m'      // green
    const reset = '\x1b[0m'
    console.log(
      `${color}${req.method}${reset} ${req.originalUrl} ` +
      `${color}${res.statusCode}${reset} — ${ms.toFixed(2)}ms`
    )
  })

  next()
})

app.use('/api/auth', authRoutes);
app.use('/api/files', uploadRoutes);
app.use('/api/chat', chatRoutes);
app.use('/api/otp',  otpRoutes);

app.listen(process.env.PORT, () =>
  console.log(`Server running on port ${process.env.PORT}`)
);