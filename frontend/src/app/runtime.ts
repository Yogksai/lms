import { QueryClient } from '@tanstack/react-query';
import { createCourseQueries } from '@/entities/course';
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
