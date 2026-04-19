-- Core schema aligned with FastAPI backend:
--   app/models/extraction.py (NormalizedPost, ExtractedPost)
--   app/models/schemas.py (TripPlan, TripConstraints, CandidatePlace, …)
-- project.md: users, posts, extractions, places, trips, trip_edits

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
-- Posts — matches NormalizedPost + persistence (caption etc. in metadata_json)
-- ---------------------------------------------------------------------------
create table public.posts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users (id) on delete cascade,
  url text not null,
  platform text not null default 'other',
  client_post_id text,
  raw_text text,
  metadata_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint posts_platform_check check (
    platform in ('tiktok', 'instagram', 'other')
  ),
  constraint posts_user_url_unique unique (user_id, url)
);

comment on table public.posts is 'Imported social posts. metadata_json: caption, transcript, ocr_text, thumbnail_text, etc. client_post_id = API NormalizedPost.post_id.';
create index posts_user_id_idx on public.posts (user_id);
create index posts_created_at_idx on public.posts (created_at desc);
create unique index posts_user_client_post_id_uidx
  on public.posts (user_id, client_post_id)
  where client_post_id is not null;

-- ---------------------------------------------------------------------------
-- Extractions — one row per post; matches ExtractedPost (app/models/extraction.py)
-- ---------------------------------------------------------------------------
create table public.extractions (
  id uuid primary key default gen_random_uuid(),
  post_id uuid not null references public.posts (id) on delete cascade,
  is_travel_relevant boolean not null default false,
  destination_candidates jsonb not null default '[]'::jsonb,
  place_candidates jsonb not null default '[]'::jsonb,
  activities jsonb not null default '[]'::jsonb,
  vibe_tags jsonb not null default '[]'::jsonb,
  best_time_of_day jsonb not null default '[]'::jsonb,
  budget_signal text not null default 'unknown',
  pace_signal text not null default 'unknown',
  notes text not null default '',
  aggregate_confidence numeric(4, 3),
  model_version text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint extractions_post_id_unique unique (post_id),
  constraint extractions_budget_signal_check check (
    budget_signal in ('budget', 'medium', 'luxury', 'unknown')
  ),
  constraint extractions_pace_signal_check check (
    pace_signal in ('relaxed', 'moderate', 'packed', 'unknown')
  )
);

comment on table public.extractions is 'Output of POST /extract; JSON arrays mirror Pydantic list fields on ExtractedPost.';
create index extractions_post_id_idx on public.extractions (post_id);
create index extractions_travel_relevant_idx on public.extractions (is_travel_relevant);

-- ---------------------------------------------------------------------------
-- Places — resolved POIs (CandidatePlace–shaped data can live in metadata jsonb)
-- ---------------------------------------------------------------------------
create table public.places (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users (id) on delete cascade,
  normalized_name text not null,
  place_id text,
  category text,
  neighborhood text,
  lat double precision,
  lng double precision,
  opening_hours text,
  estimated_visit_minutes integer,
  mention_count integer default 0,
  avg_confidence double precision,
  score double precision,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.places is 'Geocoded POIs; aligns with CandidatePlace + extra metadata.';
create index places_user_id_idx on public.places (user_id);
create index places_place_id_idx on public.places (place_id) where place_id is not null;

-- ---------------------------------------------------------------------------
-- Trips — TripConstraints in constraints_json, TripPlan in itinerary_json
-- ---------------------------------------------------------------------------
create table public.trips (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users (id) on delete cascade,
  destination text,
  preference_profile_json jsonb,
  candidate_places_json jsonb,
  constraints_json jsonb not null default '{}'::jsonb,
  itinerary_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.trips is 'TripConstraints → constraints_json; TripPlan → itinerary_json; optional snapshots from pipeline.';
create index trips_user_id_idx on public.trips (user_id);

-- ---------------------------------------------------------------------------
-- Trip edits — /revise-trip audit trail
-- ---------------------------------------------------------------------------
create table public.trip_edits (
  id uuid primary key default gen_random_uuid(),
  trip_id uuid not null references public.trips (id) on delete cascade,
  user_prompt text not null,
  previous_itinerary_json jsonb,
  new_itinerary_json jsonb,
  created_at timestamptz not null default now()
);

comment on table public.trip_edits is 'Audit trail for revise-trip.';
create index trip_edits_trip_id_idx on public.trip_edits (trip_id);

-- ---------------------------------------------------------------------------
-- updated_at triggers
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
