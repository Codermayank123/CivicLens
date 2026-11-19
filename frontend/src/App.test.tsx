// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ProtectedRoute } from './App';
import { useAuthStore } from './store/authStore';
import type { UserProfile } from './types';

const createUser = (roles: string[]): UserProfile => ({
  id: 'test-user',
  email: 'test@example.com',
  full_name: 'Test User',
  roles,
  preferred_language: 'en',
  high_contrast_mode: false,
  reduced_motion: false,
  is_verified: true,
  created_at: '2026-01-01T00:00:00Z',
});

const renderProtectedRoute = () =>
  render(
    <MemoryRouter initialEntries={['/protected']}>
      <Routes>
        <Route
          path="/protected"
          element={
            <ProtectedRoute roles={['officer']}>
              <p>Officer dashboard</p>
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<p>Login page</p>} />
        <Route path="/" element={<p>Home page</p>} />
      </Routes>
    </MemoryRouter>,
  );

describe('ProtectedRoute', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: createUser(['citizen']),
      isAuthenticated: true,
      isLoading: false,
    });
  });

  afterEach(() => cleanup());

  it('redirects authenticated users without an allowed role', () => {
    renderProtectedRoute();

    expect(screen.getByText('Home page')).toBeTruthy();
  });

  it('allows admins to access role-protected dashboards', () => {
    useAuthStore.setState({ user: createUser(['admin']) });
    renderProtectedRoute();

    expect(screen.getByText('Officer dashboard')).toBeTruthy();
  });

  it('redirects unauthenticated users to login', () => {
    useAuthStore.setState({ user: null, isAuthenticated: false });
    renderProtectedRoute();

    expect(screen.getByText('Login page')).toBeTruthy();
  });
});
