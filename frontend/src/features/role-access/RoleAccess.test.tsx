import { act, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { AccountContext, SessionManager } from '@/entities/session';
import type { AccountGateway, User } from '@/entities/session';
import { RoleAccess } from './index';

async function setup(role: User['role'], admin = false) {
  const user: User = { id: 1, name: 'User', email: 'user@example.com', is_active: true, role };
  const gateway = {
    login: vi.fn().mockResolvedValue({ access_token: 'access', refresh_token: 'a'.repeat(43) }),
    me: vi.fn().mockResolvedValue(user),
  } as unknown as AccountGateway;
  const session = new SessionManager(gateway, vi.fn());
  await session.signIn({ email: user.email, password: 'password' });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <AccountContext.Provider value={{ session, gateway }}>
        <MemoryRouter>
          <RoleAccess admin={admin}>
            <div>Protected content</div>
          </RoleAccess>
        </MemoryRouter>
      </AccountContext.Provider>
    </QueryClientProvider>,
  );
  return { gateway, client, user };
}
describe('role access', () => {
  it('denies students access to the authoring UI', async () => {
    await setup('student');
    expect(await screen.findByRole('alert')).toHaveTextContent('права преподавателя');
    expect(screen.queryByText('Protected content')).not.toBeInTheDocument();
  });
  it('denies teachers access to admin UI', async () => {
    await setup('teacher', true);
    expect(await screen.findByRole('alert')).toHaveTextContent('права администратора');
  });
  it('allows admins after checking the live profile', async () => {
    const { gateway } = await setup('admin', true);
    expect(await screen.findByText('Protected content')).toBeInTheDocument();
    expect(gateway.me).toHaveBeenCalledTimes(2);
  });
  it('preserves editors during background checks then removes access after demotion', async () => {
    const { gateway, client, user } = await setup('teacher');
    await screen.findByText('Protected content');
    let resolve!: (user: User) => void;
    vi.mocked(gateway.me).mockReturnValue(
      new Promise<User>((yes) => {
        resolve = yes;
      }),
    );
    let pending!: Promise<void>;
    await act(async () => {
      pending = client.invalidateQueries({ queryKey: ['private', 'permissions'] });
    });
    expect(screen.getByText('Protected content')).toBeInTheDocument();
    await act(async () => {
      resolve({ ...user, role: 'student' });
      await pending;
    });
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.queryByText('Protected content')).not.toBeInTheDocument();
  });
});
