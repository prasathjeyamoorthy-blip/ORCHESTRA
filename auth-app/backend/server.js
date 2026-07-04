require('dotenv').config();
const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const cookieParser = require('cookie-parser');
const multer = require('multer');
const FormData = require('form-data');
const verifyToken = require('./middleware/verifyToken');
const authRoutes   = require('./routes/auth');
const uploadRoutes = require('./routes/uploads');
const chatRoutes   = require('./routes/chat');
const otpRoutes    = require('./routes/otp');

const app = express();

// Configure multer for file uploads
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 50 * 1024 * 1024 }, // 50MB limit
});

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

// ── Document verification endpoints ───────────────────────────────────────────
app.post('/api/documents/verify', verifyToken, upload.single('file'), async (req, res) => {
  try {
    // Create FormData for forwarding to pan_verification service
    const formData = new FormData()
    
    // Copy form fields
    if (req.body.session_id) formData.append('session_id', req.body.session_id)
    if (req.body.doc_type) formData.append('doc_type', req.body.doc_type)
    
    // Add authenticated user ID
    formData.append('auth_id', req.user.id)
    
    // Add file if present
    if (req.file) {
      formData.append('file', req.file.buffer, {
        filename: req.file.originalname,
        contentType: req.file.mimetype
      })
    }

    const response = await fetch(`${process.env.PAN_VERIFICATION_URL || 'http://localhost:5000'}/api/verify`, {
      method: 'POST',
      body: formData,
    })

    const result = await response.json()
    
    if (response.ok) {
      console.log(`[documents/verify] Processed for user ${req.user.id}, status: ${result.status}`)
      res.json(result)
    } else {
      console.error(`[documents/verify] Processing failed: ${result.message}`)
      res.status(response.status).json(result)
    }
  } catch (error) {
    console.error('[documents/verify] Error:', error.message)
    res.status(502).json({ 
      status: 'error',
      message: 'Document verification service unavailable. Please try again.' 
    })
  }
})

app.post('/api/documents/confirm', verifyToken, async (req, res) => {
  try {
    const { session_id, auth_id, extracted_fields, user_fields } = req.body
    
    // Forward to pan_verification service for final confirmation and save
    const response = await fetch(`${process.env.PAN_VERIFICATION_URL || 'http://localhost:5000'}/api/confirm_save`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id,
        auth_id: auth_id || req.user.id,
        extracted_fields: extracted_fields || {},
        user_fields: user_fields || {},
      }),
    })

    const result = await response.json()
    
    if (response.ok) {
      console.log(`[documents/confirm] Confirmed for user ${req.user.id}, session ${session_id}`)
      res.json(result)
    } else {
      console.error(`[documents/confirm] Confirmation failed: ${result.message}`)
      res.status(response.status).json(result)
    }
  } catch (error) {
    console.error('[documents/confirm] Error:', error.message)
    res.status(502).json({ 
      status: 'error',
      message: 'Document confirmation service unavailable. Please try again.' 
    })
  }
})

// ── Document completion endpoint ──────────────────────────────────────────────
app.post('/api/complete_document', verifyToken, async (req, res) => {
  try {
    const { session_id, auth_id, extracted_fields, user_fields } = req.body;
    
    if (!session_id) {
      return res.status(400).json({ error: 'session_id is required' });
    }
    
    // Forward to pan-rag service
    const response = await fetch(`${process.env.RAG_URL}/api/complete_document`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id,
        auth_id: auth_id || req.user.id, // Use authenticated user ID if auth_id not provided
        extracted_fields: extracted_fields || {},
        user_fields: user_fields || {},
      }),
    });
    
    const result = await response.json();
    
    if (response.ok) {
      // Log successful document completion
      console.log(`[document] Completed for user ${req.user.id}, session ${session_id}`);
      res.json(result);
    } else {
      console.error(`[document] Completion failed: ${result.message}`);
      res.status(response.status).json(result);
    }
  } catch (error) {
    console.error('[document] Completion error:', error.message);
    res.status(502).json({ 
      status: 'error',
      message: 'Document completion service unavailable. Please try again.' 
    });
  }
});

// ── Direct upload to pan-rag (with user_id injection) ────────────────────────
app.post('/api/upload', verifyToken, upload.single('file'), async (req, res) => {
  try {
    const formData = new FormData()
    if (req.body.session_id) formData.append('session_id', req.body.session_id)
    if (req.body.doc_type)   formData.append('doc_type',   req.body.doc_type)
    if (req.body.message)    formData.append('message',    req.body.message)
    // Always inject the authenticated user ID
    formData.append('user_id', req.user.id)
    if (req.file) {
      formData.append('file', req.file.buffer, {
        filename: req.file.originalname,
        contentType: req.file.mimetype,
      })
    }
    const ragRes = await fetch(`${process.env.RAG_URL || 'http://localhost:8000'}/api/upload`, {
      method: 'POST',
      body: formData,
    })
    const result = await ragRes.json()
    res.status(ragRes.status).json(result)
  } catch (error) {
    console.error('[upload] Error:', error.message)
    res.status(502).json({ status: 'error', message: 'Upload service unavailable.' })
  }
})

// ── FINALIZE APPLICATION - Integration Orchestrator ───────────────────────────
app.post('/api/finalize-application', verifyToken, async (req, res) => {
  try {
    const { session_id, trigger_automation } = req.body;
    
    if (!session_id) {
      return res.status(400).json({ 
        status: 'error',
        error: 'session_id is required' 
      });
    }
    
    console.log(`[finalize] Starting finalization for user ${req.user.id}, session ${session_id}`);
    
    // Forward to pan-rag service
    const response = await fetch(`${process.env.RAG_URL}/api/finalize-application`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id,
        user_id: req.user.id,
        trigger_automation: trigger_automation || false,
      }),
    });
    
    const result = await response.json();
    
    if (response.ok) {
      console.log(`[finalize] Success for user ${req.user.id}, automation: ${result.automation_triggered}`);
      res.json(result);
    } else {
      console.error(`[finalize] Failed: ${result.detail || result.message}`);
      res.status(response.status).json({
        status: 'error',
        message: result.detail || result.message || 'Finalization failed',
      });
    }
  } catch (error) {
    console.error('[finalize] Error:', error.message);
    res.status(502).json({ 
      status: 'error',
      message: 'Application finalization service unavailable. Please try again.',
      error: error.message
    });
  }
});

app.listen(process.env.PORT, () =>
  console.log(`Server running on port ${process.env.PORT}`)
);


// ── Voice API endpoints ────────────────────────────────────────────────────────
// POST /api/voice/speak - Main voice interaction endpoint
app.post('/api/voice/speak', verifyToken, upload.single('audio'), async (req, res) => {
  try {
    const userId = req.user.id;
    const language = req.body.language || 'en';
    const sessionId = req.body.session_id;

    // Validate audio file
    if (!req.file) {
      return res.status(400).json({
        status: 'error',
        error: 'No audio file provided',
        audio_available: false
      });
    }

    // Validate language
    if (!['en', 'ta', 'hi'].includes(language)) {
      return res.status(400).json({
        status: 'error',
        error: 'Unsupported language. Supported: en, ta, hi',
        audio_available: false
      });
    }

    console.log(`[voice/speak] User ${userId} submitted voice request (${language})`);

    // Create FormData for voice agent
    const formData = new FormData();
    formData.append('audio', req.file.buffer, {
      filename: 'audio.webm',
      contentType: req.file.mimetype
    });
    formData.append('language', language);
    formData.append('session_id', sessionId || require('uuid').v4());

    // Forward to voice agent service
    const voiceAgentUrl = process.env.VOICE_AGENT_URL || 'http://localhost:8002';
    const voiceResponse = await fetch(`${voiceAgentUrl}/api/voice/speak`, {
      method: 'POST',
      body: formData,
      timeout: 30000
    });

    if (!voiceResponse.ok) {
      console.error(`[voice/speak] Voice agent error: ${voiceResponse.status}`);
      
      // Try to get error details from voice agent
      let errorData = {};
      try {
        errorData = await voiceResponse.json();
      } catch (e) {
        // Voice agent returned non-JSON error
      }

      return res.status(503).json({
        status: 'error',
        error: 'Voice processing failed',
        audio_available: false,
        details: errorData.error
      });
    }

    // Get transcript and reply from response headers
    const transcript = decodeURIComponent(voiceResponse.headers.get('X-Transcript') || '');
    const reply = decodeURIComponent(voiceResponse.headers.get('X-Reply') || '');
    const responseLanguage = voiceResponse.headers.get('X-Language') || language;

    console.log(`[voice/speak] Processed successfully. Transcript: "${transcript.substring(0, 50)}..."`);

    // Store in Supabase conversation history
    try {
      const { createClient } = require('@supabase/supabase-js');
      const supabase = createClient(
        process.env.SUPABASE_URL,
        process.env.SUPABASE_SERVICE_ROLE_KEY
      );

      // Insert user voice input
      await supabase.from('conversations').insert({
        user_id: userId,
        session_id: sessionId,
        role: 'user',
        content: transcript,
        message_type: 'voice_input',
        language: language,
        created_at: new Date().toISOString()
      });

      // Insert assistant voice response
      await supabase.from('conversations').insert({
        user_id: userId,
        session_id: sessionId,
        role: 'assistant',
        content: reply,
        message_type: 'voice_output',
        language: responseLanguage,
        created_at: new Date().toISOString()
      });

      // Log voice usage
      await supabase.from('voice_usage_logs').insert({
        user_id: userId,
        session_id: sessionId,
        event_type: 'stt_request',
        language: language,
        success: true,
        created_at: new Date().toISOString()
      });

    } catch (dbError) {
      console.error('[voice/speak] Database error:', dbError.message);
      // Continue anyway - we still have the audio to send
    }

    // Forward audio response to client
    res.setHeader('Content-Type', 'audio/wav');
    res.setHeader('X-Transcript', encodeURIComponent(transcript));
    res.setHeader('X-Reply', encodeURIComponent(reply));
    res.setHeader('X-Language', responseLanguage);
    
    // Pipe audio response
    voiceResponse.body.pipe(res);

  } catch (error) {
    console.error('[voice/speak] Error:', error.message);
    
    res.status(500).json({
      status: 'error',
      error: 'Voice processing error',
      message: error.message,
      audio_available: false
    });
  }
});

// GET /api/voice/health - Check voice service status
app.get('/api/voice/health', async (req, res) => {
  try {
    const voiceAgentUrl = process.env.VOICE_AGENT_URL || 'http://localhost:8002';
    
    const healthResponse = await fetch(`${voiceAgentUrl}/api/health`, {
      timeout: 5000
    });

    if (healthResponse.ok) {
      const healthData = await healthResponse.json();
      
      return res.json({
        status: 'success',
        voice_agent_status: 'online',
        stt_available: healthData.stt_available,
        tts_available: healthData.tts_available,
        supported_languages: healthData.supported_languages || ['en', 'ta', 'hi'],
        latency_ms: healthData.latency_ms
      });
    } else {
      return res.status(503).json({
        status: 'degraded',
        voice_agent_status: 'offline',
        message: 'Voice agent not responding'
      });
    }

  } catch (error) {
    console.error('[voice/health] Error:', error.message);
    
    res.status(503).json({
      status: 'error',
      voice_agent_status: 'offline',
      error: 'Cannot reach voice agent service',
      message: error.message
    });
  }
});

// GET /api/voice/preferences - Get user voice preferences
app.get('/api/voice/preferences', verifyToken, async (req, res) => {
  try {
    const { createClient } = require('@supabase/supabase-js');
    const supabase = createClient(
      process.env.SUPABASE_URL,
      process.env.SUPABASE_SERVICE_ROLE_KEY
    );

    const { data, error } = await supabase
      .from('voice_preferences')
      .select('*')
      .eq('user_id', req.user.id)
      .single();

    if (error && error.code !== 'PGRST116') {
      throw error;
    }

    // Return defaults if no preferences exist
    const preferences = data || {
      user_id: req.user.id,
      preferred_language: 'en',
      voice_enabled: true,
      auto_play_responses: true,
      show_transcripts: true
    };

    res.json(preferences);

  } catch (error) {
    console.error('[voice/preferences] Error:', error.message);
    res.status(500).json({ error: 'Failed to fetch preferences' });
  }
});

// POST /api/voice/preferences - Save user voice preferences
app.post('/api/voice/preferences', verifyToken, async (req, res) => {
  try {
    const { preferred_language, voice_enabled, auto_play_responses, show_transcripts } = req.body;

    const { createClient } = require('@supabase/supabase-js');
    const supabase = createClient(
      process.env.SUPABASE_URL,
      process.env.SUPABASE_SERVICE_ROLE_KEY
    );

    const { data, error } = await supabase
      .from('voice_preferences')
      .upsert({
        user_id: req.user.id,
        preferred_language,
        voice_enabled,
        auto_play_responses,
        show_transcripts,
        updated_at: new Date().toISOString()
      })
      .select();

    if (error) throw error;

    res.json({
      status: 'success',
      preferences: data[0]
    });

  } catch (error) {
    console.error('[voice/preferences] Error:', error.message);
    res.status(500).json({ error: 'Failed to save preferences' });
  }
});

// GET /api/voice/history - Get voice conversation history
app.get('/api/voice/history', verifyToken, async (req, res) => {
  try {
    const sessionId = req.query.session_id;
    const limit = parseInt(req.query.limit) || 50;

    const { createClient } = require('@supabase/supabase-js');
    const supabase = createClient(
      process.env.SUPABASE_URL,
      process.env.SUPABASE_SERVICE_ROLE_KEY
    );

    let query = supabase
      .from('conversations')
      .select('*')
      .eq('user_id', req.user.id)
      .in('message_type', ['voice_input', 'voice_output'])
      .order('created_at', { ascending: false })
      .limit(limit);

    if (sessionId) {
      query = query.eq('session_id', sessionId);
    }

    const { data, error } = await query;

    if (error) throw error;

    res.json({
      status: 'success',
      messages: data
    });

  } catch (error) {
    console.error('[voice/history] Error:', error.message);
    res.status(500).json({ error: 'Failed to fetch voice history' });
  }
});
