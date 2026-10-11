import { z } from 'zod';
const lessonOutline = z.object({
  id: z.number().int().positive(),
  module_id: z.number().int().positive(),
  title: z.string(),
  position: z.number().int().positive(),
});
const moduleSchema = z.object({
  id: z.number().int().positive(),
  course_id: z.number().int().positive(),
  title: z.string(),
  description: z.string(),
  position: z.number().int().positive(),
  is_preview: z.boolean(),
  lessons: z.array(lessonOutline),
});
export const courseSchema = z.object({
  id: z.number().int().positive(),
  slug: z.string(),
  title: z.string(),
  description: z.string(),
});
export const courseDetailSchema = courseSchema.extend({ modules: z.array(moduleSchema) });
export const coursePageSchema = z.object({
  items: z.array(courseSchema),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
});
export const lessonSchema = lessonOutline.extend({
  summary: z.string(),
  video_url: z.string().url(),
});
export type Course = z.infer<typeof courseSchema>;
export type CourseDetail = z.infer<typeof courseDetailSchema>;
export type Lesson = z.infer<typeof lessonSchema>;
export function youtubeEmbedUrl(value: string): string | null {
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || url.username || url.password || url.port) return null;
    let id: string | null = null;
    if (url.hostname === 'youtu.be') id = url.pathname.slice(1);
    else if (['youtube.com', 'www.youtube.com'].includes(url.hostname)) {
      if (url.pathname === '/watch') id = url.searchParams.get('v');
      else if (/^\/(embed|shorts)\//.test(url.pathname)) id = url.pathname.split('/')[2] ?? null;
    }
    return id && /^[\w-]{11}$/.test(id) ? 'https://www.youtube-nocookie.com/embed/' + id : null;
  } catch {
    return null;
  }
}
