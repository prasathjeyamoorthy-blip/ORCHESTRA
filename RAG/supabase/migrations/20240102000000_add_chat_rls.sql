-- Migration: add_chat_rls
-- Ensures chat_sessions, conversations, and user_profiles are
-- fully isolated per user at the database level via Row Level Security.
-- The backend uses the service key (bypasses RLS for server-side ops),
-- but RLS prevents any direct/client-side cross-user data leakage.

-- ── chat_sessions ─────────────────────────────────────────────────────────────
create table if not exists chat_sessions (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users(id) on delete cascade,
  title      text not null default 'New Chat',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table chat_sessions enable row level security;

drop policy if exists "Own sessions only" on chat_sessions;
create policy "Own sessions only"
  on chat_sessions for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create index if not exists chat_sessions_user_id_idx
  on chat_sessions (user_id, updated_at desc);

-- ── conversations ─────────────────────────────────────────────────────────────
create table if not exists conversations (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users(id) on delete cascade,
  session_id uuid,
  role       text not null check (role in ('user', 'assistant')),
  content    text not null,
  created_at timestamptz default now()
);

-- Add session_id column if it doesn't exist yet (for pre-existing tables)
alter table conversations
  add column if not exists session_id uuid references chat_sessions(id) on delete cascade;

alter table conversations enable row level security;

drop policy if exists "Own conversations only" on conversations;
create policy "Own conversations only"
  on conversations for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create index if not exists conversations_user_id_idx
  on conversations (user_id, created_at asc);

create index if not exists conversations_session_idx
  on conversations (session_id, created_at asc);

-- ── user_profiles ─────────────────────────────────────────────────────────────
create table if not exists user_profiles (
  user_id    uuid primary key references auth.users(id) on delete cascade,
  facts      jsonb not null default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table user_profiles enable row level security;

drop policy if exists "Own profile only" on user_profiles;
create policy "Own profile only"
  on user_profiles for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
