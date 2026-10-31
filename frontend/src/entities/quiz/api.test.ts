import { QueryClient } from '@tanstack/react-query';
import { describe, expect, it, vi } from 'vitest';
import { createQuizGateway, quizKey } from './api';
import { attemptSchema, questionWriteSchema, quizWriteSchema } from './model';
describe('quiz gateway and contracts', () => {
  it('keeps quiz data private and scoped to the current account', async () => {
    const request = vi
      .fn()
      .mockResolvedValue({
        module_id: 20,
        available: true,
        question_count: 10,
        passing_score: 70,
        time_limit_seconds: 600,
        remaining_today: 5,
        daily_limit: 5,
        reset_at: '2026-10-23T19:00:00Z',
        timezone: 'Asia/Almaty',
        open_attempt: null,
      });
    const gateway = createQuizGateway({ request, authorize: vi.fn() });
    const client = new QueryClient();
    await client.fetchQuery(gateway.info(1, 10, 20));
    expect(request).toHaveBeenCalledWith(
      '/courses/10/modules/20/quiz',
      expect.objectContaining({ authenticated: true, signal: expect.any(AbortSignal) }),
    );
    expect(gateway.info(1, 10, 20).queryKey.slice(0, 4)).toEqual(quizKey(1, 10));
    expect(gateway.info(2, 10, 20).queryKey).not.toEqual(gateway.info(1, 10, 20).queryKey);
    client.clear();
  });
  it('sends only answers for grading and uses an owned attempt path', async () => {
    const request = vi.fn().mockResolvedValue({});
    const gateway = createQuizGateway({ request, authorize: vi.fn() });
    await expect(gateway.submit(10, 'attempt', { 12: 'B' })).rejects.toThrow();
    expect(request).toHaveBeenCalledWith('/courses/10/attempts/attempt/submit', {
      method: 'POST',
      body: { answers: { 12: 'B' } },
      authenticated: true,
    });
  });
  it('uses quiz revisions on all authoring writes', async () => {
    const request = vi.fn().mockResolvedValue(undefined);
    const gateway = createQuizGateway({ request, authorize: vi.fn() });
    await gateway.configure(10, 20, 3, {
      question_count: 1,
      passing_score: 70,
      time_limit_seconds: 600,
      enabled: false,
    });
    await gateway.archive(10, 20, 4, 99);
    expect(request.mock.calls[0]![0]).toBe('/authoring/courses/10/modules/20/quiz?revision=3');
    expect(request.mock.calls[1]![0]).toBe(
      '/authoring/courses/10/modules/20/quiz/questions/99?revision=4',
    );
  });
  it('rejects a malformed attempt response', () => {
    expect(attemptSchema.safeParse({ status: 'submitted', result: { passed: true } }).success).toBe(
      false,
    );
  });
  it.each([0, 101, 1.5])('rejects invalid quiz length %s', (question_count) => {
    expect(
      quizWriteSchema.safeParse({
        question_count,
        passing_score: 70,
        time_limit_seconds: 600,
        enabled: true,
      }).success,
    ).toBe(false);
  });
  it('requires all four answers and an explanation', () => {
    expect(
      questionWriteSchema.safeParse({
        lesson_id: 1,
        prompt: 'Test',
        options: { A: '1', B: '2', C: '3' },
        correct_option: 'A',
        explanation: '',
        is_active: true,
      }).success,
    ).toBe(false);
  });
});
