import { z } from 'zod';
const password = z
  .string()
  .min(8, 'Минимум 8 символов')
  .max(72, 'Максимум 72 символа')
  .refine((value) => new TextEncoder().encode(value).length <= 72, 'Максимум 72 байта UTF-8');
export const loginSchema = z.object({
  email: z.string().trim().email('Введите корректную почту'),
  password: z.string().min(1, 'Введите пароль').max(72, 'Пароль слишком длинный'),
});
export const registerSchema = loginSchema
  .extend({
    name: z.string().trim().min(1, 'Введите имя').max(30, 'Максимум 30 символов'),
    password,
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Пароли не совпадают',
    path: ['confirmPassword'],
  });
export const profileSchema = z.object({
  name: z.string().trim().min(1, 'Введите имя').max(30, 'Максимум 30 символов'),
});
export type LoginValues = z.infer<typeof loginSchema>;
export type RegisterValues = z.infer<typeof registerSchema>;
export type ProfileValues = z.infer<typeof profileSchema>;
