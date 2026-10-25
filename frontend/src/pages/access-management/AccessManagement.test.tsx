import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { EnrollmentContext, createEnrollmentGateway } from '@/entities/enrollment';
import { AccountContext, SessionManager } from '@/entities/session';
import type { AccountGateway } from '@/entities/session';
import AccessManagementPage from './index';

async function setup() {
  const student = {
    id: 1,
    name: 'Student',
    email: 'student@example.com',
    role: 'student',
    is_active: true,
  };
  const account = {
    login: vi.fn().mockResolvedValue({ access_token: 'access', refresh_token: 'a'.repeat(43) }),
    me: vi.fn().mockResolvedValue({ ...student, id: 2, role: 'teacher' }),
  } as unknown as AccountGateway;
  const session = new SessionManager(account, vi.fn());
  await session.signIn({ email: student.email, password: 'password' });
  const grant = {
    id: 30,
    course_id: 10,
    user_id: 1,
    source: 'admin_grant',
    request_id: null,
    granted_by: 3,
    created_at: '2026-10-12T10:00:00Z',
    expires_at: '2099-01-01T00:00:00Z',
    revoked_at: null,
    revoked_by: null,
    student,
    active: true,
  };
  const pending = {
    id: 20,
    course_id: 10,
    user_id: 1,
    status: 'pending',
    message: '<script>text</script>',
    created_at: '2026-10-12T10:00:00Z',
    decided_at: null,
    decided_by: null,
    decision_note: '',
    student,
  };
  const request = vi
    .fn()
    .mockImplementation(async (path: string, options?: { method?: string }) => {
      if (options?.method) return undefined;
      return {
        items: path.includes('/requests?') ? [pending] : [grant],
        total: 1,
        limit: 20,
        offset: 0,
      };
    });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <AccountContext.Provider value={{ session, gateway: account }}>
        <EnrollmentContext.Provider
          value={createEnrollmentGateway({ request, authorize: vi.fn() })}
        >
          <MemoryRouter initialEntries={['/access/courses/10']}>
            <Routes>
              <Route path="/access/courses/:courseId" element={<AccessManagementPage />} />
            </Routes>
          </MemoryRouter>
        </EnrollmentContext.Provider>
      </AccountContext.Provider>
    </QueryClientProvider>,
  );
  return { request };
}
describe('teacher access management', () => {
  it('submits a scoped approval with a teacher-selected duration', async () => {
    const { request } = await setup();
    await screen.findByRole('button', { name: 'Одобрить' });
    const duration = screen.getByLabelText('Срок доступа в днях');
    await userEvent.clear(duration);
    await userEvent.type(duration, '30');
    await userEvent.click(screen.getByRole('button', { name: 'Одобрить' }));
    expect(request).toHaveBeenCalledWith(
      '/access/courses/10/requests/20',
      expect.objectContaining({
        method: 'PUT',
        authenticated: true,
        body: { decision: 'approve', duration_days: 30, note: '' },
      }),
    );
    expect(document.querySelector('script')).toBeNull();
  });
  it('prevents teachers from revoking an admin grant or creating one', async () => {
    await setup();
    expect(await screen.findByRole('button', { name: 'Отозвать разрешение' })).toBeDisabled();
    expect(screen.queryByRole('button', { name: 'Выдать доступ' })).not.toBeInTheDocument();
  });
});
