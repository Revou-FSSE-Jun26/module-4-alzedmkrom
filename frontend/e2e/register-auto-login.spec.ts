import { expect, test } from '@playwright/test';
import { registerThroughUi } from './helpers/auth';

// FE-PAGE-01: a new account is signed in automatically. The helper checks the landing on `/` and
// the "Log out" button. This test also checks that the session belongs to the new user.
test('registration signs the new user in and the profile shows that user', async ({ page }) => {
  const user = await registerThroughUi(page);
  await page.goto('/profile');
  await expect(page.getByLabel('Email', { exact: true })).toHaveValue(user.email.toLowerCase());
});
