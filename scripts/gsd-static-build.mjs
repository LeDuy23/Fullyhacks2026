#!/usr/bin/env node
/**
 * Production-ish static output for DeepDive, gated on the GSD SDK being present.
 * The published @gsd-build/sdk CLI exposes `gsd-sdk` (run / auto / init); workflows
 * in get-shit-done may expect a global install for `gsd-sdk query …`.
 */
import { mkdirSync, copyFileSync, existsSync, writeFileSync } from 'node:fs';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = dirname(fileURLToPath(import.meta.url));
const projectRoot = join(root, '..');

execSync('npm exec gsd-sdk -- --version', { stdio: 'inherit', cwd: projectRoot });

const dist = join(projectRoot, 'dist');
mkdirSync(dist, { recursive: true });
copyFileSync(join(projectRoot, 'DeepDive.html'), join(dist, 'index.html'));
if (existsSync(join(projectRoot, 'config.example.js'))) {
  copyFileSync(join(projectRoot, 'config.example.js'), join(dist, 'config.example.js'));
  writeFileSync(
    join(dist, 'config.js'),
    "window.GOOGLE_MAPS_API_KEY = '';\n",
    'utf8'
  );
}
console.log('\n✓ GSD SDK OK. Static output → dist/ (DeepDive as index.html)\n');
