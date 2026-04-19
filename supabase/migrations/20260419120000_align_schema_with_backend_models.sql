-- Upgrade databases that applied the earlier initial_schema (pre-backend alignment).
-- Safe to run on fresh DBs created from the updated 20260418191800 migration (most steps no-op).

-- ---------------------------------------------------------------------------
-- posts: client_post_id, platform enum aligned with NormalizedPost.platform
-- ---------------------------------------------------------------------------
alter table public.posts add column if not exists client_post_id text;

drop index if exists public.posts_user_client_post_id_uidx;
create unique index if not exists posts_user_client_post_id_uidx
  on public.posts (user_id, client_post_id)
  where client_post_id is not null;

alter table public.posts drop constraint if exists posts_platform_check;
update public.posts set platform = 'other' where platform = 'unknown';

alter table public.posts add constraint posts_platform_check
  check (platform in ('tiktok', 'instagram', 'other'));

-- ---------------------------------------------------------------------------
-- extractions: align with app/models/extraction.py ExtractedPost
-- ---------------------------------------------------------------------------
alter table public.extractions add column if not exists is_travel_relevant boolean default false;
alter table public.extractions add column if not exists place_candidates jsonb default '[]'::jsonb;
alter table public.extractions add column if not exists vibe_tags jsonb default '[]'::jsonb;
alter table public.extractions add column if not exists best_time_of_day jsonb default '[]'::jsonb;
alter table public.extractions add column if not exists budget_signal text default 'unknown';
alter table public.extractions add column if not exists pace_signal text default 'unknown';
alter table public.extractions add column if not exists notes text default '';
alter table public.extractions add column if not exists aggregate_confidence numeric(4, 3);

-- Legacy column renames / backfill (old migration used places + vibes)
do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'extractions' and column_name = 'places'
  ) then
    update public.extractions e
    set place_candidates = coalesce(
      (
        select jsonb_agg(obj) filter (where obj is not null)
        from jsonb_array_elements(coalesce(e.places, '[]'::jsonb)) as t(el),
        lateral (
          select case jsonb_typeof(t.el)
            when 'string' then jsonb_build_object(
              'name', coalesce(t.el #>> '{}', ''),
              'type', 'unknown',
              'confidence', 0.5,
              'reason', 'migrated from legacy places[]'
            )
            when 'object' then t.el
            else null
          end as obj
        ) x
      ),
      '[]'::jsonb
    )
    where e.place_candidates is null or e.place_candidates = '[]'::jsonb;

    alter table public.extractions drop column if exists places;
  end if;
end $$;

do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'extractions' and column_name = 'vibes'
  ) then
    execute $q$
      update public.extractions e
      set vibe_tags = coalesce(e.vibes, '[]'::jsonb)
      where e.vibe_tags is null or e.vibe_tags = '[]'::jsonb
    $q$;
  end if;
end $$;

alter table public.extractions drop column if exists vibes;

do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'extractions' and column_name = 'confidence'
  ) then
    execute $q$
      update public.extractions
      set aggregate_confidence = confidence
      where aggregate_confidence is null
    $q$;
  end if;
end $$;

alter table public.extractions drop column if exists confidence;

alter table public.extractions alter column is_travel_relevant set default false;
update public.extractions set is_travel_relevant = coalesce(is_travel_relevant, false);
alter table public.extractions alter column is_travel_relevant set not null;

update public.extractions set place_candidates = '[]'::jsonb where place_candidates is null;
update public.extractions set vibe_tags = '[]'::jsonb where vibe_tags is null;
update public.extractions set best_time_of_day = '[]'::jsonb where best_time_of_day is null;
update public.extractions set budget_signal = 'unknown' where budget_signal is null;
update public.extractions set pace_signal = 'unknown' where pace_signal is null;
update public.extractions set notes = '' where notes is null;

alter table public.extractions alter column place_candidates set default '[]'::jsonb;
alter table public.extractions alter column place_candidates set not null;
alter table public.extractions alter column vibe_tags set default '[]'::jsonb;
alter table public.extractions alter column vibe_tags set not null;
alter table public.extractions alter column best_time_of_day set default '[]'::jsonb;
alter table public.extractions alter column best_time_of_day set not null;
alter table public.extractions alter column budget_signal set not null;
alter table public.extractions alter column pace_signal set not null;
alter table public.extractions alter column notes set not null;

alter table public.extractions drop constraint if exists extractions_budget_signal_check;
alter table public.extractions add constraint extractions_budget_signal_check check (
  budget_signal in ('budget', 'medium', 'luxury', 'unknown')
);

alter table public.extractions drop constraint if exists extractions_pace_signal_check;
alter table public.extractions add constraint extractions_pace_signal_check check (
  pace_signal in ('relaxed', 'moderate', 'packed', 'unknown')
);

create index if not exists extractions_travel_relevant_idx
  on public.extractions (is_travel_relevant);

-- ---------------------------------------------------------------------------
-- places: CandidatePlace-friendly columns
-- ---------------------------------------------------------------------------
alter table public.places add column if not exists place_id text;
alter table public.places add column if not exists category text;
alter table public.places add column if not exists neighborhood text;
alter table public.places add column if not exists opening_hours text;
alter table public.places add column if not exists estimated_visit_minutes integer;
alter table public.places add column if not exists mention_count integer default 0;
alter table public.places add column if not exists avg_confidence double precision;
alter table public.places add column if not exists score double precision;

create index if not exists places_place_id_idx on public.places (place_id) where place_id is not null;

-- ---------------------------------------------------------------------------
-- trips: optional pipeline snapshots (GenerateTripRequest-shaped blobs)
-- ---------------------------------------------------------------------------
alter table public.trips add column if not exists preference_profile_json jsonb;
alter table public.trips add column if not exists candidate_places_json jsonb;
