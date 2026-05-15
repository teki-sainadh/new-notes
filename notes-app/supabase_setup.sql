-- ============================================================
-- Notes App - Supabase SQL Setup
-- Run this entire file in your Supabase SQL Editor
-- ============================================================

-- 1. USERS TABLE
create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  password_hash text not null,
  created_at timestamptz default now()
);

-- 2. NOTES TABLE
create table if not exists notes (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references users(id) on delete cascade,
  title text not null,
  content text not null,
  is_pinned boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- 3. SHARED NOTES TABLE
create table if not exists shared_notes (
  id uuid primary key default gen_random_uuid(),
  note_id uuid not null references notes(id) on delete cascade,
  shared_with_user_id uuid not null references users(id) on delete cascade,
  shared_at timestamptz default now(),
  unique(note_id, shared_with_user_id)
);

-- ============================================================
-- IMPORTANT: Disable Row Level Security on all 3 tables
-- (Our app handles auth via JWT — RLS would block our queries)
-- ============================================================
alter table users disable row level security;
alter table notes disable row level security;
alter table shared_notes disable row level security;

-- ============================================================
-- Indexes for faster queries
-- ============================================================
create index if not exists idx_notes_owner on notes(owner_id);
create index if not exists idx_shared_note_id on shared_notes(note_id);
create index if not exists idx_shared_user_id on shared_notes(shared_with_user_id);
create index if not exists idx_users_email on users(email);
