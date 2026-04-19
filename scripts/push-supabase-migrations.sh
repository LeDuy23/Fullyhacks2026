#!/usr/bin/env bash
# Push local supabase/migrations/*.sql to your hosted project on supabase.com
#
# Prerequisites (one-time):
#   1. supabase login          # browser auth, or set SUPABASE_ACCESS_TOKEN
#   2. Set PROJECT_REF below to your project ref (from Project URL: https://<ref>.supabase.co)

set -euo pipefail
cd "$(dirname "$0")/.."

export PATH="${HOME}/.local/bin:${PATH}"

PROJECT_REF="${SUPABASE_PROJECT_REF:-nqjcfrjxuexnuqbzubmw}"

if ! command -v supabase >/dev/null 2>&1; then
  echo "Install Supabase CLI: https://supabase.com/docs/guides/cli"
  exit 1
fi

echo "Linking project ref: ${PROJECT_REF}"
supabase link --project-ref "${PROJECT_REF}" --yes

echo "Pushing migrations..."
supabase db push --yes

echo "Done."
