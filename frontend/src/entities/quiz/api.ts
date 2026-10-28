import { queryOptions } from '@tanstack/react-query';
import type { HttpClient } from '@/shared/api';
import { attemptSchema, bankSchema, historySchema, infoSchema, progressSchema } from './model';
import type { Choice, QuestionWrite, QuizWrite } from './model';
export const quizKey = (userId: number, courseId: number) =>
  ['private', 'quiz', userId, courseId] as const;
export function createQuizGateway(http: HttpClient) {
  const base = (courseId: number) => `/courses/${courseId}`;
  const module = (courseId: number, moduleId: number) => `${base(courseId)}/modules/${moduleId}`;
  const author = (courseId: number, moduleId: number) =>
    `/authoring${module(courseId, moduleId)}/quiz`;
  const get = async (path: string, signal: AbortSignal) =>
    http.request(path, { authenticated: true, signal });
  return {
    bank(userId: number, courseId: number, moduleId: number, offset: number) {
      return queryOptions({
        queryKey: [...quizKey(userId, courseId), 'bank', moduleId, offset],
        staleTime: 0,
        refetchOnWindowFocus: false,
        queryFn: async ({ signal }) =>
          bankSchema.parse(
            await get(`${author(courseId, moduleId)}?limit=20&offset=${offset}`, signal),
          ),
      });
    },
    async configure(courseId: number, moduleId: number, revision: number, body: QuizWrite) {
      await http.request(`${author(courseId, moduleId)}?revision=${revision}`, {
        method: 'PUT',
        body,
        authenticated: true,
      });
    },
    async saveQuestion(
      courseId: number,
      moduleId: number,
      revision: number,
      body: QuestionWrite,
      questionId?: number,
    ) {
      await http.request(
        `${author(courseId, moduleId)}/questions${questionId ? '/' + questionId : ''}?revision=${revision}`,
        { method: questionId ? 'PUT' : 'POST', body, authenticated: true },
      );
    },
    async archive(courseId: number, moduleId: number, revision: number, questionId: number) {
      await http.request(
        `${author(courseId, moduleId)}/questions/${questionId}?revision=${revision}`,
        { method: 'DELETE', authenticated: true },
      );
    },
    info(userId: number, courseId: number, moduleId: number) {
      return queryOptions({
        queryKey: [...quizKey(userId, courseId), 'info', moduleId],
        staleTime: 0,
        retry: false,
        queryFn: async ({ signal }) =>
          infoSchema.parse(await get(`${module(courseId, moduleId)}/quiz`, signal)),
      });
    },
    async start(courseId: number, moduleId: number) {
      return attemptSchema.parse(
        await http.request(`${module(courseId, moduleId)}/attempts`, {
          method: 'POST',
          authenticated: true,
        }),
      );
    },
    attempt(userId: number, courseId: number, attemptId: string) {
      return queryOptions({
        queryKey: [...quizKey(userId, courseId), 'attempt', attemptId],
        staleTime: 0,
        retry: false,
        queryFn: async ({ signal }) =>
          attemptSchema.parse(
            await get(`${base(courseId)}/attempts/${encodeURIComponent(attemptId)}`, signal),
          ),
      });
    },
    async submit(courseId: number, attemptId: string, answers: Record<string, Choice>) {
      return attemptSchema.parse(
        await http.request(`${base(courseId)}/attempts/${encodeURIComponent(attemptId)}/submit`, {
          method: 'POST',
          body: { answers },
          authenticated: true,
        }),
      );
    },
    history(userId: number, courseId: number, moduleId: number, offset: number) {
      return queryOptions({
        queryKey: [...quizKey(userId, courseId), 'history', moduleId, offset],
        staleTime: 0,
        queryFn: async ({ signal }) =>
          historySchema.parse(
            await get(`${module(courseId, moduleId)}/attempts?limit=20&offset=${offset}`, signal),
          ),
      });
    },
    progress(userId: number, courseId: number) {
      return queryOptions({
        queryKey: [...quizKey(userId, courseId), 'progress'],
        staleTime: 0,
        retry: false,
        queryFn: async ({ signal }) =>
          progressSchema.parse(await get(`${base(courseId)}/progress`, signal)),
      });
    },
    async completeLesson(courseId: number, moduleId: number, lessonId: number, completed: boolean) {
      return progressSchema.parse(
        await http.request(`${module(courseId, moduleId)}/lessons/${lessonId}/completion`, {
          method: 'PUT',
          body: { completed },
          authenticated: true,
        }),
      );
    },
  };
}
export type QuizGateway = ReturnType<typeof createQuizGateway>;
