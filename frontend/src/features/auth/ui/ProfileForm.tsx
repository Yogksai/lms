import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useAccount } from '@/entities/session';
import { errorMessage } from '@/shared/api';
import { Button, Notice } from '@/shared/ui';
import { profileSchema } from '../model/forms';
import type { ProfileValues } from '../model/forms';
export function ProfileForm({ name }: { name: string }) {
  const { session } = useAccount();
  const [message, setMessage] = useState('');
  const [failed, setFailed] = useState(false);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ProfileValues>({ resolver: zodResolver(profileSchema), defaultValues: { name } });
  const submit = handleSubmit(async (values) => {
    setMessage('');
    try {
      const user = await session.updateName(values.name);
      reset({ name: user.name });
      setFailed(false);
      setMessage('Имя сохранено.');
    } catch (error) {
      setFailed(true);
      setMessage(errorMessage(error));
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
          aria-describedby={errors.name ? 'profile-name-error' : undefined}
        />
        {errors.name && (
          <span id="profile-name-error" className="field-error">
            {errors.name.message}
          </span>
        )}
      </label>
      {message && <Notice error={failed}>{message}</Notice>}
      <Button type="submit" disabled={isSubmitting}>
        Сохранить имя
      </Button>
    </form>
  );
}
