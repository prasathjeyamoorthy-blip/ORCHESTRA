-- Migration: add_memory_search
-- Adds full-text search on conversations for long-term semantic memory retrieval.
-- Also adds a user_memory_summaries table for compressed cross-session memory.

-- ── Full-text search index on conversations ───────────────────────────────────
-- tsvector column for fast GIN-indexed search
alter table conversations
  add column if not exists content_tsv tsvector
    generated always as (to_tsvector('english', content)) stored;

create index if not exists conversations_content_tsv_idx
  on conversations using gin(content_tsv);

-- Also index by user_id + role for efficient per-user history queries
create index if not exists conversations_user_role_idx
  on conversations (user_id, role, created_at desc);

-- ── user_memory_summaries ─────────────────────────────────────────────────────
-- Stores compressed summaries of older sessions so the bot can recall
-- what was discussed even when the raw conversation is very old.
-- One row per session — updated when a session ends or gets long.

create table if not exists user_memory_summaries (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  session_id  uuid references chat_sessions(id) on delete cascade,
  summary     text not null,           -- compressed summary of the session
  key_facts   jsonb not null default '{}', -- extracted facts from this session
  topics      text[] not null default '{}', -- topic tags for fast filtering
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);

alter table user_memory_summaries enable row level security;

drop policy if exists "Own summaries only" on user_memory_summaries;
create policy "Own summaries only"
  on user_memory_summaries for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create index if not exists memory_summaries_user_idx
  on user_memory_summaries (user_id, updated_at desc);

-- Full-text search on summaries too
alter table user_memory_summaries
  add column if not exists summary_tsv tsvector
    generated always as (to_tsvector('english', summary)) stored;

create index if not exists memory_summaries_tsv_idx
  on user_memory_summaries using gin(summary_tsv);
