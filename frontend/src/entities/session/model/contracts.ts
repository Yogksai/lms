import { z } from 'zod';
export const userSchema = z.object({
  id: z.number().int().positive(),
  name: z.string(),
  email: z.string().email(),
  is_active: z.boolean(),
});
export const tokenPairSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string().length(43),
  token_type: z.literal('bearer'),
  expires_in: z.number().positive(),
  refresh_expires_in: z.number().nonnegative(),
});
export type User = z.infer<typeof userSchema>;
export type TokenPair = z.infer<typeof tokenPairSchema>;
export interface AccountGateway {
  login(input: { email: string; password: string }): Promise<TokenPair>;
  register(input: { name: string; email: string; password: string }): Promise<User>;
  refresh(token: string): Promise<TokenPair>;
  logout(token: string): Promise<void>;
  me(): Promise<User>;
  updateName(name: string): Promise<User>;
}
