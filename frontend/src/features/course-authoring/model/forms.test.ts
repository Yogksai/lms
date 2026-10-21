import { describe, expect, it } from 'vitest';
import { courseFormSchema, moduleFormSchema, lessonFormSchema, moveItem } from './forms';
describe('authoring validation and ordering', () => {
  it('trims titles and requires safe unique-style slugs', () => {
    expect(
      courseFormSchema.parse({ title: ' Title ', slug: 'math-1', description: ' Text ' }),
    ).toEqual({ title: 'Title', slug: 'math-1', description: 'Text' });
    expect(
      courseFormSchema.safeParse({ title: 'Title', slug: 'Bad Slug', description: '' }).success,
    ).toBe(false);
  });
  it('rejects blank module titles', () => {
    expect(moduleFormSchema.safeParse({ title: ' ', description: '' }).success).toBe(false);
  });
  it('rejects arbitrary embed hosts and empty summaries', () => {
    expect(
      lessonFormSchema.safeParse({
        title: 'Title',
        summary: 'Summary',
        video_url: 'https://evil.example/video',
      }).success,
    ).toBe(false);
    expect(
      lessonFormSchema.safeParse({
        title: 'Title',
        summary: ' ',
        video_url: 'https://youtu.be/dQw4w9WgXcQ',
      }).success,
    ).toBe(false);
    expect(
      lessonFormSchema.safeParse({
        title: 'Title',
        summary: '<script>plain text</script>',
        video_url: 'https://youtu.be/dQw4w9WgXcQ',
      }).success,
    ).toBe(true);
  });
  it('moves siblings without mutating input or dropping IDs', () => {
    const ids = [1, 2, 3];
    expect(moveItem(ids, 2, -1)).toEqual([2, 1, 3]);
    expect(moveItem(ids, 2, 1)).toEqual([1, 3, 2]);
    expect(ids).toEqual([1, 2, 3]);
    expect(moveItem(ids, 1, -1)).toBe(ids);
    expect(moveItem(ids, 3, 1)).toBe(ids);
    expect(moveItem(ids, 99, 1)).toBe(ids);
  });
});
