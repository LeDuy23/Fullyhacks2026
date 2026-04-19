-- Optional demo table for the Next.js starter page (`web/app/page.tsx`).
-- Tighten RLS before production.

create table if not exists public.todos (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now()
);

comment on table public.todos is 'Demo list for Supabase + Next.js scaffold; replace with app tables when ready.';

alter table public.todos enable row level security;

drop policy if exists "todos_select_public" on public.todos;
create policy "todos_select_public"
  on public.todos for select
  using (true);

drop policy if exists "todos_insert_public" on public.todos;
create policy "todos_insert_public"
  on public.todos for insert
  with check (true);

insert into public.todos (name)
select 'Connect Next.js to Supabase'
where not exists (
  select 1 from public.todos t where t.name = 'Connect Next.js to Supabase'
);
