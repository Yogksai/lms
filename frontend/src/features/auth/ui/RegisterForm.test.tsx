import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { AccountContext, SessionManager } from '@/entities/session';
import type { AccountGateway } from '@/entities/session';
import { RegisterForm } from './RegisterForm';
describe('registration form', () => {
  it('validates input before making a registration request', async () => {
    const gateway = { register: vi.fn() } as unknown as AccountGateway;
    render(
      <AccountContext.Provider value={{ gateway, session: new SessionManager(gateway, vi.fn()) }}>
        <MemoryRouter>
          <RegisterForm />
        </MemoryRouter>
      </AccountContext.Provider>,
    );
    await userEvent.click(screen.getByRole('button', { name: 'Зарегистрироваться' }));
    expect(await screen.findByText('Введите имя')).toBeInTheDocument();
    expect(gateway.register).not.toHaveBeenCalled();
  });
});
