import { queryOptions } from '@tanstack/react-query';
import type { HttpClient } from '@/shared/api';
import { accessSchema, enrollmentPageSchema, grantPageSchema, requestPageSchema } from './model';
import type { AccessCommand, RequestStatus } from './model';
export const accessKey = (courseId: number, userId: number) =>
  ['private', 'enrollment', 'access', userId, courseId] as const;
export function createEnrollmentGateway(http: HttpClient) {
  return {
    status(courseId: number, userId: number) {
      return queryOptions({
        queryKey: accessKey(courseId, userId),
        staleTime: 0,
        refetchInterval: 30000,
        retry: false,
        enabled: Number.isSafeInteger(courseId) && courseId > 0 && userId > 0,
        queryFn: async ({ signal }) =>
          accessSchema.parse(
            await http.request(`/courses/${courseId}/access`, { authenticated: true, signal }),
          ),
      });
    },
    mine(userId: number, offset: number) {
      return queryOptions({
        queryKey: ['private', 'enrollment', 'mine', userId, offset],
        staleTime: 0,
        queryFn: async ({ signal }) =>
          enrollmentPageSchema.parse(
            await http.request(`/me/courses?limit=20&offset=${offset}`, {
              authenticated: true,
              signal,
            }),
          ),
      });
    },
    requests(courseId: number, status: RequestStatus | 'all', offset: number) {
      const params = new URLSearchParams({ limit: '20', offset: String(offset) });
      params.set('status', status);
      return queryOptions({
        queryKey: ['private', 'enrollment', 'requests', courseId, status, offset],
        staleTime: 0,
        queryFn: async ({ signal }) =>
          requestPageSchema.parse(
            await http.request(`/access/courses/${courseId}/requests?${params}`, {
              authenticated: true,
              signal,
            }),
          ),
      });
    },
    grants(courseId: number, activeOnly: boolean, offset: number) {
      return queryOptions({
        queryKey: ['private', 'enrollment', 'grants', courseId, activeOnly, offset],
        staleTime: 0,
        queryFn: async ({ signal }) =>
          grantPageSchema.parse(
            await http.request(
              `/access/courses/${courseId}/grants?limit=20&offset=${offset}&active_only=${activeOnly}`,
              { authenticated: true, signal },
            ),
          ),
      });
    },
    async command(command: AccessCommand): Promise<void> {
      await http.request(command.path, {
        method: command.method,
        body: command.body,
        authenticated: true,
      });
    },
  };
}
export type EnrollmentGateway = ReturnType<typeof createEnrollmentGateway>;
