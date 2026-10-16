import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate } from 'react-router-dom';
import { useAccount } from '@/entities/session';
import { errorMessage } from '@/shared/api';
import { Button, Notice } from '@/shared/ui';
import { loginSchema } from '../model/forms';
import type { LoginValues } from '../model/forms';
export function LoginForm() {
  const { session } = useAccount();
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({ resolver: zodResolver(loginSchema) });
  const submit = handleSubmit(async (values) => {
    setError('');
    try {
      await session.signIn(values);
      navigate('/courses', { replace: true });
    } catch (error) {
      setError(errorMessage(error));
    }
  });
  return (
    <form onSubmit={submit} noValidate>
      <label>
        Электронная почта
        <input
          type="email"
          autoComplete="username"
          {...register('email')}
          aria-invalid={!!errors.email}
          aria-describedby={errors.email ? 'login-email-error' : undefined}
        />
        {errors.email && (
          <span id="login-email-error" className="field-error">
            {errors.email.message}
          </span>
        )}
      </label>
      <label>
        Пароль
        <input
          type="password"
          autoComplete="current-password"
          {...register('password')}
          aria-invalid={!!errors.password}
          aria-describedby={errors.password ? 'login-password-error' : undefined}
        />
        {errors.password && (
          <span id="login-password-error" className="field-error">
            {errors.password.message}
          </span>
        )}
      </label>
      {error && <Notice error>{error}</Notice>}
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Входим…' : 'Войти'}
      </Button>
      <Link to="/register">Создать аккаунт</Link>
      <small>После перезагрузки страницы нужно войти заново.</small>
    </form>
  );
}
