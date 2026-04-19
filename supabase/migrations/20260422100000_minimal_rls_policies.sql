-- Minimal RLS policy set for core app tables.
-- Keeps security intent explicit without remote-schema noise.

-- Enable RLS on user-owned core tables.
alter table public.users enable row level security;
alter table public.posts enable row level security;
alter table public.extractions enable row level security;
alter table public.places enable row level security;
alter table public.trips enable row level security;
alter table public.trip_edits enable row level security;

-- users: each auth user can manage their own profile row.
drop policy if exists "Users can manage their own profile" on public.users;
create policy "Users can manage their own profile"
  on public.users
  as permissive
  for all
  to authenticated
  using (auth.uid() = auth_user_id)
  with check (auth.uid() = auth_user_id);

-- posts: user owns rows directly by user_id.
drop policy if exists "Users can manage their own posts" on public.posts;
create policy "Users can manage their own posts"
  on public.posts
  as permissive
  for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- extractions: inferred ownership via linked post ownership.
drop policy if exists "Users can manage extractions for their posts" on public.extractions;
create policy "Users can manage extractions for their posts"
  on public.extractions
  as permissive
  for all
  to authenticated
  using (
    exists (
      select 1
      from public.posts p
      where p.id = extractions.post_id
        and p.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1
      from public.posts p
      where p.id = extractions.post_id
        and p.user_id = auth.uid()
    )
  );

-- places: user owns rows directly by user_id.
drop policy if exists "Users can manage their own places" on public.places;
create policy "Users can manage their own places"
  on public.places
  as permissive
  for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- trips: user owns rows directly by user_id.
drop policy if exists "Users can manage their own trips" on public.trips;
create policy "Users can manage their own trips"
  on public.trips
  as permissive
  for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- trip_edits: ownership inferred via parent trip ownership.
drop policy if exists "Users can manage edits for their trips" on public.trip_edits;
create policy "Users can manage edits for their trips"
  on public.trip_edits
  as permissive
  for all
  to authenticated
  using (
    exists (
      select 1
      from public.trips t
      where t.id = trip_edits.trip_id
        and t.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1
      from public.trips t
      where t.id = trip_edits.trip_id
        and t.user_id = auth.uid()
    )
  );
