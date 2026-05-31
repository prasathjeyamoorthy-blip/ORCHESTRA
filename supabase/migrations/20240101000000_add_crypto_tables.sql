-- Migration: add_crypto_tables
-- Adds zero-knowledge encryption support tables and storage RLS policies

-- ── user_crypto_meta ──────────────────────────────────────────────────────────
-- Stores only opaque base64 blobs — the server never sees the MEK or KEK.
-- salt       : 16 random bytes (base64) — non-secret, used for PBKDF2
-- wrapped_mek: base64 of [12-byte wrap IV][AES-GCM wrapped MEK]

create table if not exists user_crypto_meta (
  user_id    uuid primary key references auth.users(id) on delete cascade,
  salt       text not null,
  wrapped_mek text not null,  -- base64 of [12-byte wrap IV + AES-GCM wrapped MEK]
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table user_crypto_meta enable row level security;

create policy "Own crypto meta only"
  on user_crypto_meta for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- ── document_meta ─────────────────────────────────────────────────────────────
-- Stores file metadata only — no file content, no encryption keys.

create table if not exists document_meta (
  id                 uuid primary key default gen_random_uuid(),
  user_id            uuid references auth.users(id) on delete cascade,
  storage_path       text not null,
  original_filename  text not null,
  original_mime_type text not null,
  file_size_bytes    bigint,
  created_at         timestamptz default now()
);

alter table document_meta enable row level security;

create policy "Own documents only"
  on document_meta for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- ── Storage bucket RLS ────────────────────────────────────────────────────────
-- Bucket must be created as PRIVATE in the Supabase dashboard first.
-- Users can only access their own {user_id}/ folder.

create policy "Users upload to own folder"
  on storage.objects for insert
  with check (auth.uid()::text = (storage.foldername(name))[1]);

create policy "Users read own folder"
  on storage.objects for select
  using (auth.uid()::text = (storage.foldername(name))[1]);

create policy "Users delete own folder"
  on storage.objects for delete
  using (auth.uid()::text = (storage.foldername(name))[1]);
