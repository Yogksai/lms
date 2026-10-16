import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate } from 'react-router-dom';
import { useAccount } from '@/entities/session';
import { errorMessage } from '@/shared/api';
import { Button, Notice } from '@/shared/ui';
import { registerSchema } from '../model/forms';
import type { RegisterValues } from '../model/forms';
export function RegisterForm() {
  const { gateway } = useAccount();
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterValues>({ resolver: zodResolver(registerSchema) });
  const submit = handleSubmit(async (values) => {
    setError('');
    try {
      await gateway.register({ name: values.name, email: values.email, password: values.password });
      navigate('/login?registered=1', { replace: true });
    } catch (error) {
      setError(errorMessage(error));
    }
  });
  return (
    <form onSubmit={submit} noValidate>
      <label>
        Имя
        <input
          autoComplete="name"
          {...register('name')}
          aria-invalid={!!errors.name}
          aria-describedby={errors.name ? 'register-name-error' : undefined}
        />
        {errors.name && (
          <span id="register-name-error" className="field-error">
            {errors.name.message}
          </span>
        )}
      </label>
      <label>
        Электронная почта
        <input
          type="email"
          autoComplete="username"
          {...register('email')}
          aria-invalid={!!errors.email}
          aria-describedby={errors.email ? 'register-email-error' : undefined}
        />
        {errors.email && (
          <span id="register-email-error" className="field-error">
            {errors.email.message}
          </span>
        )}
      </label>
      <label>
        Пароль
        <input
          type="password"
          autoComplete="new-password"
          {...register('password')}
          aria-invalid={!!errors.password}
          aria-describedby={errors.password ? 'register-password-error' : 'password-help'}
        />
        <small id="password-help">8–72 символа, не более 72 байт UTF-8.</small>
        {errors.password && (
          <span id="register-password-error" className="field-error">
            {errors.password.message}
          </span>
        )}
      </label>
      <label>
        Повторите пароль
        <input
          type="password"
          autoComplete="new-password"
          {...register('confirmPassword')}
          aria-invalid={!!errors.confirmPassword}
          aria-describedby={errors.confirmPassword ? 'register-confirm-error' : undefined}
        />
        {errors.confirmPassword && (
          <span id="register-confirm-error" className="field-error">
            {errors.confirmPassword.message}
          </span>
        )}
      </label>
      {error && <Notice error>{error}</Notice>}
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Создаём аккаунт…' : 'Зарегистрироваться'}
      </Button>
      <Link to="/login">Уже есть аккаунт? Войти</Link>
    </form>
  );
}
