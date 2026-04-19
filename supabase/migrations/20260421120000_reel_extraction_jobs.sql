-- Async reel-to-map extraction jobs (see app/routes/reel_jobs.py)
create table if not exists public.reel_extraction_jobs (
  id uuid primary key default gen_random_uuid(),
  source_url text not null,
  status text not null default 'queued',
  result jsonb,
  error text,
  created_at timestamptz not null default now(),
  completed_at timestamptz,
  constraint reel_extraction_jobs_status_check check (
    status in ('queued', 'processing', 'done', 'failed')
  )
);

create index if not exists reel_extraction_jobs_created_at_idx
  on public.reel_extraction_jobs (created_at desc);

comment on table public.reel_extraction_jobs is
  'POST /api/jobs — async TikTok/Instagram/Maps URL extraction; client polls GET /api/jobs/:id';
