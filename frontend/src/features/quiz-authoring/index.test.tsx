import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { createQuizGateway, QuizContext } from '@/entities/quiz';
import type { Bank } from '@/entities/quiz';
import { HttpError } from '@/shared/api';
import { QuizEditor } from './index';
vi.mock('@/entities/session', () => ({
  useCurrentUser: () => ({ id: 1 }),
  useAccount: () => ({ session: { identityVersion: () => 1 } }),
}));
const bank: Bank = {
  module_id: 20,
  title: 'Math',
  course_status: 'draft',
  lessons: [{ id: 2, module_id: 20, title: 'Fractions', position: 1 }],
  config: {
    id: 30,
    module_id: 20,
    revision: 3,
    question_count: 1,
    passing_score: 70,
    time_limit_seconds: 600,
    enabled: false,
  },
  active_questions: 0,
  items: [],
  total: 0,
  limit: 20,
  offset: 0,
};
function setup(data: Bank, request = vi.fn().mockResolvedValue(undefined)) {
  const client = new QueryClient();
  const gateway = createQuizGateway({ request, authorize: vi.fn() });
  render(
    <QueryClientProvider client={client}>
      <QuizContext.Provider value={gateway}>
        <QuizEditor bank={data} courseId={10} reload={vi.fn()} />
      </QuizContext.Provider>
    </QueryClientProvider>,
  );
  return request;
}
describe('quiz authoring', () => {
  it('keeps question editing disabled until a quiz is configured', () => {
    setup({ ...bank, config: null });
    expect(screen.getByRole('button', { name: 'Сохранить вопрос' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Сохранить настройки' })).toBeEnabled();
  });
  it('blocks writes on published courses', () => {
    setup({ ...bank, course_status: 'published' });
    expect(screen.getByRole('button', { name: 'Сохранить настройки' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Сохранить вопрос' })).toBeDisabled();
  });
  it('validates empty questions without making a request', async () => {
    const request = setup(bank);
    await userEvent.click(screen.getByRole('button', { name: 'Сохранить вопрос' }));
    expect(await screen.findByText(/Укажи урок/)).toBeInTheDocument();
    expect(request).not.toHaveBeenCalled();
  });
  it('keeps config fields on a stale revision error', async () => {
    setup(bank, vi.fn().mockRejectedValue(new HttpError(409, 'stale')));
    const length = screen.getByRole('spinbutton', { name: 'Количество вопросов (1–100)' });
    await userEvent.clear(length);
    await userEvent.type(length, '5');
    await userEvent.click(screen.getByRole('button', { name: 'Сохранить настройки' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Версия изменилась');
    expect(length).toHaveValue(5);
  });
});
