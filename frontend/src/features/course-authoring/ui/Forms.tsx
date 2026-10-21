import { useEffect, useId } from 'react';
import type { ReactNode } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Button } from '@/shared/ui';
import { courseFormSchema, moduleFormSchema, lessonFormSchema } from '../model/forms';
import type { CourseValues, ModuleValues, LessonValues } from '../model/forms';

function useUnsavedChanges(dirty: boolean) {
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);
}
function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: (id: string, errorId: string | undefined) => ReactNode;
}) {
  const id = useId();
  return (
    <label htmlFor={id}>
      {label}
      {children(id, error ? id + '-error' : undefined)}
      {error && (
        <span id={id + '-error'} className="field-error">
          {error}
        </span>
      )}
    </label>
  );
}
type Props<T> = {
  initial: T;
  save: (values: T) => Promise<unknown>;
  disabled?: boolean;
  submitLabel?: string;
};
export function CourseForm({
  initial,
  save,
  disabled = false,
  submitLabel = 'Сохранить курс',
}: Props<CourseValues>) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<CourseValues>({ resolver: zodResolver(courseFormSchema), defaultValues: initial });
  useUnsavedChanges(isDirty);
  const submit = handleSubmit(async (values) => {
    try {
      await save(values);
      reset(values);
    } catch {
      /* Error feedback belongs to the command panel. */
    }
  });
  return (
    <form onSubmit={submit} noValidate>
      <fieldset disabled={disabled || isSubmitting}>
        <Field label="Название курса" error={errors.title?.message}>
          {(id, errorId) => (
            <input
              id={id}
              {...register('title')}
              aria-invalid={!!errors.title}
              aria-describedby={errorId}
            />
          )}
        </Field>
        <Field label="Slug курса" error={errors.slug?.message}>
          {(id, errorId) => (
            <input
              id={id}
              {...register('slug')}
              aria-invalid={!!errors.slug}
              aria-describedby={errorId}
            />
          )}
        </Field>
        <Field label="Описание курса" error={errors.description?.message}>
          {(id, errorId) => (
            <textarea
              id={id}
              rows={3}
              {...register('description')}
              aria-invalid={!!errors.description}
              aria-describedby={errorId}
            />
          )}
        </Field>
        <Button type="submit">{submitLabel}</Button>
      </fieldset>
    </form>
  );
}
export function ModuleForm({
  initial,
  save,
  disabled = false,
  submitLabel = 'Сохранить модуль',
  resetAfterSave = false,
}: Props<ModuleValues> & { resetAfterSave?: boolean }) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<ModuleValues>({ resolver: zodResolver(moduleFormSchema), defaultValues: initial });
  useUnsavedChanges(isDirty);
  const submit = handleSubmit(async (values) => {
    try {
      await save(values);
      reset(resetAfterSave ? { title: '', description: '' } : values);
    } catch {
      /* Keep unsaved input when a command fails. */
    }
  });
  return (
    <form onSubmit={submit} noValidate>
      <fieldset disabled={disabled || isSubmitting}>
        <Field label="Название модуля" error={errors.title?.message}>
          {(id, errorId) => (
            <input
              id={id}
              {...register('title')}
              aria-invalid={!!errors.title}
              aria-describedby={errorId}
            />
          )}
        </Field>
        <Field label="Описание модуля" error={errors.description?.message}>
          {(id, errorId) => (
            <textarea
              id={id}
              rows={2}
              {...register('description')}
              aria-invalid={!!errors.description}
              aria-describedby={errorId}
            />
          )}
        </Field>
        <Button type="submit">{submitLabel}</Button>
      </fieldset>
    </form>
  );
}
export function LessonForm({ initial, save, disabled = false }: Props<LessonValues>) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<LessonValues>({ resolver: zodResolver(lessonFormSchema), defaultValues: initial });
  useUnsavedChanges(isDirty);
  const submit = handleSubmit(async (values) => {
    try {
      await save(values);
      reset(values);
    } catch {
      /* Keep unsaved input when a command fails. */
    }
  });
  return (
    <form onSubmit={submit} noValidate>
      <fieldset disabled={disabled || isSubmitting}>
        <Field label="Название урока" error={errors.title?.message}>
          {(id, errorId) => (
            <input
              id={id}
              {...register('title')}
              aria-invalid={!!errors.title}
              aria-describedby={errorId}
            />
          )}
        </Field>
        <Field label="YouTube видео" error={errors.video_url?.message}>
          {(id, errorId) => (
            <input
              id={id}
              type="url"
              {...register('video_url')}
              aria-invalid={!!errors.video_url}
              aria-describedby={errorId}
            />
          )}
        </Field>
        <Field label="Текст конспекта" error={errors.summary?.message}>
          {(id, errorId) => (
            <textarea
              id={id}
              rows={15}
              {...register('summary')}
              aria-invalid={!!errors.summary}
              aria-describedby={errorId}
            />
          )}
        </Field>
        <small>
          Конспект хранится как обычный текст. HTML не исполняется. Изменения сохраняются только
          после нажатия кнопки.
        </small>
        <Button type="submit">Сохранить урок</Button>
      </fieldset>
    </form>
  );
}
