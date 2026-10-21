import { describe, expect, it, vi } from 'vitest';
import { createAuthoringGateway } from './api';
import { editorCourseSchema } from './model';
import type { HttpClient } from '@/shared/api';
const course = {
  id: 1,
  title: 'Math',
  slug: 'math',
  description: '',
  status: 'draft',
  revision: 2,
  modules: [],
  teachers: [],
};
describe('authoring gateway', () => {
  it('sends authenticated commands with the expected revision', async () => {
    const request = vi.fn().mockResolvedValue(course);
    const gateway = createAuthoringGateway({ request, authorize: vi.fn() } as HttpClient);
    await gateway.command(1, 1, { path: '/modules/order', method: 'PUT', body: { ids: [3, 2] } });
    expect(request).toHaveBeenCalledWith(
      '/authoring/courses/1/modules/order?revision=1',
      expect.objectContaining({ authenticated: true, method: 'PUT', body: { ids: [3, 2] } }),
    );
  });
  it('rejects malformed lifecycle and revision contracts', () => {
    expect(editorCourseSchema.safeParse({ ...course, status: 'deleted' }).success).toBe(false);
    expect(editorCourseSchema.safeParse({ ...course, revision: 0 }).success).toBe(false);
  });
});
