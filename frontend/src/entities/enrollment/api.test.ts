import { QueryClient } from '@tanstack/react-query';
import { describe, expect, it, vi } from 'vitest';
import { createEnrollmentGateway, accessKey } from './api';
describe('enrollment gateway', () => {
  it('uses authenticated private access keys scoped to user and course', async () => {
    const request = vi.fn().mockResolvedValue({
      course_id: 10,
      available: true,
      enrolled: false,
      full_access: false,
      reasons: [],
      expires_at: null,
      request: null,
      grants: [],
    });
    const gateway = createEnrollmentGateway({ request, authorize: vi.fn() });
    const client = new QueryClient();
    await client.fetchQuery(gateway.status(10, 1));
    expect(request).toHaveBeenCalledWith(
      '/courses/10/access',
      expect.objectContaining({ authenticated: true }),
    );
    expect(gateway.status(10, 1).queryKey).toEqual(accessKey(10, 1));
    expect(gateway.status(10, 1).queryKey).not.toEqual(gateway.status(10, 2).queryKey);
    client.clear();
  });
  it('requests all history explicitly instead of falling back to pending', async () => {
    const request = vi.fn().mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
    const client = new QueryClient();
    await client.fetchQuery(
      createEnrollmentGateway({ request, authorize: vi.fn() }).requests(10, 'all', 0),
    );
    expect(request.mock.calls[0]![0]).toContain('status=all');
    client.clear();
  });
  it('sends mutations only as authenticated commands', async () => {
    const request = vi.fn().mockResolvedValue(undefined);
    await createEnrollmentGateway({ request, authorize: vi.fn() }).command({
      path: '/courses/10/enrollment',
      method: 'POST',
    });
    expect(request).toHaveBeenCalledWith(
      '/courses/10/enrollment',
      expect.objectContaining({ authenticated: true, method: 'POST' }),
    );
  });
});
