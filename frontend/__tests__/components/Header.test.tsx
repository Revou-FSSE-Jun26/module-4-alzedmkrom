import { fireEvent, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Header } from '@/components/layout/Header';
import { renderWithAuth, DEFAULT_TEST_USER } from '../helpers/renderWithAuth';

vi.mock('@/components/layout/NotificationBell', () => ({
  NotificationBell: () => <div data-testid="notification-bell" />,
}));

describe('Header', () => {
  it('renders the brand link, the bell and the navigation links with the user name', () => {
    renderWithAuth(<Header />);

    expect(screen.getByRole('link', { name: 'RevoTask' })).toHaveAttribute('href', '/');
    expect(screen.getByTestId('notification-bell')).toBeInTheDocument();

    const nav = document.getElementById('main-nav');
    expect(nav?.tagName).toBe('NAV');
    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute('href', '/');
    expect(screen.getByRole('link', { name: 'My tasks' })).toHaveAttribute('href', '/my-tasks');
    expect(screen.getByRole('link', { name: 'Profile' })).toHaveAttribute('href', '/profile');
    expect(nav).toHaveTextContent(DEFAULT_TEST_USER.name);
  });

  // FE-AUTH-03: after logout, or for an anonymous visitor, the header offers Log in only.
  it('shows Log in and no signed-in controls for an anonymous visitor', () => {
    renderWithAuth(<Header />, { token: null, user: null });

    expect(screen.getByRole('link', { name: 'Log in' })).toHaveAttribute('href', '/login');
    expect(screen.queryByRole('button', { name: 'Log out' })).toBeNull();
    expect(screen.queryByRole('link', { name: 'My tasks' })).toBeNull();
    expect(screen.queryByRole('link', { name: 'Profile' })).toBeNull();
  });

  it('calls logout once when the Log out button is clicked', () => {
    const { spies } = renderWithAuth(<Header />);

    fireEvent.click(screen.getByRole('button', { name: 'Log out' }));

    expect(spies.logout).toHaveBeenCalledTimes(1);
  });

  it('hides the navigation below sm until the menu button opens it', () => {
    renderWithAuth(<Header />);

    const menuButton = screen.getByRole('button', { name: 'Toggle navigation' });
    const nav = document.getElementById('main-nav') as HTMLElement;

    expect(menuButton).toHaveClass('sm:hidden');
    expect(menuButton).toHaveAttribute('aria-expanded', 'false');
    expect(menuButton).toHaveAttribute('aria-controls', 'main-nav');
    expect(nav).toHaveClass('hidden', 'sm:flex');

    fireEvent.click(menuButton);

    expect(menuButton).toHaveAttribute('aria-expanded', 'true');
    expect(nav).not.toHaveClass('hidden');
    expect(nav).toHaveClass('flex');

    fireEvent.click(menuButton);

    expect(menuButton).toHaveAttribute('aria-expanded', 'false');
    expect(nav).toHaveClass('hidden');
  });
});
