// @ts-check
import { test, expect } from '@playwright/test';

const tripFixture = {
  destination: 'Test Atoll',
  summary: 'Mock plan for E2E.',
  days: [
    {
      day: 1,
      area: 'North',
      theme: 'Reefs',
      items: [
        {
          time: '09:00',
          place_id: 'p1',
          name: 'Coral Point',
          activity_type: 'dive',
          duration_minutes: 60,
          why_included: 'fixture',
        },
      ],
      backup_options: [],
    },
  ],
  planning_notes: [],
};

async function goToApp(page) {
  await page.goto('/DeepDive.html');
  await page.evaluate(() => {
    localStorage.clear();
  });
  await page.reload();
  await page.getByTestId('splash-get-started').click();
  await expect(page.getByTestId('onboard-age-continue')).toBeVisible();
  await page.getByRole('button', { name: '18–24' }).click();
  await page.getByTestId('onboard-age-continue').click();
  await page.getByRole('button', { name: /expedition/i }).click();
  await page.getByTestId('onboard-trip-continue').click();
  await page.getByTestId('onboard-style-continue').click();
  await expect(page.getByTestId('main-app')).toBeVisible({ timeout: 15_000 });
}

test.describe('DeepDive UI', () => {
  test('onboarding from splash to app', async ({ page }) => {
    await page.goto('/DeepDive.html');
    await page.evaluate(() => {
      localStorage.clear();
    });
    await page.reload();
    await page.getByTestId('splash-get-started').click();
    await expect(page.getByTestId('onboard-age-continue')).toBeVisible();
    await page.getByRole('button', { name: '18–24' }).click();
    await page.getByTestId('onboard-age-continue').click();
    await page.getByRole('button', { name: /expedition/i }).click();
    await page.getByTestId('onboard-trip-continue').click();
    await page.getByTestId('onboard-style-continue').click();
    await expect(page.getByTestId('main-app')).toBeVisible();
  });

  test('tabs, FAB, action sheet', async ({ page }) => {
    await goToApp(page);
    await page.getByTestId('tab-spots').click();
    await page.getByTestId('tab-trips').click();
    await page.getByTestId('fab-main').click();
    await expect(page.getByTestId('action-new-trip')).toBeVisible();
    await expect(page.getByTestId('action-add-spots')).toBeVisible();
    await page.getByTestId('action-sheet-backdrop').click({ position: { x: 10, y: 10 } });
  });

  test('trip card opens detail', async ({ page }) => {
    await goToApp(page);
    await page.getByTestId('trip-card').first().click();
    await expect(page.getByTestId('trip-detail-back')).toBeVisible();
    await page.getByTestId('trip-detail-back').click();
    await expect(page.getByTestId('plan-new-trip')).toBeVisible();
  });

  test('plan panel with mocked API', async ({ page }) => {
    await goToApp(page);
    await page.route('http://127.0.0.1:8000/plan-from-posts', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          trip: tripFixture,
          candidate_places: [],
        }),
      });
    });
    await page.getByTestId('plan-new-trip').click();
    await page.getByTestId('plan-destination-input').fill('Maldives');
    await page.getByTestId('plan-when').click();
    const dayCells = page.getByTestId('plan-cal-day');
    const n = await dayCells.count();
    expect(n).toBeGreaterThan(2);
    await dayCells.nth(0).click();
    await dayCells.nth(Math.min(8, n - 1)).click();
    await page.getByTestId('plan-submit').click();
    await expect(page.getByTestId('trip-detail-back')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('Mock plan for E2E')).toBeVisible();
  });

  test('add spots extract panel', async ({ page }) => {
    await goToApp(page);
    // Match API only — broad **/extract can match unrelated CDN paths containing "extract".
    await page.route('http://127.0.0.1:8000/extract', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ results: [] }),
      });
    });
    await page.getByTestId('tab-spots').click();
    await page.getByTestId('spots-add-dive').click();
    await page.getByTestId('addspots-notes').click();
    await page.getByTestId('addspots-extract-input').fill('Raja Ampat diving');
    await page.getByTestId('addspots-extract-submit').click();
    await expect(page.getByTestId('addspots-extract-result')).toBeVisible({ timeout: 10_000 });
    await page.getByTestId('addspots-extract-back').click();
    await page.getByTestId('addspots-close').click();
  });

  test('profile sign out returns to splash', async ({ page }) => {
    await goToApp(page);
    await page.getByTestId('profile-button').click();
    await page.getByTestId('profile-sign-out').click();
    await expect(page.getByTestId('splash-get-started')).toBeVisible();
  });
});
