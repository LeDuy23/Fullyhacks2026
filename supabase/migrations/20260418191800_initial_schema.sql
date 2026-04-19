-- Core schema for Fullyhacks2026 (Person 1: persistence + posts pipeline)
-- Matches project.md: users, posts, extractions, places, trips (+ trip edits)

-- ---------------------------------------------------------------------------
-- Users (MVP: standalone rows; optional link to Supabase Auth later)
-- ---------------------------------------------------------------------------
create table public.users (
  id uuid primary key default gen_random_uuid(),
  email text unique,
  display_name text,
  auth_user_id uuid unique references auth.users (id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.users is 'App users; auth_user_id set when linked to Supabase Auth.';

-- ---------------------------------------------------------------------------
-- Posts (ingested links + normalized blob)
-- ---------------------------------------------------------------------------
create table public.posts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users (id) on delete cascade,
  url text not null,
  platform text not null default 'unknown',
  raw_text text,
  metadata_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint posts_platform_check check (
    platform in ('tiktok', 'instagram', 'unknown')
  ),
  constraint posts_user_url_unique unique (user_id, url)
);

comment on table public.posts is 'Imported social posts; metadata_json holds caption, transcript, thumbnail_url, creator, etc.';
create index posts_user_id_idx on public.posts (user_id);
create index posts_created_at_idx on public.posts (created_at desc);

-- ---------------------------------------------------------------------------
-- Extractions (AI output per post; Person 2 populates)
-- ---------------------------------------------------------------------------
create table public.extractions (
  id uuid primary key default gen_random_uuid(),
  post_id uuid not null references public.posts (id) on delete cascade,
  places jsonb not null default '[]'::jsonb,
  vibes jsonb not null default '[]'::jsonb,
  destination_candidates jsonb not null default '[]'::jsonb,
  activities jsonb not null default '[]'::jsonb,
  confidence numeric(4, 3),
  model_version text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint extractions_post_id_unique unique (post_id)
);

comment on table public.extractions is 'Structured travel signals from /extract; one row per post.';
create index extractions_post_id_idx on public.extractions (post_id);

-- ---------------------------------------------------------------------------
-- Places (resolved POIs after maps integration; optional until geocoded)
-- ---------------------------------------------------------------------------
create table public.places (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users (id) on delete cascade,
  normalized_name text not null,
  lat double precision,
  lng double precision,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.places is 'Geocoded / resolved places; metadata for address, hours, ratings, source_posts, etc.';
create index places_user_id_idx on public.places (user_id);

-- ---------------------------------------------------------------------------
-- Trips
-- ---------------------------------------------------------------------------
create table public.trips (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users (id) on delete cascade,
  destination text,
  constraints_json jsonb not null default '{}'::jsonb,
  itinerary_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.trips is 'Trip constraints + generated itinerary (Person 2 / planner).';
create index trips_user_id_idx on public.trips (user_id);

-- ---------------------------------------------------------------------------
-- Trip edits (natural-language revisions history)
-- ---------------------------------------------------------------------------
create table public.trip_edits (
  id uuid primary key default gen_random_uuid(),
  trip_id uuid not null references public.trips (id) on delete cascade,
  user_prompt text not null,
  previous_itinerary_json jsonb,
  new_itinerary_json jsonb,
  created_at timestamptz not null default now()
);

comment on table public.trip_edits is 'Audit trail for /revise-trip style edits.';
create index trip_edits_trip_id_idx on public.trip_edits (trip_id);

-- ---------------------------------------------------------------------------
-- Optional: keep updated_at in sync (requires extensions schema)
-- ---------------------------------------------------------------------------
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger users_set_updated_at
  before update on public.users
  for each row execute function public.set_updated_at();

create trigger posts_set_updated_at
  before update on public.posts
  for each row execute function public.set_updated_at();

create trigger extractions_set_updated_at
  before update on public.extractions
  for each row execute function public.set_updated_at();

create trigger places_set_updated_at
  before update on public.places
  for each row execute function public.set_updated_at();

create trigger trips_set_updated_at
  before update on public.trips
  for each row execute function public.set_updated_at();
