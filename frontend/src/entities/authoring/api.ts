import { queryOptions } from '@tanstack/react-query';
import type { HttpClient } from '@/shared/api';
import { roleSchema, userSchema } from '@/shared/model/identity';
import type { Role } from '@/shared/model/identity';
import { editorCourseSchema, editorPageSchema, userPageSchema } from './model';
import type { Command } from './model';

export const authoringKey = (id: number) => ['private', 'authoring', 'course', id] as const;
export function createAuthoringGateway(http: HttpClient) {
  return {
    courses(offset: number) {
      return queryOptions({
        queryKey: ['private', 'authoring', 'list', offset],
        staleTime: 0,
        queryFn: async ({ signal }) =>
          editorPageSchema.parse(
            await http.request('/authoring/courses?limit=20&offset=' + offset, {
              authenticated: true,
              signal,
            }),
          ),
      });
    },
    detail(id: number) {
      return queryOptions({
        queryKey: authoringKey(id),
        staleTime: 0,
        enabled: Number.isInteger(id) && id > 0,
        queryFn: async ({ signal }) =>
          editorCourseSchema.parse(
            await http.request('/authoring/courses/' + id, { authenticated: true, signal }),
          ),
      });
    },
    async create(input: { slug: string; title: string; description: string }) {
      return editorCourseSchema.parse(
        await http.request('/authoring/courses', {
          method: 'POST',
          body: input,
          authenticated: true,
        }),
      );
    },
    async command(id: number, revision: number, command: Command) {
      return editorCourseSchema.parse(
        await http.request(`/authoring/courses/${id}${command.path ?? ''}?revision=${revision}`, {
          ...command,
          authenticated: true,
        }),
      );
    },
    users(search: string, offset: number) {
      const params = new URLSearchParams({
        limit: '20',
        offset: String(offset),
        ...(search ? { search } : {}),
      });
      return queryOptions({
        queryKey: ['private', 'admin', 'users', search, offset],
        staleTime: 0,
        queryFn: async ({ signal }) =>
          userPageSchema.parse(
            await http.request('/admin/users?' + params, { authenticated: true, signal }),
          ),
      });
    },
    async setRole(id: number, role: Role) {
      return userSchema.parse(
        await http.request(`/admin/users/${id}/role`, {
          method: 'PUT',
          authenticated: true,
          body: { role: roleSchema.parse(role) },
        }),
      );
    },
  };
}
export type AuthoringGateway = ReturnType<typeof createAuthoringGateway>;
