const router = require('express').Router();
const { createClient } = require('@supabase/supabase-js');
const verifyToken = require('../middleware/verifyToken');

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY
);

// ── Redis (Upstash) — REQUIRED ───────────────────────────────────────────────
const UPSTASH_URL   = process.env.UPSTASH_REDIS_REST_URL;
const UPSTASH_TOKEN = process.env.UPSTASH_REDIS_REST_TOKEN;

if (!UPSTASH_URL || !UPSTASH_URL.startsWith('https://')) {
  console.error('❌ UPSTASH_REDIS_REST_URL is not set or invalid');
  console.error('   Add it to auth-app/backend/.env:');
  console.error('   UPSTASH_REDIS_REST_URL=https://your-redis-url.upstash.io');
  process.exit(1);
}

if (!UPSTASH_TOKEN || UPSTASH_TOKEN === 'your-token-here') {
  console.error('❌ UPSTASH_REDIS_REST_TOKEN is not set or invalid');
  console.error('   Add it to auth-app/backend/.env:');
  console.error('   UPSTASH_REDIS_REST_TOKEN=your_token_here');
  process.exit(1);
}

const { Redis } = require('@upstash/redis');
const redis = new Redis({ url: UPSTASH_URL, token: UPSTASH_TOKEN });
console.log('✅ Redis (Upstash) connected');

// ── Cache helpers (Upstash Redis only — no local fallback) ────────────────────
const cacheGet    = async (k)         => redis.get(k);
const cacheSet    = async (k, v, ttl) => redis.set(k, v, { ex: ttl });
const cacheDel    = async (k)         => redis.del(k);
const cacheTouch  = async (k, ttl)    => redis.expire(k, ttl);

// ── Constants ─────────────────────────────────────────────────────────────────
const MAX_HISTORY   = 40;           // turns kept in Redis / sent to RAG (increased for longer sessions)
const WINDOW_TURNS  = 6;            // recent turns injected into RAG prompt
const CACHE_TTL     = 60 * 60 * 6;  // 6h session cache (refreshed on activity)
const PROFILE_TTL   = 60 * 60 * 24 * 7; // 7-day profile cache
const MEMORY_TTL    = 60 * 60 * 24 * 30; // 30-day long-term memory cache
const RAG_URL       = process.env.RAG_URL   || 'http://localhost:8000';
const VOICE_URL     = process.env.VOICE_URL || 'http://localhost:8002';

// Max past turns to surface from long-term memory search
const MEMORY_SEARCH_LIMIT = 6;

// ── Keys ──────────────────────────────────────────────────────────────────────
const histKey    = (uid, sid) => `chat:${uid}:${sid}`;
const profileKey = (uid)      => `profile:${uid}`;
const memoryKey  = (uid)      => `ltm:${uid}`;        // long-term memory summary cache

// ── New Memory Keys (PAN Assistant AI Agent) ──────────────────────────────────
const memoryHistoryKey     = (uid) => `chat:history:${uid}`;      // last 20 messages
const memorySummaryKey     = (uid) => `chat:summary:${uid}`;      // rolling summary
const memoryPreferencesKey = (uid) => `chat:preferences:${uid}`;  // user facts JSON

// ─────────────────────────────────────────────────────────────────────────────
// HISTORY  — Redis (hot) → Supabase (cold)
// Stored as [{role:'user'|'assistant', content, ts}]
// ─────────────────────────────────────────────────────────────────────────────
async function loadHistory(userId, sessionId) {
  const key = histKey(userId, sessionId);

  // 1. Hot path — Redis
  let history = await cacheGet(key);
  if (history) {
    // Refresh TTL so active sessions never expire mid-conversation
    await cacheTouch(key, CACHE_TTL);
    return { history, key };
  }

  // 2. Cold path — Supabase (last MAX_HISTORY turns, ordered oldest→newest)
  const { data, error } = await supabase
    .from('conversations')
    .select('role, content, created_at')
    .eq('user_id', userId)
    .eq('session_id', sessionId)
    .order('created_at', { ascending: true })
    .limit(MAX_HISTORY);

  if (error) console.error('[history] Supabase load error:', error.message);

  history = (data || []).map(r => ({ role: r.role, content: r.content, ts: r.created_at }));
  await cacheSet(key, history, CACHE_TTL);
  return { history, key };
}

async function appendHistory(key, history, userId, sessionId, userMsg, botReply) {
  const ts = new Date().toISOString();
  history.push({ role: 'user',      content: userMsg,  ts });
  history.push({ role: 'assistant', content: botReply, ts });

  // Trim to window — keep most recent MAX_HISTORY turns
  if (history.length > MAX_HISTORY) history.splice(0, history.length - MAX_HISTORY);

  // Write-through: Redis first (fast), Supabase second (durable)
  await cacheSet(key, history, CACHE_TTL);
  const { error } = await supabase.from('conversations').insert([
    { user_id: userId, session_id: sessionId, role: 'user',      content: userMsg  },
    { user_id: userId, session_id: sessionId, role: 'assistant', content: botReply },
  ]);
  if (error) console.error('[history] Supabase write error:', error.message);
}

// ─────────────────────────────────────────────────────────────────────────────
// PROFILE  — structured facts, Redis (hot) → Supabase (cold)
// Only facts explicitly stated by the user are stored — never inferred from bot
// ─────────────────────────────────────────────────────────────────────────────
async function loadProfile(userId) {
  const key = profileKey(userId);
  let profile = await cacheGet(key);
  if (profile) return profile;

  const { data, error } = await supabase
    .from('user_profiles')
    .select('*')
    .eq('user_id', userId)
    .single();

  if (error && error.code !== 'PGRST116') // PGRST116 = no rows, that's fine
    console.error('[profile] Supabase load error:', error.message);

  // Convert new column-based structure to flat profile object
  profile = {};
  if (data) {
    if (data.full_name) {
      profile.full_name = data.full_name;
      profile.name = data.full_name;  // Alias for RAG compatibility
    }
    if (data.mother_name) profile.mother_name = data.mother_name;
    if (data.email) profile.email = data.email;
    if (data.phone) profile.phone = data.phone;
    if (data.annual_income) profile.income = data.annual_income;
    if (data.date_of_birth) profile.dob = data.date_of_birth;
    
    // Extract PAN preferences from JSONB
    const prefs = data.pan_preferences || {};
    if (prefs.submission_mode) profile.submission_mode = prefs.submission_mode;
    if (prefs.delivery_mode) profile.delivery_mode = prefs.delivery_mode;
    if (prefs.aadhaar_photo !== undefined) profile.aadhaar_photo = prefs.aadhaar_photo;
    if (prefs.source_of_income) profile.source_of_income = prefs.source_of_income;
    if (prefs.address_for_comm) profile.address_for_comm = prefs.address_for_comm;
    if (prefs.residential_status) profile.residential_status = prefs.residential_status;
    if (prefs.rep_assessee !== undefined) profile.rep_assessee = prefs.rep_assessee;
    if (prefs.applicant_type) profile.applicant_type = prefs.applicant_type;
  }
  
  await cacheSet(key, profile, PROFILE_TTL);
  return profile;
}

async function saveProfile(userId, facts) {
  await cacheSet(profileKey(userId), facts, PROFILE_TTL);
  
  // Convert flat facts object to column-based structure
  const profileData = {
    user_id: userId,
    updated_at: new Date().toISOString(),
  };
  
  // Map fields to columns
  if (facts.full_name || facts.name) profileData.full_name = facts.full_name || facts.name;
  if (facts.mother_name) profileData.mother_name = facts.mother_name;
  if (facts.email) profileData.email = facts.email;
  if (facts.phone) profileData.phone = facts.phone;
  if (facts.income) profileData.annual_income = facts.income;
  if (facts.dob) profileData.date_of_birth = facts.dob;
  
  // Build PAN preferences JSONB
  const panPrefs = {};
  if (facts.submission_mode) panPrefs.submission_mode = facts.submission_mode;
  if (facts.delivery_mode) panPrefs.delivery_mode = facts.delivery_mode;
  if (facts.aadhaar_photo !== undefined) panPrefs.aadhaar_photo = facts.aadhaar_photo;
  if (facts.source_of_income) panPrefs.source_of_income = facts.source_of_income;
  if (facts.address_for_comm) panPrefs.address_for_comm = facts.address_for_comm;
  if (facts.residential_status) panPrefs.residential_status = facts.residential_status;
  if (facts.rep_assessee !== undefined) panPrefs.rep_assessee = facts.rep_assessee;
  if (facts.applicant_type) panPrefs.applicant_type = facts.applicant_type;
  
  if (Object.keys(panPrefs).length > 0) {
    profileData.pan_preferences = panPrefs;
  }
  
  const { error } = await supabase
    .from('user_profiles')
    .upsert(profileData, { onConflict: 'user_id' });
    
  if (error) console.error('[profile] Supabase write error:', error.message);
}

// ─────────────────────────────────────────────────────────────────────────────
// LONG-TERM MEMORY  — semantic search across all past conversations
// Surfaces relevant past exchanges when the user references something old.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Search the user's full conversation history for turns relevant to the query.
 * Uses Postgres full-text search (tsvector) — fast even with thousands of rows.
 * Returns up to MEMORY_SEARCH_LIMIT paired (user + assistant) turns.
 */
async function searchLongTermMemory(userId, query, currentSessionId) {
  try {
    // Build a tsquery from the user's message — take meaningful words only
    const words = query
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, ' ')
      .split(/\s+/)
      .filter(w => w.length > 2 && !STOP_WORDS.has(w))
      .slice(0, 8); // cap at 8 terms

    if (words.length === 0) return [];

    const tsquery = words.join(' | '); // OR search — broad recall

    // Find matching user messages from OTHER sessions (current session already in window)
    const { data, error } = await supabase
      .from('conversations')
      .select('session_id, role, content, created_at')
      .eq('user_id', userId)
      .eq('role', 'user')
      .neq('session_id', currentSessionId)
      .textSearch('content_tsv', tsquery, { type: 'websearch' })
      .order('created_at', { ascending: false })
      .limit(MEMORY_SEARCH_LIMIT);

    if (error) {
      // Fallback: if tsvector column doesn't exist yet, use ilike
      if (error.code === '42703') {
        return await _fallbackMemorySearch(userId, words, currentSessionId);
      }
      console.error('[ltm] search error:', error.message);
      return [];
    }

    if (!data?.length) return [];

    // For each matching user turn, fetch the assistant reply that followed it
    const pairs = [];
    for (const row of data) {
      const { data: reply } = await supabase
        .from('conversations')
        .select('content, created_at')
        .eq('user_id', userId)
        .eq('session_id', row.session_id)
        .eq('role', 'assistant')
        .gt('created_at', row.created_at)
        .order('created_at', { ascending: true })
        .limit(1)
        .single();

      pairs.push({
        user:      row.content,
        assistant: reply?.content || '',
        ts:        row.created_at,
      });
    }

    return pairs;
  } catch (err) {
    console.error('[ltm] searchLongTermMemory error:', err.message);
    return [];
  }
}

/** Fallback when tsvector column isn't migrated yet — simple ilike search */
async function _fallbackMemorySearch(userId, words, currentSessionId) {
  try {
    const pattern = `%${words.slice(0, 3).join('%')}%`;
    const { data } = await supabase
      .from('conversations')
      .select('session_id, role, content, created_at')
      .eq('user_id', userId)
      .eq('role', 'user')
      .neq('session_id', currentSessionId)
      .ilike('content', pattern)
      .order('created_at', { ascending: false })
      .limit(MEMORY_SEARCH_LIMIT);

    if (!data?.length) return [];

    const pairs = [];
    for (const row of data) {
      const { data: reply } = await supabase
        .from('conversations')
        .select('content, created_at')
        .eq('user_id', userId)
        .eq('session_id', row.session_id)
        .eq('role', 'assistant')
        .gt('created_at', row.created_at)
        .order('created_at', { ascending: true })
        .limit(1)
        .single();

      pairs.push({
        user:      row.content,
        assistant: reply?.content || '',
        ts:        row.created_at,
      });
    }
    return pairs;
  } catch { return []; }
}

/**
 * Save a session summary to user_memory_summaries after a session ends
 * or when it reaches a certain length. Called async — never blocks the response.
 */
async function saveSessionSummary(userId, sessionId, history) {
  if (history.length < 4) return; // too short to summarize

  try {
    // Build a compact summary: just the user turns (what the user said/asked)
    const userTurns = history
      .filter(m => m.role === 'user')
      .map(m => m.content)
      .join(' | ');

    // Extract topics from user turns (simple keyword extraction)
    const topics = extractTopics(userTurns);

    const { error } = await supabase
      .from('user_memory_summaries')
      .upsert(
        {
          user_id:    userId,
          session_id: sessionId,
          summary:    userTurns.slice(0, 2000), // cap at 2000 chars
          topics,
          updated_at: new Date().toISOString(),
        },
        { onConflict: 'session_id' }
      );

    if (error) console.error('[ltm] saveSessionSummary error:', error.message);
  } catch (err) {
    console.error('[ltm] saveSessionSummary error:', err.message);
  }
}

/** Extract simple topic tags from text */
function extractTopics(text) {
  const PAN_TOPICS = [
    ['pan', 'pan card', 'pan number', 'pan application'],
    ['aadhaar', 'aadhar'],
    ['tan', 'tds', 'tcs'],
    ['income', 'salary', 'tax'],
    ['correction', 'update', 'change'],
    ['reprint', 'lost', 'duplicate'],
    ['link', 'linking'],
    ['documents', 'upload'],
    ['status', 'track'],
  ];
  const lower = text.toLowerCase();
  const found = [];
  for (const group of PAN_TOPICS) {
    if (group.some(t => lower.includes(t))) found.push(group[0]);
  }
  return found;
}

// Common English stop words to skip in memory search
const STOP_WORDS = new Set([
  'the','a','an','is','are','was','were','be','been','being',
  'have','has','had','do','does','did','will','would','could','should',
  'may','might','shall','can','need','dare','ought','used',
  'i','me','my','myself','we','our','ours','ourselves',
  'you','your','yours','yourself','yourselves',
  'he','him','his','himself','she','her','hers','herself',
  'it','its','itself','they','them','their','theirs','themselves',
  'what','which','who','whom','this','that','these','those',
  'am','and','but','if','or','because','as','until','while',
  'of','at','by','for','with','about','against','between','into',
  'through','during','before','after','above','below','to','from',
  'up','down','in','out','on','off','over','under','again','further',
  'then','once','here','there','when','where','why','how',
  'all','both','each','few','more','most','other','some','such',
  'no','nor','not','only','own','same','so','than','too','very',
  'just','don','should','now',
]);


/**
 * Get the most recent conversation from the user's last session.
 * Used when user asks "where we left off" or "continue from last time".
 */
async function getLastSessionSummary(userId, currentSessionId) {
  try {
    // Find the most recent session (excluding current one)
    const { data: sessions } = await supabase
      .from('chat_sessions')
      .select('id, title, updated_at')
      .eq('user_id', userId)
      .neq('id', currentSessionId)
      .order('updated_at', { ascending: false })
      .limit(1);

    if (!sessions?.length) return null;

    const lastSession = sessions[0];

    // Get the last 6 messages from that session (3 exchanges)
    const { data: messages } = await supabase
      .from('conversations')
      .select('role, content, created_at')
      .eq('user_id', userId)
      .eq('session_id', lastSession.id)
      .order('created_at', { ascending: false })
      .limit(6);

    if (!messages?.length) return null;

    // Reverse to get chronological order
    messages.reverse();

    return {
      session_title: lastSession.title,
      session_date: lastSession.updated_at,
      messages: messages.map(m => ({
        role: m.role,
        content: m.content,
        ts: m.created_at,
      })),
    };
  } catch (err) {
    console.error('[ltm] getLastSessionSummary error:', err.message);
    return null;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// PAN ASSISTANT AI AGENT MEMORY (Redis-based persistent memory)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Load all three memory components for a user in parallel.
 * Returns { history: [], summary: string, preferences: {} }
 */
async function loadAgentMemory(userId) {
  try {
    const [history, summary, preferences] = await Promise.all([
      redis.get(memoryHistoryKey(userId)),
      redis.get(memorySummaryKey(userId)),
      redis.get(memoryPreferencesKey(userId)),
    ]);

    return {
      history: Array.isArray(history) ? history : [],
      summary: summary || '',
      preferences: preferences && typeof preferences === 'object' ? preferences : {},
    };
  } catch (err) {
    console.error('[agent-memory] loadAgentMemory error:', err.message);
    throw new Error('Failed to load agent memory from Redis');
  }
}

/**
 * Save agent memory history to Redis with 30-day TTL.
 */
async function saveAgentHistory(userId, history) {
  try {
    await redis.set(memoryHistoryKey(userId), history, { ex: MEMORY_TTL });
  } catch (err) {
    console.error('[agent-memory] saveAgentHistory error:', err.message);
    throw err;
  }
}

/**
 * Save agent memory summary to Redis with 30-day TTL.
 */
async function saveAgentSummary(userId, summary) {
  try {
    await redis.set(memorySummaryKey(userId), summary, { ex: MEMORY_TTL });
  } catch (err) {
    console.error('[agent-memory] saveAgentSummary error:', err.message);
    throw err;
  }
}

/**
 * Save agent memory preferences to Redis with 30-day TTL.
 */
async function saveAgentPreferences(userId, preferences) {
  try {
    await redis.set(memoryPreferencesKey(userId), preferences, { ex: MEMORY_TTL });
  } catch (err) {
    console.error('[agent-memory] saveAgentPreferences error:', err.message);
    throw err;
  }
}

/**
 * Clear all agent memory for a user.
 */
async function clearAgentMemory(userId) {
  try {
    await Promise.all([
      redis.del(memoryHistoryKey(userId)),
      redis.del(memorySummaryKey(userId)),
      redis.del(memoryPreferencesKey(userId)),
    ]);
  } catch (err) {
    console.error('[agent-memory] clearAgentMemory error:', err.message);
    throw err;
  }
}

/**
 * Trigger AI summarization when history exceeds 20 messages.
 * Calls AI to create a rolling summary and trims history to last 10 messages.
 */
async function triggerSummarization(userId, history, existingSummary) {
  if (history.length <= 20) return;

  try {
    // Build conversation text for summarization
    const conversationText = history
      .map(m => `${m.role === 'user' ? 'User' : 'Assistant'}: ${m.content}`)
      .join('\n');

    const summaryPrompt = `Summarize this conversation in 3-5 sentences focusing on what the user asked, what was resolved, and any important details like PAN number, name, or issues.${existingSummary ? ` Append to existing summary if provided:\n\nExisting summary: ${existingSummary}\n\n` : '\n\n'}Conversation:\n${conversationText}`;

    // Call AI for summarization (using simple fetch to avoid blocking)
    // This is fire-and-forget - we don't wait for the result
    fetch(`${RAG_URL}/api/summarize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: summaryPrompt, user_id: userId }),
      signal: AbortSignal.timeout(30_000),
    })
      .then(async (res) => {
        if (res.ok) {
          const data = await res.json();
          const newSummary = data.summary || '';
          if (newSummary) {
            await saveAgentSummary(userId, newSummary);
            console.log(`[agent-memory] Saved summary for user ${userId.slice(0, 8)}`);
          }
        }
      })
      .catch((err) => {
        console.error('[agent-memory] Summarization failed:', err.message);
      });

    // Trim history to last 10 messages immediately
    const trimmedHistory = history.slice(-10);
    await saveAgentHistory(userId, trimmedHistory);
    
  } catch (err) {
    console.error('[agent-memory] triggerSummarization error:', err.message);
  }
}

/**
 * Trigger preference extraction every 5 messages.
 * Calls AI to extract user facts and merge with existing preferences.
 */
async function triggerPreferenceExtraction(userId, history, existingPreferences) {
  if (history.length % 5 !== 0) return;

  try {
    // Build recent conversation text (last 10 messages)
    const recentText = history
      .slice(-10)
      .map(m => `${m.role === 'user' ? 'User' : 'Assistant'}: ${m.content}`)
      .join('\n');

    const extractionPrompt = `From this conversation extract any user facts worth remembering. Return ONLY a JSON object with these fields: {name, pan, city, aadhaarLinked, commonIssues, preferredLanguage}. Use empty string for unknown fields. Merge with existing: ${JSON.stringify(existingPreferences)}\n\nConversation:\n${recentText}`;

    // Call AI for preference extraction (fire-and-forget)
    fetch(`${RAG_URL}/api/extract-preferences`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: extractionPrompt, user_id: userId }),
      signal: AbortSignal.timeout(30_000),
    })
      .then(async (res) => {
        if (res.ok) {
          const data = await res.json();
          try {
            const newPreferences = typeof data.preferences === 'string' 
              ? JSON.parse(data.preferences) 
              : data.preferences;
            
            if (newPreferences && typeof newPreferences === 'object') {
              // Merge with existing preferences
              const merged = { ...existingPreferences, ...newPreferences };
              await saveAgentPreferences(userId, merged);
              console.log(`[agent-memory] Updated preferences for user ${userId.slice(0, 8)}`);
            }
          } catch (parseErr) {
            console.error('[agent-memory] Failed to parse preferences JSON:', parseErr.message);
          }
        }
      })
      .catch((err) => {
        console.error('[agent-memory] Preference extraction failed:', err.message);
      });
    
  } catch (err) {
    console.error('[agent-memory] triggerPreferenceExtraction error:', err.message);
  }
}

/**
 * Build dynamic system prompt for PAN Assistant AI Agent.
 */
function buildAgentSystemPrompt(summary, preferences) {
  let prompt = `You are PAN Assistant, an expert AI agent helping Indian users with everything related to PAN cards — application, correction, linking with Aadhaar, income tax, TDS, Form 26AS, PAN for minors, NRIs, companies, and lost PAN recovery. You are friendly, concise, and accurate. Never make up PAN-related legal or tax information — say you're unsure if you don't know.`;

  if (summary) {
    prompt += `\n\nSummary of past conversations with this user:\n${summary}`;
  }

  if (preferences && Object.keys(preferences).length > 0) {
    prompt += `\n\nKnown facts about this user:\n${JSON.stringify(preferences, null, 2)}`;
  }

  return prompt;
}

/**
 * Check if the user is asking about their last session/conversation.
 */
function _isAskingAboutLastSession(message) {
  const m = message.toLowerCase();
  const LAST_SESSION_PATTERNS = [
    'where we left', 'where did we', 'where were we',
    'where i left', 'where did i', 'where was i',
    'continue', 'resume', 'pick up where',
    'last conversation', 'previous chat', 'last session', 'last time',
    'what were we', 'what was i',
  ];
  return LAST_SESSION_PATTERNS.some(p => m.includes(p));
}

/**
 * Check if the user is asking about their stored data/information.
 * Returns { isAsking: boolean, specificField: string|null }
 */
function _isAskingAboutStoredData(message) {
  const m = message.toLowerCase();
  
  // General patterns - asking about all stored data
  const GENERAL_PATTERNS = [
    // What do you know
    'what do you know about me', 'what you know about me', 'what do u know about me',
    'what all do you know', 'what all you know', 'what info do you have',
    'what information do you have', 'what data do you have', 'what details do you have',
    
    // What did I give/tell/provide
    'what did i give', 'what did i tell', 'what did i provide', 'what did i share',
    'what have i given', 'what have i told', 'what have i provided', 'what have i shared',
    'what i gave', 'what i told', 'what i provided', 'what i shared',
    'what details did i give', 'what details did i provide', 'what info did i give',
    
    // Show/tell me my data
    'show me my details', 'show my details', 'show me my info', 'show my info',
    'show me my data', 'show my data', 'tell me my details', 'tell my details',
    'give me my details', 'give my details', 'list my details', 'list my info',
    
    // What information/details
    'what information i gave', 'what details i gave', 'what data i gave',
    'what information i provided', 'what details i provided', 'what data i provided',
    'what information do you have about me', 'what details do you have about me',
    
    // My profile/information
    'my profile', 'my information', 'my details', 'my data', 'about me',
    'show profile', 'view profile', 'see profile', 'check profile',
    'show information', 'view information', 'see information',
    
    // What have you saved/stored/remembered
    'what have you saved', 'what did you save', 'what you saved',
    'what have you stored', 'what did you store', 'what you stored',
    'what have you remembered', 'what did you remember', 'what you remember',
    'what do you remember about me', 'what you remember about me',
    
    // Recall/retrieve
    'recall my details', 'recall my info', 'retrieve my details', 'retrieve my info',
    'get my details', 'get my info', 'fetch my details', 'fetch my info',
    
    // Summary/overview
    'give me a summary', 'give summary', 'summarize my info', 'summarize my details',
    'overview of my details', 'overview of my info', 'summary of my data',
  ];
  
  // Specific field patterns - asking about particular information
  // IMPORTANT: These patterns should NOT match when user is PROVIDING data (e.g., "my name is X")
  // We check for "is", "are", "was" after the field to exclude providing statements
  const SPECIFIC_PATTERNS = {
    name: [
      'what is my name', 'whats my name', 'what name did i give',
      'what name i provided', 'do you know my name', 'tell me my name',
      'what did i say my name was', 'remind me my name',
    ],
    email: [
      'what is my email', 'whats my email', 'what email did i give',
      'what email i provided', 'do you know my email', 'tell me my email',
      'what email address',
    ],
    phone: [
      'what is my phone', 'whats my phone', 'what phone did i give',
      'what phone number', 'what number did i give', 'tell me my phone',
    ],
    pan: [
      'what is my pan', 'whats my pan', 'what pan did i give',
      'what pan number', 'do you have my pan',
      'tell me my pan', 'what pan i provided',
    ],
    aadhaar: [
      'what is my aadhaar', 'whats my aadhaar', 'what aadhaar did i give',
      'what aadhaar number', 'do you have my aadhaar',
    ],
    address: [
      'what is my address', 'whats my address', 'what address did i give',
      'where do i live', 'tell me my address',
    ],
    income: [
      'what is my income', 'whats my income', 'what is my salary', 'whats my salary',
      'what salary did i give', 'what income did i give', 'how much do i earn',
      'tell me my income', 'tell me my salary', 'do you have my income', 'do you have my salary',
    ],
    dob: [
      'what is my dob', 'whats my dob', 'what is my date of birth',
      'when was i born', 'what dob did i give',
    ],
    mother_name: [
      'what is my mother name', 'whats my mother name',
      'what mother name did i give',
    ],
  };
  
  // Check for general patterns
  for (const pattern of GENERAL_PATTERNS) {
    if (m.includes(pattern)) {
      return { isAsking: true, specificField: null };
    }
  }
  
  // Check for specific field patterns
  for (const [field, patterns] of Object.entries(SPECIFIC_PATTERNS)) {
    for (const pattern of patterns) {
      if (m.includes(pattern)) {
        // CRITICAL: Exclude if user is PROVIDING data (e.g., "my salary is 6 lakhs")
        // Check if message contains patterns like "my [field] is/are/was X"
        const providingPattern = new RegExp(`\\b(my|the)\\s+(${field}|salary|income|name|email|mother|mothers?|mother's)\\s+(is|are|was|were)\\s+\\S`, 'i');
        if (providingPattern.test(message)) {
          console.log(`[stored-data-intent] Skipping ${field} - user is providing data, not asking`);
          continue; // Skip this pattern, user is providing data
        }
        return { isAsking: true, specificField: field };
      }
    }
  }
  
  return { isAsking: false, specificField: null };
}

/**
 * Build a response showing user's stored data.
 * Can show all data or specific field based on request.
 */
function _buildStoredDataResponse(profile, agentMemory, specificField = null) {
  // If asking for specific field
  if (specificField) {
    const fieldMap = {
      name: profile.full_name || profile.name,
      email: profile.email,
      phone: profile.phone,
      pan: profile.pan_number,
      aadhaar: profile.aadhaar,
      address: profile.address,
      income: profile.income || profile.annual_income,
      dob: profile.dob || profile.date_of_birth,
      mother_name: profile.mother_name,
    };
    
    const value = fieldMap[specificField];
    const fieldNames = {
      name: 'name',
      email: 'email',
      phone: 'phone number',
      pan: 'PAN number',
      aadhaar: 'Aadhaar number',
      address: 'address',
      income: 'annual income',
      dob: 'date of birth',
      mother_name: "mother's name",
    };
    
    if (value) {
      return {
        answer: `Your ${fieldNames[specificField]} is: **${value}**`,
        sources: [],
        followups: ['Show me all my details', 'Update my information', 'Continue with PAN application'],
        guided: false,
      };
    } else {
      return {
        answer: `I don't have your ${fieldNames[specificField]} on record yet. Would you like to provide it?`,
        sources: [],
        followups: ['Show me what you know about me', 'Continue with PAN application'],
        guided: false,
      };
    }
  }
  
  // Build comprehensive response with all stored data
  const sections = [];
  
  // Personal Information
  const personalInfo = [];
  if (profile.full_name || profile.name) personalInfo.push(`- **Name**: ${profile.full_name || profile.name}`);
  if (profile.mother_name) personalInfo.push(`- **Mother's Name**: ${profile.mother_name}`);
  if (profile.dob || profile.date_of_birth) personalInfo.push(`- **Date of Birth**: ${profile.dob || profile.date_of_birth}`);
  if (profile.gender) personalInfo.push(`- **Gender**: ${profile.gender}`);
  
  if (personalInfo.length > 0) {
    sections.push('### 👤 Personal Information\n' + personalInfo.join('\n'));
  }
  
  // Contact Information
  const contactInfo = [];
  if (profile.email) contactInfo.push(`- **Email**: ${profile.email}`);
  if (profile.phone) contactInfo.push(`- **Phone**: ${profile.phone}`);
  if (profile.address) contactInfo.push(`- **Address**: ${profile.address}`);
  
  if (contactInfo.length > 0) {
    sections.push('### 📞 Contact Information\n' + contactInfo.join('\n'));
  }
  
  // Identity Documents
  const identityInfo = [];
  if (profile.pan_number) identityInfo.push(`- **PAN Number**: ${profile.pan_number}`);
  if (profile.aadhaar) identityInfo.push(`- **Aadhaar Number**: ${profile.aadhaar}`);
  
  if (identityInfo.length > 0) {
    sections.push('### 🆔 Identity Documents\n' + identityInfo.join('\n'));
  }
  
  // Financial Information
  const financialInfo = [];
  if (profile.income || profile.annual_income) {
    financialInfo.push(`- **Annual Income**: ₹${profile.income || profile.annual_income}`);
  }
  if (profile.source_of_income) {
    const sources = Array.isArray(profile.source_of_income) 
      ? profile.source_of_income.join(', ') 
      : profile.source_of_income;
    financialInfo.push(`- **Source of Income**: ${sources}`);
  }
  
  if (financialInfo.length > 0) {
    sections.push('### 💰 Financial Information\n' + financialInfo.join('\n'));
  }
  
  // PAN Application Preferences
  const panPrefs = [];
  if (profile.submission_mode) panPrefs.push(`- **Submission Mode**: ${profile.submission_mode}`);
  if (profile.delivery_mode) panPrefs.push(`- **Delivery Mode**: ${profile.delivery_mode}`);
  if (profile.aadhaar_photo !== undefined) {
    panPrefs.push(`- **Aadhaar Photo on PAN**: ${profile.aadhaar_photo ? 'Yes' : 'No'}`);
  }
  if (profile.address_for_comm) panPrefs.push(`- **Address for Communication**: ${profile.address_for_comm}`);
  if (profile.residential_status) panPrefs.push(`- **Residential Status**: ${profile.residential_status}`);
  if (profile.rep_assessee !== undefined) {
    panPrefs.push(`- **Representative Assessee**: ${profile.rep_assessee ? 'Yes' : 'No'}`);
  }
  if (profile.applicant_type) panPrefs.push(`- **Applicant Type**: ${profile.applicant_type}`);
  
  if (panPrefs.length > 0) {
    sections.push('### 📋 PAN Application Preferences\n' + panPrefs.join('\n'));
  }
  
  // Agent Memory Preferences (from AI extraction)
  if (agentMemory.preferences && Object.keys(agentMemory.preferences).length > 0) {
    const memPrefs = [];
    const prefs = agentMemory.preferences;
    if (prefs.city) memPrefs.push(`- **City**: ${prefs.city}`);
    if (prefs.aadhaarLinked) memPrefs.push(`- **Aadhaar Linked**: ${prefs.aadhaarLinked}`);
    if (prefs.commonIssues) memPrefs.push(`- **Common Issues**: ${prefs.commonIssues}`);
    if (prefs.preferredLanguage) memPrefs.push(`- **Preferred Language**: ${prefs.preferredLanguage}`);
    
    if (memPrefs.length > 0) {
      sections.push('### 🧠 Additional Information\n' + memPrefs.join('\n'));
    }
  }
  
  // Conversation Summary
  if (agentMemory.summary) {
    sections.push(`### 💬 Conversation Summary\n${agentMemory.summary}`);
  }
  
  // Build final response
  if (sections.length === 0) {
    return {
      answer: "I don't have any information about you yet. As we chat and you share details, I'll remember them to make our conversations more helpful.\n\nWould you like to start a PAN application or ask me anything about PAN services?",
      sources: [],
      followups: ['Apply for new PAN', 'Check PAN status', 'Link Aadhaar with PAN'],
      guided: false,
    };
  }
  
  const answer = `Here's everything I know about you:\n\n${sections.join('\n\n')}\n\n---\n\n*This information is stored securely and will be remembered for 30 days to make our conversations more helpful.*`;
  
  return {
    answer,
    sources: [],
    followups: ['Update my information', 'Clear my data', 'Continue with PAN application'],
    guided: false,
  };
}

/**
 * Decide whether to run a long-term memory search for this message.
 * Always search for explicit memory references; also search for
 * substantive questions that might have been answered in a past session.
 */
function _shouldSearchMemory(message) {
  const m = message.toLowerCase();

  // Explicit memory references — always search
  const EXPLICIT = [
    'last time', 'previously', 'before', 'earlier', 'you told me', 'you said',
    'i asked', 'i told you', 'i mentioned', 'i said', 'i gave', 'i provided',
    'remember', 'recall',
    'what did i', 'what was', 'what were', 'what are the', 'what is the',
    'did i ask', 'did you tell', 'did i give', 'did i provide',
    'history', 'past', 'old', 'again', 'repeat', 'remind me',
    'where we left', 'where did we', 'where i left', 'where did i',
    'continue', 'resume', 'pick up',
    'last conversation', 'previous chat', 'last session',
    'details i', 'information i', 'data i',
  ];
  if (EXPLICIT.some(p => m.includes(p))) return true;

  // Substantive questions about PAN topics — search for prior context
  const TOPIC_QUESTION = /\b(how|what|when|where|which|why|can i|do i|should i|is it|are there)\b.{0,60}\b(pan|aadhaar|tan|tds|document|fee|status|link|apply|correct|reprint|form)\b/i;
  if (TOPIC_QUESTION.test(message)) return true;

  return false;
}

// ─────────────────────────────────────────────────────────────────────────────
// CONTEXT BUILDER  — assembles the structured block sent to RAG
// ─────────────────────────────────────────────────────────────────────────────
function buildUserContext(profile, history, longTermMemory = [], lastSessionSummary = null) {
  const parts = [];

  // ── Profile block — everything we know about the user ──
  const _ACTION_WORDS = /\b(apply|register|get|create|obtain|pan|card|application|here|there|trying|going|looking|planning|wanting|citizen|entity|indian|foreign|company|huf|firm|nri)\b/i;
  const _isValidName = (n) => n && n.trim().length >= 2 && !_ACTION_WORDS.test(n) && n.trim().split(/\s+/).length <= 5;

  const profileLines = [];
  
  // Personal details
  if (profile.full_name)    profileLines.push(`- Full name: ${profile.full_name}`);
  if (profile.mother_name)  profileLines.push(`- Mother's name: ${profile.mother_name}`);
  if (profile.email)        profileLines.push(`- Email: ${profile.email}`);
  if (profile.phone)        profileLines.push(`- Phone: ${profile.phone}`);
  if (profile.income !== undefined && profile.income !== null && profile.income !== '')
                            profileLines.push(`- Annual income: ${profile.income}`);
  if (profile.dob)          profileLines.push(`- Date of birth: ${profile.dob}`);
  
  // PAN application preferences
  if (profile.submission_mode)    profileLines.push(`- Submission mode: ${profile.submission_mode}`);
  if (profile.delivery_mode)      profileLines.push(`- PAN delivery: ${profile.delivery_mode}`);
  if (profile.aadhaar_photo !== undefined) 
                                  profileLines.push(`- Aadhaar photo on PAN: ${profile.aadhaar_photo ? 'Yes' : 'No'}`);
  if (profile.source_of_income)   profileLines.push(`- Source of income: ${profile.source_of_income}`);
  if (profile.address_for_comm)   profileLines.push(`- Address for communication: ${profile.address_for_comm}`);
  if (profile.residential_status) profileLines.push(`- Residential status: ${profile.residential_status}`);
  if (profile.rep_assessee !== undefined) 
                                  profileLines.push(`- Representative Assessee: ${profile.rep_assessee ? 'Yes' : 'No'}`);
  if (profile.applicant_type)     profileLines.push(`- Applicant type: ${profile.applicant_type}`);
  
  // Legacy fields (for backward compatibility)
  if (profile.gender)       profileLines.push(`- Gender: ${profile.gender}`);
  if (profile.pan_number)   profileLines.push(`- PAN number: ${profile.pan_number}`);
  if (profile.aadhaar)      profileLines.push(`- Aadhaar: ${profile.aadhaar}`);
  if (profile.address)      profileLines.push(`- Address: ${profile.address}`);

  if (profileLines.length) {
    parts.push(
      '=== VERIFIED USER FACTS ===\n' +
      profileLines.join('\n') + '\n' +
      'RULE: Never ask for information already listed above. Use it directly.'
    );
  }

  // ── Last session summary — when user asks "where we left off" ──
  if (lastSessionSummary) {
    const date = new Date(lastSessionSummary.session_date).toLocaleDateString('en-IN', { 
      day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' 
    });
    const lines = [
      '=== YOUR LAST CONVERSATION ===',
      `Session: "${lastSessionSummary.session_title}" (${date})`,
      '',
    ];
    for (const msg of lastSessionSummary.messages) {
      const role = msg.role === 'assistant' ? 'Assistant' : 'User';
      lines.push(`${role}: ${msg.content}`);
    }
    lines.push('');
    lines.push('RULE: The user is asking about this previous conversation. Summarize what you were discussing and offer to continue or help with something new.');
    parts.push(lines.join('\n'));
  }

  // ── Long-term memory — relevant past exchanges from older sessions ──
  if (longTermMemory.length) {
    const lines = ['=== RELEVANT PAST CONVERSATIONS ==='];
    for (const pair of longTermMemory) {
      const date = new Date(pair.ts).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
      lines.push(`[${date}] User: ${pair.user}`);
      if (pair.assistant) lines.push(`[${date}] Assistant: ${pair.assistant.slice(0, 300)}${pair.assistant.length > 300 ? '…' : ''}`);
    }
    lines.push('RULE: Use the above past context to answer questions about what the user previously asked or was told.');
    parts.push(lines.join('\n'));
  }

  // ── Recent conversation window ──
  const window = history.slice(-WINDOW_TURNS * 2);
  if (window.length) {
    const lines = ['=== RECENT CONVERSATION ==='];
    for (const msg of window) {
      lines.push(`${msg.role === 'assistant' ? 'Assistant' : 'User'}: ${msg.content}`);
    }
    lines.push('RULE: Answer from this conversation directly if the user references it.');
    parts.push(lines.join('\n'));
  }

  return parts.join('\n\n');
}

// ─────────────────────────────────────────────────────────────────────────────
// SESSION ROUTES
// ─────────────────────────────────────────────────────────────────────────────
router.get('/sessions', verifyToken, async (req, res) => {
  const { data, error } = await supabase
    .from('chat_sessions')
    .select('id, title, created_at, updated_at')
    .eq('user_id', req.user.id)
    .order('updated_at', { ascending: false });
  if (error) return res.status(500).json({ error: 'Failed to load sessions.' });
  return res.json({ sessions: data || [] });
});

router.post('/sessions', verifyToken, async (req, res) => {
  const { data, error } = await supabase
    .from('chat_sessions')
    .insert({ user_id: req.user.id, title: 'New Chat' })
    .select('id, title, created_at, updated_at')
    .single();
  if (error) return res.status(500).json({ error: 'Failed to create session.' });

  // Clear any stale RAG flow state for this session
  fetch(`${RAG_URL}/api/session/${data.id}`, { method: 'DELETE' }).catch(() => {});

  return res.json({ session: data });
});

router.delete('/sessions/:id', verifyToken, async (req, res) => {
  const { id } = req.params;
  const uid = req.user.id;

  try {
    // Clear Redis caches
    await cacheDel(histKey(uid, id));

    // Delete conversations (FK) first
    await supabase.from('conversations').delete().eq('session_id', id).eq('user_id', uid);

    // Delete memory summaries
    await supabase.from('user_memory_summaries').delete().eq('session_id', id).eq('user_id', uid);

    // Delete the session itself
    await supabase.from('chat_sessions').delete().eq('id', id).eq('user_id', uid);

    // Check if user has any remaining sessions — if none, clear their profile too
    const { data: remaining } = await supabase
      .from('chat_sessions')
      .select('id')
      .eq('user_id', uid)
      .limit(1);

    if (!remaining?.length) {
      // No sessions left — wipe profile facts and profile cache
      await supabase.from('user_profiles').delete().eq('user_id', uid);
      await cacheDel(profileKey(uid));
    }

    // Clear RAG flow state (fire-and-forget)
    fetch(`${RAG_URL}/api/session/${id}`, { method: 'DELETE' }).catch(() => {});

    return res.json({ message: 'Session deleted.' });
  } catch (err) {
    console.error('[delete session] error:', err.message);
    return res.status(500).json({ error: 'Failed to delete session.' });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// HISTORY ROUTE  — used by frontend when switching sessions
// ─────────────────────────────────────────────────────────────────────────────
router.get('/history/:sessionId', verifyToken, async (req, res) => {
  try {
    const userId = req.user.id;
    const sessionId = req.params.sessionId;
    
    // ── SECURITY: Validate session ownership ──────────────────────────────────
    const { data: sessionCheck, error: sessionError } = await supabase
      .from('chat_sessions')
      .select('id')
      .eq('id', sessionId)
      .eq('user_id', userId)
      .single();
    
    if (sessionError || !sessionCheck) {
      console.error(`[history] SECURITY: User ${userId.slice(0,8)} attempted to access session ${sessionId.slice(0,8)} they don't own`);
      return res.status(403).json({ error: 'Session not found or access denied.' });
    }
    
    // Load chat history and flow state in parallel
    const [{ history }, flowStateResult] = await Promise.all([
      loadHistory(userId, sessionId),
      // Fetch flow state from Python RAG server (non-blocking — graceful degradation)
      fetch(`${RAG_URL}/flow-state/${encodeURIComponent(userId)}/${encodeURIComponent(sessionId)}`)
        .then(r => r.ok ? r.json() : null)
        .catch(() => null),
    ]);

    return res.json({ history, flow_state: flowStateResult || null });
  } catch (err) {
    console.error('[history] GET error:', err);
    return res.status(500).json({ error: 'Failed to load history.' });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// PROFILE ROUTE
// ─────────────────────────────────────────────────────────────────────────────
router.get('/profile', verifyToken, async (req, res) => {
  const profile = await loadProfile(req.user.id);
  return res.json({ profile });
});

// ─────────────────────────────────────────────────────────────────────────────
// MAIN CHAT ROUTE  — SSE streaming
// ─────────────────────────────────────────────────────────────────────────────
router.post('/', verifyToken, async (req, res) => {
  const { message, session_id, language } = req.body;
  const userId = req.user.id;

  if (!message?.trim()) return res.status(400).json({ error: 'Message is required.' });
  if (!session_id)       return res.status(400).json({ error: 'session_id is required.' });

  try {
    const _t = Date.now();

    // ── SECURITY: Validate session ownership ──────────────────────────────────
    // Ensure the session_id belongs to this user before loading any data
    const { data: sessionCheck, error: sessionError } = await supabase
      .from('chat_sessions')
      .select('id')
      .eq('id', session_id)
      .eq('user_id', userId)
      .single();
    
    if (sessionError || !sessionCheck) {
      console.error(`[chat] SECURITY: User ${userId.slice(0,8)} attempted to access session ${session_id.slice(0,8)} they don't own`);
      return res.status(403).json({ error: 'Session not found or access denied.' });
    }

    // 1. Load history + profile + agent memory in parallel
    const [{ history, key: cacheKey }, profile, agentMemory] = await Promise.all([
      loadHistory(userId, session_id),
      loadProfile(userId),
      loadAgentMemory(userId),
    ]);

    // 1b. If user is starting a PAN application, force-refresh profile from Supabase
    // to ensure latest saved preferences are included (bypasses stale Redis cache)
    const _PAN_APPLY_MSG = /\b(apply|wanna|want|get|create|register|obtain)\b.{0,30}\bpan\b|\bnew\s+pan\b|\bpan\s+(card\s+)?(apply|application)\b/i;
    if (_PAN_APPLY_MSG.test(message)) {
      await cacheDel(profileKey(userId));
      const freshProfile = await loadProfile(userId);
      Object.assign(profile, freshProfile);
    }

    // 1c. Check if user is asking about their stored data
    const storedDataQuery = _isAskingAboutStoredData(message);
    console.log('[stored-data-intent] Query:', message);
    console.log('[stored-data-intent] Detection result:', storedDataQuery);
    
    if (storedDataQuery.isAsking) {
      console.log('[stored-data-intent] Building response for user:', userId.slice(0, 8));
      const response = _buildStoredDataResponse(profile, agentMemory, storedDataQuery.specificField);
      
      // Still append to history for memory continuity
      const ts = new Date().toISOString();
      agentMemory.history.push({ role: 'user', content: message, ts });
      agentMemory.history.push({ role: 'assistant', content: response.answer, ts: new Date().toISOString() });
      
      // Save memory (non-blocking)
      saveAgentHistory(userId, agentMemory.history).catch(() => {});
      
      // Also save to session history
      await appendHistory(cacheKey, history, userId, session_id, message, response.answer);
      
      // Update session timestamp
      await supabase
        .from('chat_sessions')
        .update({ updated_at: new Date().toISOString() })
        .eq('id', session_id)
        .eq('user_id', userId);
      
      console.log('[stored-data-intent] Returning response, NOT calling RAG');
      return res.json(response);
    }

    // 1d. Check if user is asking about their last session
    const lastSessionSummary = _isAskingAboutLastSession(message)
      ? await getLastSessionSummary(userId, session_id)
      : null;

    // 1e. Long-term memory search — runs in parallel, only when query looks
    //     like it references past context ("what did I ask", "last time", etc.)
    //     or is a factual question that might have been answered before.
    const longTermMemory = _shouldSearchMemory(message)
      ? await searchLongTermMemory(userId, message, session_id)
      : [];

    // 2. Build structured context block for RAG (using updated profile + LTM + last session)
    const userContext = buildUserContext(profile, history, longTermMemory, lastSessionSummary);

    // 2b. Build agent system prompt with memory (ONLY if RAG supports it)
    // NOTE: Temporarily disabled to prevent hallucinations until RAG is updated
    // const agentSystemPrompt = buildAgentSystemPrompt(agentMemory.summary, agentMemory.preferences);
    const agentSystemPrompt = null; // Disabled until RAG properly handles system_prompt
    
    // 2c. Append new user message to agent memory history
    const ts = new Date().toISOString();
    agentMemory.history.push({ role: 'user', content: message, ts });

    // 3. Open SSE stream to RAG
    let ragRes;
    try {
      const ragPayload = {
        question:      message,
        session_id,
        user_id:       userId,
        user_context:  userContext,
        account_email: req.user.email || '',
        language:      language || undefined,
      };
      
      // Only include system_prompt if it's not null (to prevent hallucinations)
      if (agentSystemPrompt) {
        ragPayload.system_prompt = agentSystemPrompt;
      }
      
      ragRes = await fetch(`${RAG_URL}/api/ask-stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ragPayload),
        signal: AbortSignal.timeout(90_000),
      });

      // If streaming endpoint not available yet, fall back to non-streaming
      if (ragRes.status === 404 || ragRes.status === 405) {
        const fallbackPayload = {
          question: message,
          session_id,
          user_id: userId,
          user_context: userContext,
          account_email: req.user.email || '',
          language: language || undefined,
        };
        
        // Only include system_prompt if it's not null
        if (agentSystemPrompt) {
          fallbackPayload.system_prompt = agentSystemPrompt;
        }
        
        const fallbackRes = await fetch(`${RAG_URL}/api/ask`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(fallbackPayload),
          signal: AbortSignal.timeout(90_000),
        });
        if (!fallbackRes.ok) return res.status(502).json({ error: 'RAG pipeline error.' });
        const ragData = await fallbackRes.json();
        const reply = ragData.answer;
        
        // Append assistant reply to agent memory
        agentMemory.history.push({ role: 'assistant', content: reply, ts: new Date().toISOString() });
        
        // Save agent memory (non-blocking)
        saveAgentHistory(userId, agentMemory.history).catch(() => {});
        
        // Trigger summarization if needed (non-blocking)
        if (agentMemory.history.length > 20) {
          triggerSummarization(userId, agentMemory.history, agentMemory.summary).catch(() => {});
        }
        
        // Trigger preference extraction every 5 messages (non-blocking)
        triggerPreferenceExtraction(userId, agentMemory.history, agentMemory.preferences).catch(() => {});
        
        await appendHistory(cacheKey, history, userId, session_id, message, reply);
        const isFirst = history.length === 2;
        const title   = message.length > 40 ? message.slice(0, 40) + '…' : message;
        await supabase.from('chat_sessions')
          .update({ ...(isFirst && { title }), updated_at: new Date().toISOString() })
          .eq('id', session_id).eq('user_id', userId);
        return res.json({ answer: reply, session_id, sources: ragData.sources || [], followups: ragData.followups || [], open_upload: ragData.open_upload || false, form_data: ragData.form_data || null, field_buttons: ragData.field_buttons || null, title: isFirst ? title : undefined, elapsed_ms: ragData.elapsed_ms });
      }

      if (!ragRes.ok) return res.status(502).json({ error: 'RAG pipeline error.' });
    } catch (fetchErr) {
      const reason = fetchErr.cause?.message || fetchErr.message || '';
      if (fetchErr.name === 'TimeoutError' || reason.includes('timeout'))
        return res.status(503).json({ error: 'Taking longer than usual — please try again.' });
      console.error('[chat] RAG unreachable:', reason);
      return res.status(503).json({ error: 'AI service unavailable. Make sure the RAG server is running on port 8000.' });
    }

    // 4. Set up SSE response to frontend
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('X-Accel-Buffering', 'no');
    res.flushHeaders();

    // 5. Proxy the SSE stream, intercept meta/done to do persistence
    let metaData   = null;
    let fullAnswer = '';
    let titleSent  = false;

    const reader = ragRes.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop(); // keep incomplete line

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        let event;
        try { event = JSON.parse(line.slice(6)); } catch { continue; }

        if (event.type === 'meta') {
          metaData = event;
          // Forward meta to frontend (strip internal type field)
          res.write(`data: ${JSON.stringify({ type: 'meta', session_id: event.session_id, intent: event.intent, sources: event.sources || [], followups: event.followups || [], open_upload: event.open_upload || false, form_data: event.form_data || null, options: event.options || null, confirm_action: event.confirm_action || false, flow_confirmed: event.flow_confirmed || false, flow_data: event.flow_data || null, field_buttons: event.field_buttons || null, confirmation_fields: event.confirmation_fields || null })}\n\n`);

        } else if (event.type === 'token') {
          fullAnswer += event.text;
          res.write(`data: ${JSON.stringify({ type: 'token', text: event.text })}\n\n`);

        } else if (event.type === 'replace') {
          // Hallucination correction — replace accumulated answer
          fullAnswer = event.text;
          res.write(`data: ${JSON.stringify({ type: 'replace', text: event.text })}\n\n`);

        } else if (event.type === 'done') {
          // Append assistant reply to agent memory
          agentMemory.history.push({ role: 'assistant', content: fullAnswer, ts: new Date().toISOString() });
          
          // Save agent memory (non-blocking)
          saveAgentHistory(userId, agentMemory.history).catch(() => {});
          
          // Trigger summarization if needed (non-blocking)
          if (agentMemory.history.length > 20) {
            triggerSummarization(userId, agentMemory.history, agentMemory.summary).catch(() => {});
          }
          
          // Trigger preference extraction every 5 messages (non-blocking)
          triggerPreferenceExtraction(userId, agentMemory.history, agentMemory.preferences).catch(() => {});
          
          // Persist conversation turn
          await appendHistory(cacheKey, history, userId, session_id, message, fullAnswer);

          // ── Persist confirmed flow details to user profile ──────
          // When the user confirms their application details, save them
          // to the profile so they're available in future sessions.
          const flowConfirmed = metaData?.flow_confirmed || event.flow_confirmed;
          const flowData      = metaData?.flow_data      || event.flow_data || event.collected_facts;
          if (flowConfirmed && flowData && Object.keys(flowData).length) {
            const profileUpdates = {};
            // Personal details
            if (flowData.full_name || flowData.name) profileUpdates.full_name  = flowData.full_name || flowData.name;
            if (flowData.mother_name)  profileUpdates.mother_name = flowData.mother_name;
            if (flowData.email)        profileUpdates.email        = flowData.email;
            if (flowData.salary || flowData.income) profileUpdates.income = flowData.salary || flowData.income;
            // PAN preferences — save ALL of them
            if (flowData.submission_mode)    profileUpdates.submission_mode    = flowData.submission_mode;
            if (flowData.delivery_mode)      profileUpdates.delivery_mode      = flowData.delivery_mode;
            if (flowData.aadhaar_photo !== undefined) profileUpdates.aadhaar_photo = flowData.aadhaar_photo;
            if (flowData.source_of_income)   profileUpdates.source_of_income   = flowData.source_of_income;
            if (flowData.address_for_comm)   profileUpdates.address_for_comm   = flowData.address_for_comm;
            if (flowData.residential_status) profileUpdates.residential_status = flowData.residential_status;
            if (flowData.rep_assessee !== undefined) profileUpdates.rep_assessee = flowData.rep_assessee;
            if (flowData.applicant_type)     profileUpdates.applicant_type     = flowData.applicant_type;
            if (Object.keys(profileUpdates).length) {
              const updatedProfile = { ...profile, ...profileUpdates };
              // Invalidate Redis cache so next request gets fresh data
              await cacheDel(profileKey(userId));
              saveProfile(userId, updatedProfile).catch(() => {});
            }
          }

          // Auto-title session on first turn
          const isFirst = history.length === 2;
          const title   = message.length > 40 ? message.slice(0, 40) + '…' : message;
          await supabase
            .from('chat_sessions')
            .update({ ...(isFirst && { title }), updated_at: new Date().toISOString() })
            .eq('id', session_id)
            .eq('user_id', userId);

          if (isFirst) {
            res.write(`data: ${JSON.stringify({ type: 'title', title })}\n\n`);
          }

          // Save session summary for long-term memory (fire-and-forget, every 10 turns)
          if (history.length > 0 && history.length % 10 === 0) {
            saveSessionSummary(userId, session_id, history).catch(() => {});
          }

          console.log(`⏱  [chat] session=${session_id.slice(0,8)} intent=${metaData?.intent || '?'} ${((Date.now()-_t)/1000).toFixed(2)}s`);
          res.write(`data: ${JSON.stringify({ type: 'done', elapsed_ms: event.elapsed_ms ?? (Date.now() - _t) })}\n\n`);
          res.end();
          return;

        } else if (event.type === 'error') {
          res.write(`data: ${JSON.stringify({ type: 'error', message: event.message })}\n\n`);
          res.end();
          return;
        }
      }
    }

    res.end();

  } catch (err) {
    console.error('[chat] Unhandled error:', err);
    if (!res.headersSent) {
      return res.status(500).json({ error: 'Something went wrong.' });
    }
    res.write(`data: ${JSON.stringify({ type: 'error', message: 'Something went wrong.' })}\n\n`);
    res.end();
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// AGENT MEMORY ROUTES
// ─────────────────────────────────────────────────────────────────────────────

/**
 * DELETE /api/chat/memory - Clear all memory for logged-in user
 */
router.delete('/memory', verifyToken, async (req, res) => {
  try {
    await clearAgentMemory(req.user.id);
    return res.json({ message: 'Memory cleared.' });
  } catch (err) {
    console.error('[agent-memory] DELETE /memory error:', err);
    return res.status(500).json({ error: 'Failed to clear memory.' });
  }
});

/**
 * GET /api/chat/memory - Get memory for logged-in user (for profile/debug page)
 */
router.get('/memory', verifyToken, async (req, res) => {
  try {
    const { history, summary, preferences } = await loadAgentMemory(req.user.id);
    return res.json({
      summary,
      preferences,
      messageCount: history.length,
    });
  } catch (err) {
    console.error('[agent-memory] GET /memory error:', err);
    return res.status(500).json({ error: 'Failed to load memory.' });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// VOICE ROUTE  — STT → full chat pipeline → TTS
// Receives raw audio, returns WAV audio + transcript/reply in headers.
// Runs through the SAME chat pipeline as text messages (session, context, flow).
// ─────────────────────────────────────────────────────────────────────────────
const multer = require('multer');
const _voiceUpload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 25 * 1024 * 1024 } });

router.post('/voice/speak', verifyToken, _voiceUpload.single('audio'), async (req, res) => {
  const userId    = req.user.id;
  const language  = req.body.language || 'en';
  const sessionId = req.body.session_id || null;

  if (!req.file || req.file.size < 500) {
    return res.status(422).json({ error: 'Audio too short — please speak for at least 1 second.' });
  }

  try {
    // ── Step 1: STT — send audio to voice agent STT endpoint ─────────────
    // Use native FormData (Node 18+) — the npm form-data package is incompatible
    // with Node's native fetch.
    const sttForm = new FormData()
    sttForm.append('audio', new Blob([req.file.buffer], { type: req.file.mimetype || 'audio/webm' }), req.file.originalname || 'audio.webm')
    sttForm.append('language', language)

    const sttRes = await fetch(`${VOICE_URL}/api/voice/stt`, {
      method: 'POST',
      body: sttForm,
      signal: AbortSignal.timeout(30_000),
    });

    if (!sttRes.ok) {
      const err = await sttRes.json().catch(() => ({}));
      return res.status(422).json({ error: err.detail || 'Could not transcribe audio.' });
    }

    const sttData = await sttRes.json();
    const transcript = sttData.transcript?.trim();
    if (!transcript) {
      return res.status(422).json({ error: 'Could not hear speech — please speak clearly and try again.' });
    }

    console.log(`[voice] Transcript (${language}): ${transcript}`);

    // ── Step 2: Chat — run transcript through full chat pipeline ──────────
    // Use the same logic as the main POST / route to ensure session context,
    // flow state, and profile are all properly applied.
    let reply = '';
    let activeSid = sessionId;

    // Auto-create session if none provided
    if (!activeSid) {
      const { data: newSession, error: sessErr } = await supabase
        .from('chat_sessions')
        .insert({ user_id: userId, title: transcript.slice(0, 40) })
        .select('id')
        .single();
      if (sessErr || !newSession) {
        return res.status(500).json({ error: 'Could not create chat session.' });
      }
      activeSid = newSession.id;
    }

    // Load history + profile + agent memory in parallel
    const [{ history, key: cacheKey }, profile, agentMemory] = await Promise.all([
      loadHistory(userId, activeSid),
      loadProfile(userId),
      loadAgentMemory(userId),
    ]);

    const longTermMemory = _shouldSearchMemory(transcript)
      ? await searchLongTermMemory(userId, transcript, activeSid)
      : [];
    const userContext = buildUserContext(profile, history, longTermMemory);

    // Call RAG ask endpoint (non-streaming for voice — simpler)
    const ragPayload = {
      question:      transcript,
      session_id:    activeSid,
      user_id:       userId,
      user_context:  userContext,
      account_email: req.user.email || '',
      language:      language,
    };

    const ragRes = await fetch(`${RAG_URL}/api/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(ragPayload),
      signal: AbortSignal.timeout(60_000),
    });

    if (!ragRes.ok) {
      return res.status(502).json({ error: 'AI service error.' });
    }

    const ragData = await ragRes.json();
    reply = ragData.answer || '';

    // Persist the exchange
    agentMemory.history.push({ role: 'user',      content: transcript, ts: new Date().toISOString() });
    agentMemory.history.push({ role: 'assistant', content: reply,      ts: new Date().toISOString() });
    saveAgentHistory(userId, agentMemory.history).catch(() => {});
    await appendHistory(cacheKey, history, userId, activeSid, transcript, reply);
    const isFirst = history.length === 2;
    const title   = transcript.length > 40 ? transcript.slice(0, 40) + '…' : transcript;
    await supabase.from('chat_sessions')
      .update({ ...(isFirst && { title }), updated_at: new Date().toISOString() })
      .eq('id', activeSid).eq('user_id', userId);

    console.log(`[voice] Reply: ${reply.slice(0, 80)}...`);

    // ── Step 3: TTS — synthesise reply to speech ──────────────────────────
    const ttsForm = new FormData()
    ttsForm.append('text', reply)
    ttsForm.append('language', language)

    const ttsRes = await fetch(`${VOICE_URL}/api/voice/tts`, {
      method: 'POST',
      body: ttsForm,
      signal: AbortSignal.timeout(30_000),
    });

    if (!ttsRes.ok) {
      // TTS failed — return JSON fallback so user still sees the text reply
      return res.json({ transcript, reply, audio_available: false, session_id: activeSid });
    }

    const audioBuffer = Buffer.from(await ttsRes.arrayBuffer());

    const { encodeURIComponent: enc } = require('url');
    res.setHeader('Content-Type', 'audio/wav');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('X-Transcript', encodeURIComponent(transcript));
    res.setHeader('X-Reply',      encodeURIComponent(reply));
    res.setHeader('X-Session-Id', activeSid);
    return res.send(audioBuffer);

  } catch (err) {
    const reason = err.name === 'TimeoutError' ? 'Voice request timed out.' : `Voice processing failed: ${err.message}`;
    console.error('[voice] ERROR:', err.name, err.message, err.stack?.split('\n')[1]);
    return res.status(500).json({ error: reason });
  }
});

// ── TTS proxy — allows frontend to call /api/chat/voice/tts with auth ────────
router.post('/voice/tts', verifyToken, _voiceUpload.none(), async (req, res) => {
  const { text, language = 'en' } = req.body;
  if (!text?.trim()) return res.status(400).json({ error: 'Text is required.' });

  try {
    const ttsForm = new FormData()
    ttsForm.append('text', text)
    ttsForm.append('language', language)

    const ttsRes = await fetch(`${VOICE_URL}/api/voice/tts`, {
      method: 'POST',
      body: ttsForm,
      signal: AbortSignal.timeout(30_000),
    });

    if (!ttsRes.ok) return res.status(503).json({ error: 'TTS service unavailable.' });

    const audioBuffer = Buffer.from(await ttsRes.arrayBuffer());
    res.setHeader('Content-Type', 'audio/wav');
    res.setHeader('Cache-Control', 'no-cache');
    return res.send(audioBuffer);
  } catch (err) {
    return res.status(500).json({ error: 'TTS failed.' });
  }
});

module.exports = router;
