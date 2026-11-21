import { randomBytes } from 'node:crypto';
import { expect, type Page } from '@playwright/test';

export interface TestUser {
  name: string;
  email: string;
  password: string;
}

interface RegisterOptions {
  user?: TestUser;
  expectLogoutButton?: boolean;
}

// Each call returns a new user. The credentials exist only in the returned object and are never stored.
export function newUser(): TestUser {
  const suffix = randomBytes(6).toString('hex');
  return {
    name: `E2E ${suffix}`,
    email: `e2e-${Date.now()}-${suffix}@example.com`,
    password: `Pw-${randomBytes(9).toString('base64url')}`,
  };
}

// Registers through the UI. The app signs the user in after registration, so the test lands on `/`.
export async function registerThroughUi(page: Page, options: RegisterOptions = {}): Promise<TestUser> {
  const user = options.user ?? newUser();
  const expectLogoutButton = options.expectLogoutButton ?? true;

  await page.goto('/register');
  await page.getByLabel('Name', { exact: true }).fill(user.name);
  await page.getByLabel('Email', { exact: true }).fill(user.email);
  await page.getByLabel('Password', { exact: true }).fill(user.password);
  await page.getByRole('button', { name: 'Create account' }).click();

  await expect(page).toHaveURL((url) => url.pathname === '/');
  if (expectLogoutButton) {
    await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible();
  }

  return user;
}

// Logs out through the UI. On narrow viewports the navigation is collapsed behind the menu button.
export async function logoutThroughUi(page: Page): Promise<void> {
  const menuButton = page.getByRole('button', { name: 'Toggle navigation' });
  const logoutButton = page.getByRole('button', { name: 'Log out' });

  // Wait until either control is visible so the menu state is known before deciding to open it.
  await expect(menuButton.or(logoutButton)).toBeVisible();
  if (await menuButton.isVisible()) {
    await menuButton.click();
  }

  await logoutButton.click();
}
