-- Migration: add_voice_support
-- Adds voice interaction support to the PAN application system
-- Includes voice message types, preferences, and usage logging

-- ── Add voice columns to conversations table ──────────────────────────────────
ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS message_type TEXT DEFAULT 'text_input' 
    CHECK (message_type IN ('text_input', 'text_output', 'voice_input', 'voice_output'));

ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS audio_url TEXT;

ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS language VARCHAR(5);

ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS duration_seconds INTEGER;

-- ── Voice preferences table ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS voice_preferences (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    preferred_language VARCHAR(5) DEFAULT 'en' CHECK (preferred_language IN ('en', 'ta', 'hi')),
    voice_enabled BOOLEAN DEFAULT true,
    auto_play_responses BOOLEAN DEFAULT true,
    show_transcripts BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── Voice usage logging ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS voice_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    event_type VARCHAR(20) NOT NULL CHECK (event_type IN ('stt_request', 'tts_request', 'error', 'language_switch')),
    language VARCHAR(5),
    processing_time_ms INTEGER,
    success BOOLEAN,
    error_type VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── Create indexes for performance ─────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_conversations_voice_type ON conversations(message_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_language ON conversations(language);
CREATE INDEX IF NOT EXISTS idx_conversations_audio_url ON conversations(audio_url) WHERE audio_url IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_voice_preferences_language ON voice_preferences(preferred_language);
CREATE INDEX IF NOT EXISTS idx_voice_usage_user ON voice_usage_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_voice_usage_event ON voice_usage_logs(event_type, created_at DESC);

-- ── Enable row-level security ──────────────────────────────────────────────────
ALTER TABLE voice_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE voice_usage_logs ENABLE ROW LEVEL SECURITY;

-- ── Voice preferences RLS policies ─────────────────────────────────────────────
DROP POLICY IF EXISTS "Users access own voice preferences" ON voice_preferences;
CREATE POLICY "Users access own voice preferences" 
    ON voice_preferences FOR ALL 
    USING (auth.uid() = user_id) 
    WITH CHECK (auth.uid() = user_id);

-- ── Voice usage logs RLS policies ──────────────────────────────────────────────
DROP POLICY IF EXISTS "Users access own voice logs" ON voice_usage_logs;
CREATE POLICY "Users access own voice logs" 
    ON voice_usage_logs FOR SELECT
    USING (auth.uid() = user_id);

-- ── Update conversations table RLS for voice messages ──────────────────────────
-- Existing conversations RLS policy already covers voice messages
-- since they use the same user_id and session_id checks
