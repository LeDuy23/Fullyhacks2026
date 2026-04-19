-- Idempotent smoke test: insert rows across core tables, verify, delete (FK-safe order).
-- Run: supabase db query -f supabase/scripts/smoke_test_inserts_deletes.sql --linked

do $$
declare
  uid uuid;
  pid uuid;
  tid uuid;
  plid uuid;
  has_todos boolean;
  has_revision_history boolean;
begin
  select exists (
    select 1
    from information_schema.tables
    where table_schema = 'public' and table_name = 'todos'
  ) into has_todos;

  select exists (
    select 1
    from information_schema.tables
    where table_schema = 'public' and table_name = 'revision_history'
  ) into has_revision_history;

  -- Clean leftovers from a previous interrupted run
  delete from public.trip_edits te
  using public.trips t
  where te.trip_id = t.id and t.destination = '__SMOKE_TRIP__';
  delete from public.trips where destination = '__SMOKE_TRIP__';
  delete from public.extractions e
  using public.posts p
  where e.post_id = p.id and p.url = 'https://example.smoke/test-post-unique';
  delete from public.posts where url = 'https://example.smoke/test-post-unique';
  delete from public.places where normalized_name = '__SMOKE_PLACE__';
  delete from public.users where email = 'smoke.user@fullyhacks.invalid';

  insert into public.users (email, display_name)
  values ('smoke.user@fullyhacks.invalid', 'Smoke User')
  returning id into uid;

  insert into public.posts (user_id, url, platform, client_post_id, raw_text, metadata_json)
  values (
    uid,
    'https://example.smoke/test-post-unique',
    'other',
    'smoke-client-1',
    'Smoke test raw_text',
    '{"source": "smoke"}'::jsonb
  )
  returning id into pid;

  insert into public.extractions (
    post_id,
    is_travel_relevant,
    destination_candidates,
    place_candidates,
    activities,
    vibe_tags,
    best_time_of_day,
    budget_signal,
    pace_signal,
    notes
  )
  values (
    pid,
    true,
    '[{"name":"SmokeCity","confidence":0.66}]'::jsonb,
    '[{"name":"Smoke Cafe","type":"cafe","confidence":0.7,"reason":"smoke"}]'::jsonb,
    '["sightseeing"]'::jsonb,
    '["relaxed"]'::jsonb,
    '["morning"]'::jsonb,
    'medium',
    'moderate',
    'smoke test row'
  );

  insert into public.places (user_id, normalized_name, lat, lng, category, mention_count)
  values (uid, '__SMOKE_PLACE__', 35.6812, 139.7671, 'cafe', 1)
  returning id into plid;

  insert into public.trips (user_id, destination, constraints_json, itinerary_json, preference_profile_json)
  values (
    uid,
    '__SMOKE_TRIP__',
    '{"days": 2}'::jsonb,
    '{"summary": "smoke"}'::jsonb,
    '{"top_vibes": []}'::jsonb
  )
  returning id into tid;

  insert into public.trip_edits (trip_id, user_prompt, previous_itinerary_json, new_itinerary_json)
  values (tid, '__SMOKE_EDIT__', '{}'::jsonb, '{"changed": true}'::jsonb);

  -- Optional demo table
  if has_todos then
    insert into public.todos (name) values ('__SMOKE_TODO__');
  else
    raise notice 'SMOKE_INFO: skipped todos checks (table public.todos not found)';
  end if;

  -- Optional audit table maintained by integrator / policy layer
  if has_revision_history then
    raise notice 'SMOKE_INFO: revision_history exists; skipping strict writes in smoke test';
  end if;

  if (select count(*) from public.users where id = uid) <> 1 then
    raise exception 'assert failed: user row';
  end if;
  if (select count(*) from public.posts where id = pid) <> 1 then
    raise exception 'assert failed: post row';
  end if;
  if (select count(*) from public.extractions where post_id = pid) <> 1 then
    raise exception 'assert failed: extraction row';
  end if;
  if (select count(*) from public.places where id = plid) <> 1 then
    raise exception 'assert failed: place row';
  end if;
  if (select count(*) from public.trips where id = tid) <> 1 then
    raise exception 'assert failed: trip row';
  end if;
  if (select count(*) from public.trip_edits where trip_id = tid) <> 1 then
    raise exception 'assert failed: trip_edit row';
  end if;
  if has_todos and (select count(*) from public.todos where name = '__SMOKE_TODO__') <> 1 then
    raise exception 'assert failed: todo row';
  end if;

  raise notice 'SMOKE_OK: all inserts visible before delete';

  if has_todos then
    delete from public.todos where name = '__SMOKE_TODO__';
  end if;
  delete from public.trip_edits where trip_id = tid;
  delete from public.trips where id = tid;
  delete from public.extractions where post_id = pid;
  delete from public.posts where id = pid;
  delete from public.places where id = plid;
  delete from public.users where id = uid;

  if exists (select 1 from public.users where id = uid) then
    raise exception 'assert failed: user still exists after delete';
  end if;

  raise notice 'SMOKE_OK: deletes completed, database round-trip successful';
end $$;
