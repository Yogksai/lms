import { describe, expect, it, vi } from 'vitest';
import { createHttpClient, HttpError } from './http';
const json = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } });
describe('HTTP transport', () => {
  it('sends JSON and uses the same-origin API path', async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(json({ id: 1 }));
    const client = createHttpClient(fetcher);
    expect(await client.request('/auth/login', { method: 'POST', body: { email: 'a' } })).toEqual({
      id: 1,
    });
    expect(fetcher.mock.calls[0]?.[0]).toBe('/v1/auth/login');
    expect(fetcher.mock.calls[0]?.[1]?.credentials).toBe('omit');
  });
  it('handles logout without parsing an empty body', async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 204 }));
    expect(
      await createHttpClient(fetcher).request('/auth/logout', { method: 'POST' }),
    ).toBeUndefined();
  });
  it('retries authenticated requests only once after a 401', async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json({ id: 1 }));
    const bridge = {
      accessToken: () => 'old',
      recover: vi.fn().mockResolvedValue('new'),
      invalidate: vi.fn(),
    };
    const client = createHttpClient(fetcher);
    client.authorize(bridge);
    await client.request('/auth/me', { authenticated: true });
    expect(bridge.recover).toHaveBeenCalledWith('old');
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(fetcher.mock.calls[1]?.[1]?.headers).toMatchObject({ Authorization: 'Bearer new' });
  });
  it('invalidates the session after a second 401', async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(json({}, 401));
    const bridge = {
      accessToken: () => 'old',
      recover: vi.fn().mockResolvedValue('new'),
      invalidate: vi.fn(),
    };
    const client = createHttpClient(fetcher);
    client.authorize(bridge);
    await expect(client.request('/auth/me', { authenticated: true })).rejects.toBeInstanceOf(
      HttpError,
    );
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(bridge.invalidate).toHaveBeenCalledOnce();
  });
  it('never retries login or refresh requests', async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(json({}, 401));
    const client = createHttpClient(fetcher);
    await expect(
      client.request('/auth/refresh', { method: 'POST', body: { refresh_token: 'token' } }),
    ).rejects.toBeInstanceOf(HttpError);
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('does not send a protected request without a local token', async () => {
    const fetcher = vi.fn<typeof fetch>();
    const client = createHttpClient(fetcher);
    await expect(client.request('/auth/me', { authenticated: true })).rejects.toBeInstanceOf(
      HttpError,
    );
    expect(fetcher).not.toHaveBeenCalled();
  });
});
