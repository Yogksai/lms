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
    lesson(courseId: number, moduleId: number, lessonId: number) {
      return queryOptions({
        queryKey: ['courses', courseId, 'modules', moduleId, 'lessons', lessonId],
        queryFn: async ({ signal }) =>
          lessonSchema.parse(
            await http.request(
              '/courses/' + courseId + '/modules/' + moduleId + '/lessons/' + lessonId,
              { signal },
            ),
          ),
        enabled: [courseId, moduleId, lessonId].every((id) => Number.isInteger(id) && id > 0),
      });
    },
  };
}
export type CourseQueries = ReturnType<typeof createCourseQueries>;
