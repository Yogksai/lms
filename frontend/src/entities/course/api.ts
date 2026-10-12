import { queryOptions } from '@tanstack/react-query';
import type { HttpClient } from '@/shared/api';
import { courseDetailSchema, coursePageSchema, lessonSchema } from './model';
export function createCourseQueries(http: HttpClient) {
  return {
    catalog(search: string, offset: number) {
      return queryOptions({
        queryKey: ['courses', 'catalog', search, offset],
        queryFn: async ({ signal }) => {
          const params = new URLSearchParams({
            limit: '10',
            offset: String(offset),
            ...(search ? { search } : {}),
          });
          return coursePageSchema.parse(await http.request('/courses?' + params, { signal }));
        },
      });
    },
    detail(id: number) {
      return queryOptions({
        queryKey: ['courses', id],
        queryFn: async ({ signal }) =>
          courseDetailSchema.parse(await http.request('/courses/' + id, { signal })),
        enabled: Number.isInteger(id) && id > 0,
      });
    },
    lesson(courseId: number, moduleId: number, lessonId: number, userId?: number) {
      return queryOptions({
        queryKey: userId
          ? ['private', 'lesson', userId, courseId, moduleId, lessonId]
          : ['courses', courseId, 'modules', moduleId, 'lessons', lessonId],
        staleTime: 0,
        retry: false,
        refetchInterval: userId ? 30000 : false,
        queryFn: async ({ signal }) =>
          lessonSchema.parse(
            await http.request(
              '/courses/' + courseId + '/modules/' + moduleId + '/lessons/' + lessonId,
              { signal, authenticated: !!userId },
            ),
          ),
        enabled: [courseId, moduleId, lessonId].every((id) => Number.isInteger(id) && id > 0),
      });
    },
  };
}
export type CourseQueries = ReturnType<typeof createCourseQueries>;
