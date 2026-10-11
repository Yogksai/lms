import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, expect, it, vi } from 'vitest';
import { AuthoringContext, authoringKey } from '@/entities/authoring';
import type { AuthoringGateway, EditorCourse } from '@/entities/authoring';
import { AccountContext, SessionManager } from '@/entities/session';
import type { AccountGateway } from '@/entities/session';
import { useCourseCommand } from './commands';

function Save() {
  const mutation = useCourseCommand(1, 1);
  return (
    <>
      <button onClick={() => mutation.mutate({ method: 'PUT', body: {} })}>Save</button>
      {mutation.isError && <span>Rejected late response</span>}
    </>
  );
}
describe('authoring command lifecycle', () => {
  it('does not repopulate private cache after logout during a save', async () => {
    const account = {
      login: vi.fn().mockResolvedValue({ access_token: 'access', refresh_token: 'a'.repeat(43) }),
      me: vi.fn().mockResolvedValue({
        id: 1,
        name: 'Teacher',
        email: 'teacher@example.com',
        role: 'teacher',
        is_active: true,
      }),
      logout: vi.fn().mockResolvedValue(undefined),
    } as unknown as AccountGateway;
    const session = new SessionManager(account, vi.fn());
    await session.signIn({ email: 'teacher@example.com', password: 'password' });
    let resolve!: (course: EditorCourse) => void;
    const gateway = {
      command: vi.fn().mockReturnValue(
        new Promise<EditorCourse>((yes) => {
          resolve = yes;
        }),
      ),
    } as unknown as AuthoringGateway;
    const client = new QueryClient();
    render(
      <QueryClientProvider client={client}>
        <AccountContext.Provider value={{ session, gateway: account }}>
          <AuthoringContext.Provider value={gateway}>
            <Save />
          </AuthoringContext.Provider>
        </AccountContext.Provider>
      </QueryClientProvider>,
    );
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(gateway.command).toHaveBeenCalledTimes(1);
    await act(async () => {
      await session.signOut();
      resolve({
        id: 1,
        title: 'Math',
        slug: 'math',
        description: '',
        status: 'draft',
        revision: 2,
        modules: [],
        teachers: [],
      });
    });
    expect(await screen.findByText('Rejected late response')).toBeInTheDocument();
    expect(client.getQueryData(authoringKey(1))).toBeUndefined();
  });
});
