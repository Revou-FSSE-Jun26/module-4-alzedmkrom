import { expect, test } from '@playwright/test';

// Browser checks for the route states added for FE-UX-01, FE-PAGE-03, and FE-PAGE-05.
// Uses the seeded demo users (flask seed). The password is the documented demo value.
const DEMO_PASSWORD = process.env.SEED_PASSWORD ?? 'revotask-dev';
const MISSING_BOARD_ID = '00000000-0000-0000-0000-000000000000';

test('a missing board shows the board not-found page', async ({ page }) => {
  await page.goto(`/boards/${MISSING_BOARD_ID}`);
  await expect(page.getByRole('heading', { name: 'Board not found' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Back to dashboard' })).toHaveAttribute('href', '/');
});

test('an anonymous visitor opening my tasks is sent to login', async ({ page }) => {
  await page.goto('/my-tasks');
  await expect(page).toHaveURL(/\/login/);
});

test('a logged-in member sees the my tasks page with its heading', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email', { exact: true }).fill('alice@revotask.test');
  await page.getByLabel('Password', { exact: true }).fill(DEMO_PASSWORD);
  await page.getByRole('button', { name: 'Log in' }).click();
  await expect(page).toHaveURL((url) => url.pathname === '/');

  await page.goto('/my-tasks');
  await expect(page.getByRole('heading', { name: 'My tasks' })).toBeVisible();
});
