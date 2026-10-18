import { z } from 'zod';

export const roleSchema = z.enum(['student', 'teacher', 'admin']);
export const userSchema = z.object({
  id: z.number().int().positive(),
  name: z.string(),
  email: z.string().email(),
  is_active: z.boolean(),
  role: roleSchema,
});
export type Role = z.infer<typeof roleSchema>;
