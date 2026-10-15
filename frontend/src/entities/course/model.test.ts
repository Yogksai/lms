import { describe, expect, it } from 'vitest';
import { coursePageSchema, youtubeEmbedUrl } from './model';
describe('course contracts and videos', () => {
  it('validates API responses at the boundary', () => {
    expect(coursePageSchema.safeParse({ items: [], total: 0, limit: 10, offset: 0 }).success).toBe(
      true,
    );
    expect(
      coursePageSchema.safeParse({ items: [{ id: 'wrong' }], total: 1, limit: 10, offset: 0 })
        .success,
    ).toBe(false);
  });
  it.each([
    'https://www.youtube.com/watch?v=rfscVS0vtbw',
    'https://youtu.be/rfscVS0vtbw',
    'https://youtube.com/shorts/rfscVS0vtbw',
  ])('maps a YouTube guide to a privacy-enhanced player: %s', (url) => {
    expect(youtubeEmbedUrl(url)).toBe('https://www.youtube-nocookie.com/embed/rfscVS0vtbw');
  });
  it.each([
    'https://evil.test/watch?v=rfscVS0vtbw',
    'http://youtube.com/watch?v=rfscVS0vtbw',
    'https://youtube.com.evil.test/watch?v=rfscVS0vtbw',
    'not a url',
  ])('rejects unsupported video sources: %s', (url) => {
    expect(youtubeEmbedUrl(url)).toBeNull();
  });
});
