import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';
import { BASEMAPS } from '../src/lib/mapBasemaps';

// This project is ESM ("type": "module" in package.json), so __dirname
// isn't available -- derive it from import.meta.url instead.
const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * End-to-end walkthrough against the REAL stack: live Supabase (Auth + DB)
 * and live Google Earth Engine. This is not a mocked test -- it registers a
 * real institution, a real field, and waits for a real satellite-processing
 * job to finish. See e2e/README.md for prerequisites.
 *
 * Deliberately does not assert a specific risk tier/outcome for the field --
 * that depends on real, variable satellite data availability. What it does
 * assert: every step completes without crashing, the field eventually leaves
 * the "processing" state (doesn't get stuck forever), and the portfolio
 * list/table responsive layout (docs/AUDIT-FINDINGS.md #20) behaves as
 * designed at both desktop and mobile widths.
 */
test.setTimeout(5 * 60_000);

test('register institution, register a field, verify dashboard and responsive fields list', async ({
  page,
}) => {
  const stamp = Date.now();
  // Not example.com/.test -- pydantic's EmailStr (backend/app/schemas/domain.py)
  // uses email-validator's deliverability check, which correctly rejects
  // RFC 2606 reserved domains (example.*, .test, .invalid, .localhost) as
  // undeliverable. gmail.com resolves real MX records, and +addressing keeps
  // each run's email unique without needing a real inbox per run.
  const email = `agrisat.e2e+${stamp}@gmail.com`;
  const password = 'E2ETestPassword123!';

  await test.step('Register a new institution + admin account', async () => {
    await page.goto('/register');
    await page.getByLabel('Organization name *').fill(`E2E Test Institution ${stamp}`);
    await page.getByLabel('Contact email *').fill(email);
    await page.getByLabel('Administrator email *').fill(email);
    await page.getByLabel(/Password/).fill(password);
    await page.getByRole('button', { name: 'Create institution' }).click();

    // Auto signs in and lands on the dashboard.
    await expect(page).toHaveURL('/', { timeout: 20_000 });
    await expect(page.getByText('Portfolio overview')).toBeVisible({ timeout: 15_000 });
  });

  await test.step('Map layer switcher has one entry per basemap, no duplicates', async () => {
    // Regression guard: a BaseLayer wrapping two sibling TileLayers (the old
    // "hybrid" pattern) registers as two duplicate radio entries instead of
    // one combined layer -- caught live, fixed in MapBasemapLayers.tsx.
    await page.getByRole('link', { name: '+ Register field' }).click();
    await expect(page).toHaveURL(/\/fields\/new/);
    await page.locator('.leaflet-control-layers').click();
    const labels = await page.locator('.leaflet-control-layers-list label').allInnerTexts();
    expect(labels).toHaveLength(BASEMAPS.length);
    expect(new Set(labels).size).toBe(labels.length);
    await page.locator('.leaflet-control-layers').click(); // close it again
  });

  await test.step('Register a field via GeoJSON upload', async () => {
    await page.getByRole('button', { name: 'Upload file' }).click();
    await page
      .locator('input[type="file"]')
      .setInputFiles(path.join(__dirname, 'fixtures', 'sample-field.geojson'));

    await expect(page.getByText(/Boundary ready/)).toBeVisible({ timeout: 10_000 });

    await page.getByLabel('Field name').fill(`E2E field ${stamp}`);
    await page.getByLabel('Farmer reference').fill(`E2E-FARMER-${stamp}`);

    await page.getByRole('button', { name: /Register & analyze/ }).click();

    // Per docs/AUDIT-FINDINGS.md #9: registration now navigates to the field
    // detail page immediately after the field is created, rather than
    // waiting on this page for processing to finish.
    await expect(page).toHaveURL(/\/fields\/[0-9a-f-]{36}$/, { timeout: 20_000 });
  });

  await test.step('Wait for satellite processing to leave the "processing" state', async () => {
    // Wait for the page's own initial fetch to resolve first -- otherwise
    // checking that the "processing" banner isn't visible can trivially
    // pass before the page has even had a chance to render it.
    await expect(page.getByText('Loading field analysis')).not.toBeVisible({ timeout: 15_000 });

    // Real GEE call -- can legitimately take a couple of minutes, but can
    // also finish in seconds (as it did here). Only wait on the banner if
    // it's actually showing; if processing already resolved by the time we
    // got here, there's nothing to wait for.
    const analyzingBanner = page.getByText('Satellite analysis in progress');
    if (await analyzingBanner.isVisible()) {
      await expect(analyzingBanner).not.toBeVisible({ timeout: 4 * 60_000 });
    }
    await page.screenshot({ path: 'e2e/screenshots/field-detail-resolved.png', fullPage: true });
  });

  await test.step('Fields list: desktop shows the table, not the card list', async () => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto('/fields');
    await expect(page.getByText('Loading field portfolio')).not.toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('heading', { name: 'Registered fields' })).toBeVisible();
    await expect(page.locator('.portfolio-table-desktop')).toBeVisible();
    await expect(page.locator('.field-card-list')).toBeHidden();
    await page.screenshot({ path: 'e2e/screenshots/fields-list-desktop.png', fullPage: true });
  });

  await test.step('Fields list: mobile shows the card list, not the table', async () => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.reload();
    await expect(page.getByText('Loading field portfolio')).not.toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('heading', { name: 'Registered fields' })).toBeVisible();
    await expect(page.locator('.field-card-list')).toBeVisible();
    await expect(page.locator('.portfolio-table-desktop')).toBeHidden();
    await page.screenshot({ path: 'e2e/screenshots/fields-list-mobile.png', fullPage: true });
  });

  await test.step('Dashboard loads with the registered field', async () => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto('/');
    await expect(page.getByText('Loading portfolio overview')).not.toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('Portfolio overview')).toBeVisible();
    await page.screenshot({ path: 'e2e/screenshots/dashboard.png', fullPage: true });
  });
});
