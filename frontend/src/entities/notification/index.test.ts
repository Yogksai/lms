import { describe, expect, it } from 'vitest';
import { notificationPageSchema } from './index';
describe('notification contracts', () => {
  it.each(['https://evil.example', 'javascript:alert(1)', '//evil.example', '/admin/users'])(
    'rejects unexpected notification link %s',
    (link) => {
      expect(
        notificationPageSchema.safeParse({
          items: [
            {
              id: 1,
              title: 'Result',
              message: 'Math',
              link,
              created_at: '2026-10-22T00:00:00Z',
              read_at: null,
            },
          ],
          total: 1,
          limit: 20,
          offset: 0,
        }).success,
      ).toBe(false);
    },
  );
});
