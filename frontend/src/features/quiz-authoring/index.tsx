import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  choices,
  questionWriteSchema,
  quizWriteSchema,
  quizKey,
  useQuizGateway,
} from '@/entities/quiz';
import type { Bank, Question, QuestionWrite, QuizWrite } from '@/entities/quiz';
import { useAccount, useCurrentUser } from '@/entities/session';
import { errorMessage, HttpError } from '@/shared/api';
import { Button, Notice } from '@/shared/ui';

function ConfigForm({
  bank,
  disabled,
  save,
}: {
  bank: Bank;
  disabled: boolean;
  save: (data: QuizWrite) => Promise<void>;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<QuizWrite>({
    resolver: zodResolver(quizWriteSchema),
    defaultValues: bank.config ?? {
      question_count: 10,
      passing_score: 70,
      time_limit_seconds: 600,
      enabled: false,
    },
  });
  return (
    <form onSubmit={handleSubmit(save)}>
      <fieldset disabled={disabled}>
        <legend>Настройки теста</legend>
        <label>
          Количество вопросов (1–100)
          <input
            type="number"
            min={1}
            max={100}
            {...register('question_count', { valueAsNumber: true })}
          />
        </label>
        <label>
          Проходной балл, %
          <input
            type="number"
            min={1}
            max={100}
            {...register('passing_score', { valueAsNumber: true })}
          />
        </label>
        <label>
          Время, секунд (60–7200)
          <input
            type="number"
            min={60}
            max={7200}
            {...register('time_limit_seconds', { valueAsNumber: true })}
          />
        </label>
        <label className="check-label">
          <input type="checkbox" {...register('enabled')} />
          Тест доступен студентам после публикации курса
        </label>
        {Object.entries(errors).map(([name, error]) => (
          <span role="alert" key={name}>
            {error?.message}
          </span>
        ))}
        <Button type="submit">Сохранить настройки</Button>
      </fieldset>
    </form>
  );
}

function QuestionForm({
  bank,
  initial,
  disabled,
  save,
}: {
  bank: Bank;
  initial: Question | null;
  disabled: boolean;
  save: (data: QuestionWrite) => Promise<void>;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<QuestionWrite>({
    resolver: zodResolver(questionWriteSchema),
    defaultValues: initial ?? {
      lesson_id: bank.lessons[0]?.id,
      prompt: '',
      options: { A: '', B: '', C: '', D: '' },
      correct_option: 'A',
      explanation: '',
      is_active: true,
    },
  });
  return (
    <form onSubmit={handleSubmit(save)}>
      <fieldset disabled={disabled || !bank.lessons.length}>
        <legend>{initial ? 'Редактировать вопрос' : 'Новый вопрос'}</legend>
        <label>
          Урок для повторения
          <select {...register('lesson_id', { valueAsNumber: true })}>
            {bank.lessons.map((lesson) => (
              <option key={lesson.id} value={lesson.id}>
                {lesson.title}
              </option>
            ))}
          </select>
        </label>
        <label>
          Вопрос
          <textarea rows={3} maxLength={10000} {...register('prompt')} />
        </label>
        {choices.map((choice) => (
          <label key={choice}>
            Вариант {choice}
            <input maxLength={2000} {...register(`options.${choice}`)} />
            {errors.options?.[choice] && (
              <span role="alert">Вариант обязателен, до 2000 символов.</span>
            )}
          </label>
        ))}
        <label>
          Правильный вариант
          <select {...register('correct_option')}>
            {choices.map((choice) => (
              <option key={choice}>{choice}</option>
            ))}
          </select>
        </label>
        <label>
          Пояснение после сдачи
          <textarea rows={4} maxLength={10000} {...register('explanation')} />
        </label>
        <label className="check-label">
          <input type="checkbox" {...register('is_active')} />
          Включён в случайную выборку
        </label>
        {(errors.lesson_id || errors.prompt || errors.explanation) && (
          <Notice error>Укажи урок, текст вопроса и пояснение (до 10 000 символов).</Notice>
        )}
        <Button type="submit">Сохранить вопрос</Button>
      </fieldset>
    </form>
  );
}

type Command =
  | { type: 'config'; data: QuizWrite }
  | { type: 'question'; data: QuestionWrite; id?: number }
  | { type: 'archive'; id: number };
export function QuizEditor({
  bank,
  courseId,
  reload,
}: {
  bank: Bank;
  courseId: number;
  reload: () => void;
}) {
  const [selected, setSelected] = useState<Question | null>(null);
  const user = useCurrentUser();
  const { session } = useAccount();
  const gateway = useQuizGateway();
  const client = useQueryClient();
  const revision = bank.config?.revision ?? 0;
  const command = useMutation({
    mutationFn: async (input: Command) => {
      const identity = session.identityVersion();
      if (input.type === 'config')
        await gateway.configure(courseId, bank.module_id, revision, input.data);
      else if (input.type === 'archive')
        await gateway.archive(courseId, bank.module_id, revision, input.id);
      else await gateway.saveQuestion(courseId, bank.module_id, revision, input.data, input.id);
      if (identity !== session.identityVersion()) return;
      await client.invalidateQueries({ queryKey: quizKey(user?.id ?? 0, courseId) });
      setSelected(null);
    },
  });
  const disabled = bank.course_status !== 'draft' || command.isPending;
  const run = async (input: Command) => {
    try {
      await command.mutateAsync(input);
    } catch {
      /* Mutation state renders the error without discarding the form. */
    }
  };
  return (
    <>
      <p>
        Активных вопросов: {bank.active_questions}. Версия теста: {revision}.
      </p>
      <p>
        Изменения доступны только в черновике. Сохранение обновит формы; уже начатые попытки
        сохраняют прежние вопросы и настройки.
      </p>
      {bank.course_status !== 'draft' && (
        <Notice>Верни курс в черновик, чтобы редактировать тест.</Notice>
      )}
      {command.isError && (
        <Notice error>
          {command.error instanceof HttpError && command.error.status === 409
            ? 'Версия изменилась или курс не в черновике. Обнови данные перед повторным сохранением.'
            : errorMessage(command.error)}
        </Notice>
      )}
      {command.isSuccess && <Notice>Сохранено.</Notice>}
      <Button disabled={command.isPending} onClick={reload}>
        Обновить данные и сбросить формы
      </Button>
      <section className="authoring-card">
        <h2>Параметры</h2>
        <ConfigForm
          key={revision}
          bank={bank}
          disabled={disabled}
          save={(data) => run({ type: 'config', data })}
        />
      </section>
      <section className="authoring-card">
        <h2>Банк вопросов</h2>
        {!bank.config && (
          <Notice>
            Сначала сохрани настройки с выключенным тестом, затем добавь вопросы и включи тест.
          </Notice>
        )}
        {!bank.lessons.length && <Notice>Сначала добавь уроки в модуль.</Notice>}
        <ul className="authoring-list">
          {bank.items.map((item) => (
            <li key={item.id} className="authoring-row">
              <span>
                {item.prompt} · {item.lesson_title} · {item.is_active ? 'активен' : 'архив'}
              </span>
              <div className="actions">
                <Button disabled={disabled} onClick={() => setSelected(item)}>
                  Изменить #{item.id}
                </Button>
                <Button
                  disabled={disabled || !item.is_active}
                  onClick={() => {
                    if (window.confirm('Убрать вопрос из будущих попыток?'))
                      void run({ type: 'archive', id: item.id });
                  }}
                >
                  Архивировать
                </Button>
              </div>
            </li>
          ))}
        </ul>
        {selected && (
          <Button disabled={command.isPending} onClick={() => setSelected(null)}>
            К новому вопросу
          </Button>
        )}
        <QuestionForm
          key={`${revision}-${selected?.id ?? 'new'}`}
          bank={bank}
          initial={selected}
          disabled={disabled || !bank.config}
          save={(data) => run({ type: 'question', data, id: selected?.id })}
        />
      </section>
    </>
  );
}
