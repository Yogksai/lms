import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { EnrollmentContext, createEnrollmentGateway } from '@/entities/enrollment';
import type { CourseAccess as Access } from '@/entities/enrollment';
import { AccountContext, SessionManager } from '@/entities/session';
import type { AccountGateway } from '@/entities/session';
import { CourseAccess } from './CourseAccess';

const initial: Access = {
  course_id: 10,
  available: true,
  enrolled: false,
  full_access: false,
  reasons: [],
  expires_at: null,
  request: null,
  grants: [],
};
async function setup(access: Access, authenticated = true) {
  let state = access;
  const account = {
    login: vi.fn().mockResolvedValue({ access_token: 'access', refresh_token: 'a'.repeat(43) }),
    me: vi.fn().mockResolvedValue({
      id: 1,
      name: 'Student',
      email: 'student@example.com',
      is_active: true,
      role: 'student',
    }),
    logout: vi.fn().mockResolvedValue(undefined),
  } as unknown as AccountGateway;
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const session = new SessionManager(account, () => {
    void client.cancelQueries({ queryKey: ['private'] });
    client.removeQueries({ queryKey: ['private'] });
  });
  if (authenticated) await session.signIn({ email: 'student@example.com', password: 'password' });
  const request = vi
    .fn()
    .mockImplementation(async (path: string, options?: { method?: string }) => {
      if (path === '/courses/10/enrollment' && options?.method === 'POST') {
        state = { ...state, enrolled: true };
        return state;
      }
      return state;
    });
  const gateway = createEnrollmentGateway({ request, authorize: vi.fn() });
  render(
    <QueryClientProvider client={client}>
      <AccountContext.Provider value={{ session, gateway: account }}>
        <EnrollmentContext.Provider value={gateway}>
          <MemoryRouter>
            <CourseAccess
              courseId={10}
              outline={(full) => <span>{full ? 'Full outline' : 'Preview outline'}</span>}
            />
          </MemoryRouter>
        </EnrollmentContext.Provider>
      </AccountContext.Provider>
    </QueryClientProvider>,
  );
  return { request, client, session };
}
describe('student course access', () => {
  it('allows anonymous preview and asks for login before enrollment', async () => {
    const { request } = await setup(initial, false);
    expect(screen.getByText('Preview outline')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Войдите' })).toBeInTheDocument();
    expect(request).not.toHaveBeenCalled();
  });
  it('enrolls without unlocking and then offers an access request', async () => {
    const { request } = await setup(initial);
    await userEvent.click(await screen.findByRole('button', { name: 'Записаться на курс' }));
    expect(
      await screen.findByRole('button', { name: 'Запросить полный доступ' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Preview outline')).toBeInTheDocument();
    expect(request).toHaveBeenCalledWith(
      '/courses/10/enrollment',
      expect.objectContaining({ authenticated: true, method: 'POST' }),
    );
  });
  it('shows cancellation rather than duplicate request controls for a pending request', async () => {
    await setup({
      ...initial,
      enrolled: true,
      request: {
        id: 20,
        course_id: 10,
        user_id: 1,
        message: '',
        status: 'pending',
        created_at: '2026-10-12T10:00:00Z',
        decided_at: null,
        decided_by: null,
        decision_note: '',
      },
    });
    expect(await screen.findByRole('button', { name: 'Отменить заявку' })).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Запросить полный доступ' }),
    ).not.toBeInTheDocument();
  });
  it('shows approved access and expiry without a payment control', async () => {
    await setup({
      ...initial,
      enrolled: true,
      full_access: true,
      reasons: ['teacher_approval'],
      expires_at: '2099-01-01T00:00:00Z',
    });
    expect(await screen.findByText('Full outline')).toBeInTheDocument();
    expect(screen.getByText(/Все модули доступны до/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /купить|оплатить/i })).not.toBeInTheDocument();
  });
  it('allows a new request after a previous grant expires', async () => {
    await setup({
      ...initial,
      enrolled: true,
      request: {
        id: 20,
        course_id: 10,
        user_id: 1,
        message: '',
        status: 'approved',
        created_at: '2025-01-01T00:00:00Z',
        decided_at: '2025-01-02T00:00:00Z',
        decided_by: 2,
        decision_note: '',
      },
    });
    expect(
      await screen.findByRole('button', { name: 'Запросить полный доступ' }),
    ).toBeInTheDocument();
  });
  it('rejects late mutation completion after logout instead of refetching private data', async () => {
    const { session, request, client } = await setup(initial);
    await screen.findByRole('button', { name: 'Записаться на курс' });
    let resolve!: () => void;
    request.mockImplementationOnce(
      () =>
        new Promise<void>((yes) => {
          resolve = yes;
        }),
    );
    await userEvent.click(screen.getByRole('button', { name: 'Записаться на курс' }));
    await act(async () => {
      await session.signOut();
      resolve();
    });
    expect(await screen.findByRole('link', { name: 'Войдите' })).toBeInTheDocument();
    expect(client.getQueriesData({ queryKey: ['private', 'enrollment'] })).toEqual([]);
  });
});
