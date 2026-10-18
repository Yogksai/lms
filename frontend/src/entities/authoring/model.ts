import { z } from 'zod';
import { userSchema } from '@/shared/model/identity';

export const statusSchema = z.enum(['draft', 'published', 'archived']);
const lessonSchema = z.object({
  id: z.number().int().positive(),
  module_id: z.number().int().positive(),
  title: z.string(),
  position: z.number().int().positive(),
  summary: z.string(),
  video_url: z.string().url(),
});
const moduleSchema = z.object({
  id: z.number().int().positive(),
  course_id: z.number().int().positive(),
  title: z.string(),
  description: z.string(),
  position: z.number().int().positive(),
  lessons: z.array(lessonSchema),
});
const summarySchema = z.object({
  id: z.number().int().positive(),
  slug: z.string(),
  title: z.string(),
  description: z.string(),
  status: statusSchema,
  revision: z.number().int().positive(),
});
export const editorCourseSchema = summarySchema.extend({
  modules: z.array(moduleSchema),
  teachers: z.array(userSchema),
});
export const editorPageSchema = z.object({
  items: z.array(summarySchema),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
});
export const userPageSchema = editorPageSchema
  .omit({ items: true })
  .extend({ items: z.array(userSchema) });
export type EditorCourse = z.infer<typeof editorCourseSchema>;
export type EditorModule = z.infer<typeof moduleSchema>;
export type EditorLesson = z.infer<typeof lessonSchema>;
export type Status = z.infer<typeof statusSchema>;
export const statusLabels: Record<Status, string> = {
  draft: 'Черновик',
  published: 'Опубликован',
  archived: 'В архиве',
};
export type Command = { path?: string; method: 'POST' | 'PUT' | 'DELETE'; body?: unknown };
