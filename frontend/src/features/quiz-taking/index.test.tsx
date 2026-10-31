import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { createQuizGateway, QuizContext } from '@/entities/quiz';
import type { Attempt } from '@/entities/quiz';
import { AttemptForm, AttemptReview, QuizStart } from './index';
const account = vi.hoisted(() => ({ identity: 1 }));
vi.mock('@/entities/session', () => ({
  useCurrentUser: () => ({ id: 1 }),
  useAccount: () => ({ session: { identityVersion: () => account.identity } }),
}));
const attempt: Attempt = {
  attempt_id: '00000000-0000-4000-8000-000000000001',
  course_id: 10,
  module_id: 20,
  module_title: 'Math',
  quiz_revision: 1,
  passing_score: 70,
  started_at: '2026-10-22T10:00:00Z',
  deadline_at: '2026-10-22T10:10:00Z',
  server_time: '2026-10-22T10:00:00Z',
  status: 'in_progress',
  questions: [
    {
      question_id: 1,
      lesson_id: 2,
      lesson_title: 'Fractions',
      prompt: '1 + 1?',
      options: { A: '2', B: '3', C: '4', D: '5' },
    },
  ],
  answers: {},
  result: null,
};
function setup(element: React.ReactNode, request = vi.fn()) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const gateway = createQuizGateway({ request, authorize: vi.fn() });
  render(
    <QueryClientProvider client={client}>
      <QuizContext.Provider value={gateway}>
        <MemoryRouter>{element}</MemoryRouter>
      </QuizContext.Provider>
    </QueryClientProvider>,
  );
  return { client, request };
}
afterEach(() => {
  vi.restoreAllMocks();
  account.identity = 1;
});
describe('quiz taking', () => {
  it('does not render explanations before submission', () => {
    setup(<AttemptForm attempt={attempt} />);
    expect(screen.queryByText(/Правильный ответ/)).not.toBeInTheDocument();
    expect(screen.getAllByRole('radio')).toHaveLength(4);
  });
  it('submits only selected question answers', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const request = vi.fn().mockResolvedValue({ ...attempt, status: 'expired' });
    setup(<AttemptForm attempt={attempt} />, request);
    await userEvent.click(screen.getByRole('radio', { name: 'A. 2' }));
    await userEvent.click(screen.getByRole('button', { name: 'Сдать тест' }));
    await waitFor(() =>
      expect(request).toHaveBeenCalledWith(
        expect.stringContaining('/submit'),
        expect.objectContaining({ body: { answers: { 1: 'A' } } }),
      ),
    );
  });
  it('keeps answers after a network error for a safe retry', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    setup(<AttemptForm attempt={attempt} />, vi.fn().mockRejectedValue(new Error('offline')));
    await userEvent.click(screen.getByRole('radio', { name: 'B. 3' }));
    await userEvent.click(screen.getByRole('button', { name: 'Сдать тест' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Ответы остались в форме');
    expect(screen.getByRole('radio', { name: 'B. 3' })).toBeChecked();
  });
  it('does not apply a late submission after account change', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    let resolve!: (value: unknown) => void;
    const pending = new Promise((done) => {
      resolve = done;
    });
    const { client } = setup(<AttemptForm attempt={attempt} />, vi.fn().mockReturnValue(pending));
    await userEvent.click(screen.getByRole('button', { name: 'Сдать тест' }));
    account.identity = 2;
    resolve({ ...attempt, status: 'expired' });
    await waitFor(() => expect(screen.getByRole('button', { name: 'Сдать тест' })).toBeEnabled());
    expect(client.getQueryCache().findAll()).toHaveLength(0);
  });
  it('shows result explanations and links only for existing lessons', () => {
    setup(
      <AttemptReview
        attempt={{
          ...attempt,
          status: 'submitted',
          result: {
            correct_count: 0,
            total: 1,
            score_percent: 0,
            passed: false,
            questions: [
              {
                ...attempt.questions[0]!,
                selected_option: 'B',
                correct_option: 'A',
                is_correct: false,
                explanation: 'Add one and one.',
              },
            ],
            review_lessons: [
              { lesson_id: 2, title: 'Fractions', wrong_answers: 1 },
              { lesson_id: null, title: 'Old lesson', wrong_answers: 1 },
            ],
          },
        }}
      />,
    );
    expect(screen.getByText('Add one and one.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Fractions' })).toHaveAttribute(
      'href',
      '/courses/10/modules/20/lessons/2',
    );
    expect(screen.getByText(/Old lesson/)).toBeInTheDocument();
  });
  it('does not permit a new attempt when daily limit is exhausted', () => {
    setup(
      <QuizStart
        courseId={10}
        info={{
          module_id: 20,
          available: true,
          question_count: 10,
          passing_score: 70,
          time_limit_seconds: 600,
          remaining_today: 0,
          daily_limit: 5,
          reset_at: '2026-10-22T19:00:00Z',
          timezone: 'Asia/Almaty',
          open_attempt: null,
        }}
      />,
    );
    expect(screen.getByRole('button', { name: 'Начать тест' })).toBeDisabled();
  });
});
