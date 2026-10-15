import type { HttpClient } from '@/shared/api';
import { tokenPairSchema, userSchema } from './model/contracts';
import type { AccountGateway } from './model/contracts';
export function createAccountGateway(http: HttpClient): AccountGateway {
  return {
    login: async (input) =>
      tokenPairSchema.parse(await http.request('/auth/login', { method: 'POST', body: input })),
    register: async (input) =>
      userSchema.parse(await http.request('/auth/register', { method: 'POST', body: input })),
    refresh: async (token) =>
      tokenPairSchema.parse(
        await http.request('/auth/refresh', { method: 'POST', body: { refresh_token: token } }),
      ),
    logout: async (token) => {
      await http.request('/auth/logout', { method: 'POST', body: { refresh_token: token } });
    },
    me: async () => userSchema.parse(await http.request('/auth/me', { authenticated: true })),
    updateName: async (name) =>
      userSchema.parse(
        await http.request('/auth/me', { method: 'PATCH', body: { name }, authenticated: true }),
      ),
  };
}
