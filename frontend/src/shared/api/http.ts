export class HttpError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: unknown,
  ) {
    super(typeof detail === 'string' ? detail : 'Запрос не выполнен');
  }
}
export interface AuthorizationPort {
  accessToken(): string | null;
  recover(failedToken: string): Promise<string>;
  invalidate(): void;
}
type RequestOptions = {
  method?: string;
  body?: unknown;
  authenticated?: boolean;
  signal?: AbortSignal;
};
export interface HttpClient {
  request(path: string, options?: RequestOptions): Promise<unknown>;
  authorize(port: AuthorizationPort): void;
}
export function createHttpClient(fetcher: typeof fetch = (...args) => fetch(...args)): HttpClient {
  let authorization: AuthorizationPort | undefined;
  return {
    authorize(port) {
      authorization = port;
    },
    async request(path, options = {}) {
      const attempt = (token: string | null) =>
        fetcher('/v1' + path, {
          method: options.method || 'GET',
          signal: options.signal
            ? AbortSignal.any([options.signal, AbortSignal.timeout(15000)])
            : AbortSignal.timeout(15000),
          credentials: 'omit',
          headers: {
            Accept: 'application/json',
            ...(options.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
            ...(token ? { Authorization: 'Bearer ' + token } : {}),
          },
          ...(options.body !== undefined ? { body: JSON.stringify(options.body) } : {}),
        });
      const initialToken = options.authenticated ? (authorization?.accessToken() ?? null) : null;
      if (options.authenticated && !initialToken) throw new HttpError(401, 'Войдите в аккаунт');
      let response = await attempt(initialToken);
      if (response.status === 401 && options.authenticated && authorization && initialToken) {
        const replacement = await authorization.recover(initialToken);
        if (options.signal?.aborted) throw new DOMException('Aborted', 'AbortError');
        response = await attempt(replacement);
        if (response.status === 401) authorization.invalidate();
      }
      if (response.status === 204) return undefined;
      const body: unknown = await response.json().catch(() => undefined);
      if (!response.ok) {
        const detail =
          typeof body === 'object' && body !== null && 'detail' in body
            ? body.detail
            : 'Сервис временно недоступен';
        throw new HttpError(response.status, detail);
      }
      return body;
    },
  };
}
export function errorMessage(error: unknown): string {
  if (error instanceof HttpError) {
    if (error.status === 401) return 'Сессия завершена или данные для входа неверны.';
    if (error.status === 409) return 'Аккаунт с этой почтой уже существует.';
    if (error.status === 422) return 'Проверьте заполненные поля.';
    if (error.status === 403) return 'Этот урок недоступен в бесплатном просмотре.';
    if (error.status === 404) return 'Материал не найден.';
  }
  return 'Не удалось связаться с сервером. Проверьте соединение и попробуйте снова.';
}
