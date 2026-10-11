import { HttpError } from '@/shared/api';
import type { AccountGateway, TokenPair, User } from './contracts';
export class SessionManager {
  private pair: TokenPair | null = null;
  private user: User | null = null;
  private epoch = 0;
  private pending: Promise<string> | null = null;
  private listeners = new Set<() => void>();
  constructor(
    private readonly gateway: AccountGateway,
    private readonly clearPrivateData: () => void,
  ) {}
  snapshot = (): User | null => this.user;
  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };
  private publish() {
    for (const listener of this.listeners) listener();
  }
  accessToken = () => this.pair?.access_token ?? null;
  invalidate = () => {
    this.epoch++;
    this.pair = null;
    this.user = null;
    this.pending = null;
    this.clearPrivateData();
    this.publish();
  };
  async signIn(input: { email: string; password: string }) {
    this.invalidate();
    const epoch = this.epoch;
    const pair = await this.gateway.login(input);
    if (epoch !== this.epoch) {
      await this.gateway.logout(pair.refresh_token).catch(() => undefined);
      return;
    }
    this.pair = pair;
    try {
      const user = await this.gateway.me();
      if (epoch !== this.epoch) return;
      if (!user.is_active) throw new HttpError(401, 'Аккаунт недоступен');
      this.user = user;
      this.publish();
    } catch (error) {
      if (epoch === this.epoch) {
        this.invalidate();
        await this.gateway.logout(pair.refresh_token).catch(() => undefined);
      }
      throw error;
    }
  }
  recover = async (failedToken: string): Promise<string> => {
    if (!this.pair) throw new HttpError(401, 'Сессия завершена');
    if (this.pair.access_token !== failedToken) return this.pair.access_token;
    if (this.pending) return this.pending;
    const epoch = this.epoch;
    const refreshToken = this.pair.refresh_token;
    const pending = this.gateway
      .refresh(refreshToken)
      .then((pair) => {
        if (epoch !== this.epoch) throw new HttpError(401, 'Сессия завершена');
        this.pair = pair;
        return pair.access_token;
      })
      .catch((error) => {
        if (epoch === this.epoch) this.invalidate();
        throw error;
      })
      .finally(() => {
        if (this.pending === pending) this.pending = null;
      });
    this.pending = pending;
    return pending;
  };
  async signOut() {
    const token = this.pair?.refresh_token;
    this.invalidate();
    if (token) await this.gateway.logout(token);
  }
  async updateName(name: string) {
    const epoch = this.epoch;
    const user = await this.gateway.updateName(name);
    if (epoch !== this.epoch) throw new HttpError(401, 'Сессия завершена');
    this.user = user;
    this.publish();
    return user;
  }
  async reloadProfile() {
    const epoch = this.epoch;
    const user = await this.gateway.me();
    if (epoch !== this.epoch) throw new HttpError(401, 'Сессия завершена');
    if (!user.is_active) throw new HttpError(401, 'Аккаунт недоступен');
    this.user = user;
    this.publish();
    return user;
  }
}
