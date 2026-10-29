import { QueryClient } from '@tanstack/react-query';
import { createCourseQueries } from '@/entities/course';
import { createAuthoringGateway } from '@/entities/authoring';
import { createEnrollmentGateway } from '@/entities/enrollment';
import { createQuizGateway } from '@/entities/quiz';
import { createNotificationGateway } from '@/entities/notification';
import { createAccountGateway, SessionManager } from '@/entities/session';
import { createHttpClient, HttpError } from '@/shared/api';
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (count, error) => !(error instanceof HttpError && error.status < 500) && count < 1,
    },
    mutations: { retry: false },
  },
});
const http = createHttpClient();
export const gateway = createAccountGateway(http);
export const session = new SessionManager(gateway, () => {
  void queryClient.cancelQueries({ queryKey: ['private'] });
  queryClient.removeQueries({ queryKey: ['private'] });
});
http.authorize(session);
export const courseQueries = createCourseQueries(http);
export const authoringGateway = createAuthoringGateway(http);
export const enrollmentGateway = createEnrollmentGateway(http);
export const quizGateway = createQuizGateway(http);
export const notificationGateway = createNotificationGateway(http);
