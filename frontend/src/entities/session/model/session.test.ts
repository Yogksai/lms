import { describe, expect, it, vi } from 'vitest';
import { SessionManager } from './session';
import type { AccountGateway, TokenPair } from './contracts';
const pair: TokenPair = {
  access_token: 'first-access',
  refresh_token: 'a'.repeat(43),
  token_type: 'bearer',
  expires_in: 900,
  refresh_expires_in: 2592000,
};
const user = { id: 1, name: 'Student', email: 'student@example.com', is_active: true };
function setup() {
  const gateway: AccountGateway = {
    login: vi.fn().mockResolvedValue(pair),
    register: vi.fn().mockResolvedValue(user),
    refresh: vi
      .fn()
      .mockResolvedValue({ ...pair, access_token: 'next-access', refresh_token: 'b'.repeat(43) }),
    logout: vi.fn().mockResolvedValue(undefined),
    me: vi.fn().mockResolvedValue(user),
    updateName: vi.fn().mockResolvedValue({ ...user, name: 'Updated' }),
  };
  const clear = vi.fn();
  return { gateway, clear, session: new SessionManager(gateway, clear) };
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
describe('in-memory sessions', () => {
  it('logs in and keeps no persistent browser storage', async () => {
    const { session } = setup();
    await session.signIn({ email: user.email, password: 'password' });
    expect(session.snapshot()).toEqual(user);
    expect(session.accessToken()).toBe(pair.access_token);
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });
  it('shares simultaneous refreshes and uses the newest token for late 401s', async () => {
    const { session, gateway } = setup();
    await session.signIn({ email: user.email, password: 'password' });
    const pending = deferred<TokenPair>();
    vi.mocked(gateway.refresh).mockReturnValue(pending.promise);
    const first = session.recover(pair.access_token);
    const second = session.recover(pair.access_token);
    expect(gateway.refresh).toHaveBeenCalledTimes(1);
    pending.resolve({ ...pair, access_token: 'next-access', refresh_token: 'b'.repeat(43) });
    expect(await first).toBe('next-access');
    expect(await second).toBe('next-access');
    expect(await session.recover(pair.access_token)).toBe('next-access');
    expect(gateway.refresh).toHaveBeenCalledTimes(1);
  });
  it('does not restore identity after logout during refresh', async () => {
    const { session, gateway } = setup();
    await session.signIn({ email: user.email, password: 'password' });
    const pending = deferred<TokenPair>();
    vi.mocked(gateway.refresh).mockReturnValue(pending.promise);
    const recovery = session.recover(pair.access_token);
    const check = expect(recovery).rejects.toThrow();
    await session.signOut();
    pending.resolve({ ...pair, access_token: 'late-access' });
    await check;
    expect(session.snapshot()).toBeNull();
    expect(session.accessToken()).toBeNull();
    expect(gateway.logout).toHaveBeenCalledWith(pair.refresh_token);
  });
  it('clears identity and private data on refresh failure without retry', async () => {
    const { session, gateway, clear } = setup();
    await session.signIn({ email: user.email, password: 'password' });
    vi.mocked(gateway.refresh).mockRejectedValue(new Error('Network'));
    await expect(session.recover(pair.access_token)).rejects.toThrow('Network');
    expect(gateway.refresh).toHaveBeenCalledTimes(1);
    expect(session.snapshot()).toBeNull();
    expect(clear).toHaveBeenCalledTimes(2);
  });
  it('clears local identity even if server logout fails', async () => {
    const { session, gateway } = setup();
    await session.signIn({ email: user.email, password: 'password' });
    vi.mocked(gateway.logout).mockRejectedValue(new Error('Network'));
    await expect(session.signOut()).rejects.toThrow('Network');
    expect(session.snapshot()).toBeNull();
  });
  it('does not accept a disabled account', async () => {
    const { session, gateway } = setup();
    vi.mocked(gateway.me).mockResolvedValue({ ...user, is_active: false });
    await expect(session.signIn({ email: user.email, password: 'password' })).rejects.toThrow();
    expect(session.snapshot()).toBeNull();
    expect(gateway.logout).toHaveBeenCalled();
  });
  it('updates the profile and notifies subscribers', async () => {
    const { session } = setup();
    const listener = vi.fn();
    const unsubscribe = session.subscribe(listener);
    await session.signIn({ email: user.email, password: 'password' });
    await session.updateName('Updated');
    expect(session.snapshot()?.name).toBe('Updated');
    expect(listener).toHaveBeenCalled();
    unsubscribe();
  });
  it('ignores profile responses that arrive after logout', async () => {
    const { session, gateway } = setup();
    await session.signIn({ email: user.email, password: 'password' });
    const pending = deferred<typeof user>();
    vi.mocked(gateway.updateName).mockReturnValue(pending.promise);
    const update = session.updateName('Updated');
    const check = expect(update).rejects.toThrow();
    await session.signOut();
    pending.resolve({ ...user, name: 'Updated' });
    await check;
    expect(session.snapshot()).toBeNull();
  });
  it('a fresh manager has no remembered session', () => {
    expect(setup().session.snapshot()).toBeNull();
  });
});
