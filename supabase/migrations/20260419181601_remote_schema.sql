drop extension if exists "pg_net";

revoke delete on table "public"."extractions" from "anon";

revoke insert on table "public"."extractions" from "anon";

revoke references on table "public"."extractions" from "anon";

revoke select on table "public"."extractions" from "anon";

revoke trigger on table "public"."extractions" from "anon";

revoke truncate on table "public"."extractions" from "anon";

revoke update on table "public"."extractions" from "anon";

revoke delete on table "public"."extractions" from "authenticated";

revoke insert on table "public"."extractions" from "authenticated";

revoke references on table "public"."extractions" from "authenticated";

revoke select on table "public"."extractions" from "authenticated";

revoke trigger on table "public"."extractions" from "authenticated";

revoke truncate on table "public"."extractions" from "authenticated";

revoke update on table "public"."extractions" from "authenticated";

revoke delete on table "public"."extractions" from "service_role";

revoke insert on table "public"."extractions" from "service_role";

revoke references on table "public"."extractions" from "service_role";

revoke select on table "public"."extractions" from "service_role";

revoke trigger on table "public"."extractions" from "service_role";

revoke truncate on table "public"."extractions" from "service_role";

revoke update on table "public"."extractions" from "service_role";

revoke delete on table "public"."places" from "anon";

revoke insert on table "public"."places" from "anon";

revoke references on table "public"."places" from "anon";

revoke select on table "public"."places" from "anon";

revoke trigger on table "public"."places" from "anon";

revoke truncate on table "public"."places" from "anon";

revoke update on table "public"."places" from "anon";

revoke delete on table "public"."places" from "authenticated";

revoke insert on table "public"."places" from "authenticated";

revoke references on table "public"."places" from "authenticated";

revoke select on table "public"."places" from "authenticated";

revoke trigger on table "public"."places" from "authenticated";

revoke truncate on table "public"."places" from "authenticated";

revoke update on table "public"."places" from "authenticated";

revoke delete on table "public"."places" from "service_role";

revoke insert on table "public"."places" from "service_role";

revoke references on table "public"."places" from "service_role";

revoke select on table "public"."places" from "service_role";

revoke trigger on table "public"."places" from "service_role";

revoke truncate on table "public"."places" from "service_role";

revoke update on table "public"."places" from "service_role";

revoke delete on table "public"."posts" from "anon";

revoke insert on table "public"."posts" from "anon";

revoke references on table "public"."posts" from "anon";

revoke select on table "public"."posts" from "anon";

revoke trigger on table "public"."posts" from "anon";

revoke truncate on table "public"."posts" from "anon";

revoke update on table "public"."posts" from "anon";

revoke delete on table "public"."posts" from "authenticated";

revoke insert on table "public"."posts" from "authenticated";

revoke references on table "public"."posts" from "authenticated";

revoke select on table "public"."posts" from "authenticated";

revoke trigger on table "public"."posts" from "authenticated";

revoke truncate on table "public"."posts" from "authenticated";

revoke update on table "public"."posts" from "authenticated";

revoke delete on table "public"."posts" from "service_role";

revoke insert on table "public"."posts" from "service_role";

revoke references on table "public"."posts" from "service_role";

revoke select on table "public"."posts" from "service_role";

revoke trigger on table "public"."posts" from "service_role";

revoke truncate on table "public"."posts" from "service_role";

revoke update on table "public"."posts" from "service_role";

revoke delete on table "public"."reel_extraction_jobs" from "anon";

revoke insert on table "public"."reel_extraction_jobs" from "anon";

revoke references on table "public"."reel_extraction_jobs" from "anon";

revoke select on table "public"."reel_extraction_jobs" from "anon";

revoke trigger on table "public"."reel_extraction_jobs" from "anon";

revoke truncate on table "public"."reel_extraction_jobs" from "anon";

revoke update on table "public"."reel_extraction_jobs" from "anon";

revoke delete on table "public"."reel_extraction_jobs" from "authenticated";

revoke insert on table "public"."reel_extraction_jobs" from "authenticated";

revoke references on table "public"."reel_extraction_jobs" from "authenticated";

revoke select on table "public"."reel_extraction_jobs" from "authenticated";

revoke trigger on table "public"."reel_extraction_jobs" from "authenticated";

revoke truncate on table "public"."reel_extraction_jobs" from "authenticated";

revoke update on table "public"."reel_extraction_jobs" from "authenticated";

revoke delete on table "public"."reel_extraction_jobs" from "service_role";

revoke insert on table "public"."reel_extraction_jobs" from "service_role";

revoke references on table "public"."reel_extraction_jobs" from "service_role";

revoke select on table "public"."reel_extraction_jobs" from "service_role";

revoke trigger on table "public"."reel_extraction_jobs" from "service_role";

revoke truncate on table "public"."reel_extraction_jobs" from "service_role";

revoke update on table "public"."reel_extraction_jobs" from "service_role";

revoke delete on table "public"."todos" from "anon";

revoke insert on table "public"."todos" from "anon";

revoke references on table "public"."todos" from "anon";

revoke select on table "public"."todos" from "anon";

revoke trigger on table "public"."todos" from "anon";

revoke truncate on table "public"."todos" from "anon";

revoke update on table "public"."todos" from "anon";

revoke delete on table "public"."todos" from "authenticated";

revoke insert on table "public"."todos" from "authenticated";

revoke references on table "public"."todos" from "authenticated";

revoke select on table "public"."todos" from "authenticated";

revoke trigger on table "public"."todos" from "authenticated";

revoke truncate on table "public"."todos" from "authenticated";

revoke update on table "public"."todos" from "authenticated";

revoke delete on table "public"."todos" from "service_role";

revoke insert on table "public"."todos" from "service_role";

revoke references on table "public"."todos" from "service_role";

revoke select on table "public"."todos" from "service_role";

revoke trigger on table "public"."todos" from "service_role";

revoke truncate on table "public"."todos" from "service_role";

revoke update on table "public"."todos" from "service_role";

revoke delete on table "public"."trip_edits" from "anon";

revoke insert on table "public"."trip_edits" from "anon";

revoke references on table "public"."trip_edits" from "anon";

revoke select on table "public"."trip_edits" from "anon";

revoke trigger on table "public"."trip_edits" from "anon";

revoke truncate on table "public"."trip_edits" from "anon";

revoke update on table "public"."trip_edits" from "anon";

revoke delete on table "public"."trip_edits" from "authenticated";

revoke insert on table "public"."trip_edits" from "authenticated";

revoke references on table "public"."trip_edits" from "authenticated";

revoke select on table "public"."trip_edits" from "authenticated";

revoke trigger on table "public"."trip_edits" from "authenticated";

revoke truncate on table "public"."trip_edits" from "authenticated";

revoke update on table "public"."trip_edits" from "authenticated";

revoke delete on table "public"."trip_edits" from "service_role";

revoke insert on table "public"."trip_edits" from "service_role";

revoke references on table "public"."trip_edits" from "service_role";

revoke select on table "public"."trip_edits" from "service_role";

revoke trigger on table "public"."trip_edits" from "service_role";

revoke truncate on table "public"."trip_edits" from "service_role";

revoke update on table "public"."trip_edits" from "service_role";

revoke delete on table "public"."trips" from "anon";

revoke insert on table "public"."trips" from "anon";

revoke references on table "public"."trips" from "anon";

revoke select on table "public"."trips" from "anon";

revoke trigger on table "public"."trips" from "anon";

revoke truncate on table "public"."trips" from "anon";

revoke update on table "public"."trips" from "anon";

revoke delete on table "public"."trips" from "authenticated";

revoke insert on table "public"."trips" from "authenticated";

revoke references on table "public"."trips" from "authenticated";

revoke select on table "public"."trips" from "authenticated";

revoke trigger on table "public"."trips" from "authenticated";

revoke truncate on table "public"."trips" from "authenticated";

revoke update on table "public"."trips" from "authenticated";

revoke delete on table "public"."trips" from "service_role";

revoke insert on table "public"."trips" from "service_role";

revoke references on table "public"."trips" from "service_role";

revoke select on table "public"."trips" from "service_role";

revoke trigger on table "public"."trips" from "service_role";

revoke truncate on table "public"."trips" from "service_role";

revoke update on table "public"."trips" from "service_role";

revoke delete on table "public"."users" from "anon";

revoke insert on table "public"."users" from "anon";

revoke references on table "public"."users" from "anon";

revoke select on table "public"."users" from "anon";

revoke trigger on table "public"."users" from "anon";

revoke truncate on table "public"."users" from "anon";

revoke update on table "public"."users" from "anon";

revoke delete on table "public"."users" from "authenticated";

revoke insert on table "public"."users" from "authenticated";

revoke references on table "public"."users" from "authenticated";

revoke select on table "public"."users" from "authenticated";

revoke trigger on table "public"."users" from "authenticated";

revoke truncate on table "public"."users" from "authenticated";

revoke update on table "public"."users" from "authenticated";

revoke delete on table "public"."users" from "service_role";

revoke insert on table "public"."users" from "service_role";

revoke references on table "public"."users" from "service_role";

revoke select on table "public"."users" from "service_role";

revoke trigger on table "public"."users" from "service_role";

revoke truncate on table "public"."users" from "service_role";

revoke update on table "public"."users" from "service_role";

alter table "public"."reel_extraction_jobs" drop constraint "reel_extraction_jobs_status_check";

alter table "public"."reel_extraction_jobs" drop constraint "reel_extraction_jobs_pkey";

drop index if exists "public"."reel_extraction_jobs_created_at_idx";

drop index if exists "public"."reel_extraction_jobs_pkey";

drop table "public"."reel_extraction_jobs";


  create table "public"."revision_history" (
    "id" uuid not null default gen_random_uuid(),
    "table_name" text,
    "record_id" uuid,
    "old_data" jsonb,
    "new_data" jsonb,
    "changed_by" uuid,
    "changed_at" timestamp with time zone default now()
      );


alter table "public"."revision_history" enable row level security;

alter table "public"."extractions" enable row level security;

alter table "public"."places" enable row level security;

alter table "public"."posts" enable row level security;

alter table "public"."trip_edits" enable row level security;

alter table "public"."trips" enable row level security;

alter table "public"."users" enable row level security;

CREATE UNIQUE INDEX revision_history_pkey ON public.revision_history USING btree (id);

alter table "public"."revision_history" add constraint "revision_history_pkey" PRIMARY KEY using index "revision_history_pkey";

alter table "public"."revision_history" add constraint "revision_history_changed_by_fkey" FOREIGN KEY (changed_by) REFERENCES auth.users(id) not valid;

alter table "public"."revision_history" validate constraint "revision_history_changed_by_fkey";

set check_function_bodies = off;

CREATE OR REPLACE FUNCTION public.rls_auto_enable()
 RETURNS event_trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog'
AS $function$
DECLARE
  cmd record;
BEGIN
  FOR cmd IN
    SELECT *
    FROM pg_event_trigger_ddl_commands()
    WHERE command_tag IN ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
      AND object_type IN ('table','partitioned table')
  LOOP
     IF cmd.schema_name IS NOT NULL AND cmd.schema_name IN ('public') AND cmd.schema_name NOT IN ('pg_catalog','information_schema') AND cmd.schema_name NOT LIKE 'pg_toast%' AND cmd.schema_name NOT LIKE 'pg_temp%' THEN
      BEGIN
        EXECUTE format('alter table if exists %s enable row level security', cmd.object_identity);
        RAISE LOG 'rls_auto_enable: enabled RLS on %', cmd.object_identity;
      EXCEPTION
        WHEN OTHERS THEN
          RAISE LOG 'rls_auto_enable: failed to enable RLS on %', cmd.object_identity;
      END;
     ELSE
        RAISE LOG 'rls_auto_enable: skip % (either system schema or not in enforced list: %.)', cmd.object_identity, cmd.schema_name;
     END IF;
  END LOOP;
END;
$function$
;


  create policy "Users can manage extractions for their posts"
  on "public"."extractions"
  as permissive
  for all
  to authenticated
using ((EXISTS ( SELECT 1
   FROM public.posts
  WHERE ((posts.id = extractions.post_id) AND (posts.user_id = auth.uid())))))
with check ((EXISTS ( SELECT 1
   FROM public.posts
  WHERE ((posts.id = extractions.post_id) AND (posts.user_id = auth.uid())))));



  create policy "Users can manage their own posts"
  on "public"."posts"
  as permissive
  for all
  to authenticated
using ((auth.uid() = user_id))
with check ((auth.uid() = user_id));



  create policy "Users can manage their own revision history"
  on "public"."revision_history"
  as permissive
  for all
  to authenticated
using ((auth.uid() = changed_by))
with check ((auth.uid() = changed_by));



  create policy "Users can manage their own trips"
  on "public"."trips"
  as permissive
  for all
  to authenticated
using ((auth.uid() = user_id))
with check ((auth.uid() = user_id));



