import { z } from 'zod';
import { youtubeEmbedUrl } from '@/entities/course';
const title = z.string().trim().min(1, 'Введите название').max(200, 'Максимум 200 символов');
const description = z.string().trim().max(10000, 'Максимум 10 000 символов');
export const moduleFormSchema = z.object({ title, description });
export const courseFormSchema = moduleFormSchema.extend({
  slug: z
    .string()
    .min(1, 'Введите slug')
    .max(100)
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, 'Используйте латиницу, цифры и дефисы'),
});
export const lessonFormSchema = z.object({
  title,
  summary: z.string().trim().min(1, 'Введите конспект').max(100000, 'Максимум 100 000 символов'),
  video_url: z
    .string()
    .max(2048)
    .refine(
      (url) => youtubeEmbedUrl(url) !== null,
      'Введите HTTPS-ссылку на YouTube с корректным ID видео',
    ),
});
export type CourseValues = z.infer<typeof courseFormSchema>;
export type ModuleValues = z.infer<typeof moduleFormSchema>;
export type LessonValues = z.infer<typeof lessonFormSchema>;
export function moveItem(ids: number[], id: number, direction: -1 | 1): number[] {
  const index = ids.indexOf(id);
  const target = index + direction;
  if (index < 0 || target < 0 || target >= ids.length) return ids;
  const result = [...ids];
  [result[index], result[target]] = [result[target]!, result[index]!];
  return result;
}
