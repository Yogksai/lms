import { useEffect, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { choices, quizError, quizKey, useQuizGateway } from '@/entities/quiz';
import type { Attempt, Choice, QuizInfo } from '@/entities/quiz';
import { useAccount, useCurrentUser } from '@/entities/session';
import { Button, Notice } from '@/shared/ui';

export function QuizStart({ info, courseId }: { info: QuizInfo; courseId: number }) {
  const gateway = useQuizGateway();
  const { session } = useAccount();
  const navigate = useNavigate();
  const start = useMutation({
    mutationFn: async () => {
      const identity = session.identityVersion();
      const attempt = await gateway.start(courseId, info.module_id);
      if (identity === session.identityVersion())
        void navigate(`/courses/${courseId}/attempts/${attempt.attempt_id}`);
    },
  });
  return (
    <section className="authoring-card">
      <h2>Тест по модулю</h2>
      <p>
        {info.question_count} вопросов · {Math.round(info.time_limit_seconds / 60)} мин. · проходной
        балл {info.passing_score}%.
      </p>
      <p>
        Новых попыток сегодня: {info.remaining_today} из {info.daily_limit}. Обновление лимита:{' '}
        {new Date(info.reset_at).toLocaleString('ru-RU', { timeZone: info.timezone })} (
        {info.timezone}).
      </p>
      <p>
        Вопросы выбираются случайно. После сдачи появятся правильные ответы, пояснения и уроки для
        повторения. Пропущенные ответы считаются неверными.
      </p>
      {info.open_attempt ? (
        <Link to={`/courses/${courseId}/attempts/${info.open_attempt}`}>
          Продолжить начатую попытку
        </Link>
      ) : (
        <Button
          disabled={!info.available || !info.remaining_today || start.isPending}
          onClick={() => start.mutate()}
        >
          {start.isPending ? 'Создаём попытку…' : 'Начать тест'}
        </Button>
      )}
      {!info.available && !info.open_attempt && (
        <Notice>
          Преподаватель пока не включил тест или в банке недостаточно активных вопросов.
        </Notice>
      )}
      {start.isError && (
        <Notice error>
          {quizError(start.error)} Обнови страницу, чтобы проверить наличие начатой попытки.
        </Notice>
      )}
    </section>
  );
}

function Deadline({ attempt }: { attempt: Attempt }) {
  const [clock] = useState(() => ({ server: Date.parse(attempt.server_time), local: Date.now() }));
  const [now, setNow] = useState(Date.now);
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  const seconds = Math.max(
    0,
    Math.ceil((Date.parse(attempt.deadline_at) - clock.server - (now - clock.local)) / 1000),
  );
  return (
    <p role="timer" aria-live="off">
      Осталось примерно {Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, '0')}.
      Окончательный срок проверяет сервер.
    </p>
  );
}

export function AttemptForm({ attempt }: { attempt: Attempt }) {
  const [answers, setAnswers] = useState<Record<string, Choice>>({ ...attempt.answers });
  const gateway = useQuizGateway();
  const client = useQueryClient();
  const user = useCurrentUser();
  const { session } = useAccount();
  const submit = useMutation({
    mutationFn: async () => {
      const identity = session.identityVersion();
      const result = await gateway.submit(attempt.course_id, attempt.attempt_id, answers);
      if (identity !== session.identityVersion()) return;
      client.setQueryData(
        gateway.attempt(user?.id ?? 0, attempt.course_id, attempt.attempt_id).queryKey,
        result,
      );
      await client.invalidateQueries({
        queryKey: quizKey(user?.id ?? 0, attempt.course_id),
        predicate: (query) => !query.queryKey.includes('attempt'),
      });
    },
  });
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        if (
          window.confirm(
            `Сдать тест? Ответов выбрано: ${Object.keys(answers).length} из ${attempt.questions.length}. После сдачи изменить ответы нельзя.`,
          )
        )
          submit.mutate();
      }}
    >
      <Deadline attempt={attempt} />
      <Notice>
        Ответы сохраняются только при сдаче. Перезагрузка или уход со страницы сбросят несданные
        ответы; время продолжит идти.
      </Notice>
      <fieldset disabled={submit.isPending}>
        <legend>Выбери один ответ для каждого вопроса</legend>
        {attempt.questions.map((question, index) => (
          <fieldset className="authoring-card" key={question.question_id}>
            <legend>
              {index + 1}. {question.prompt}
            </legend>
            <div className="quiz-options">
              {choices.map((choice) => (
                <label key={choice} className="quiz-option">
                  <input
                    type="radio"
                    name={`question-${question.question_id}`}
                    value={choice}
                    checked={answers[question.question_id] === choice}
                    onChange={() =>
                      setAnswers((previous) => ({ ...previous, [question.question_id]: choice }))
                    }
                  />
                  <span>
                    {choice}. {question.options[choice]}
                  </span>
                </label>
              ))}
            </div>
          </fieldset>
        ))}
        <p>
          Отвечено: {Object.keys(answers).length} / {attempt.questions.length}
        </p>
        <Button type="submit">{submit.isPending ? 'Проверяем…' : 'Сдать тест'}</Button>
      </fieldset>
      {submit.isError && (
        <Notice error>
          {quizError(submit.error)} Ответы остались в форме. При сетевой ошибке можно повторить
          сдачу с теми же ответами.
        </Notice>
      )}
    </form>
  );
}

export function AttemptReview({ attempt }: { attempt: Attempt }) {
  const result = attempt.result;
  if (!result)
    return (
      <Notice>
        Срок попытки истёк. Ответы не оценены; можно начать новую попытку при наличии дневного
        лимита.
      </Notice>
    );
  return (
    <>
      <section className="authoring-card">
        <h2>{result.passed ? 'Тест пройден' : 'Нужно повторить материал'}</h2>
        <p>
          {result.correct_count} из {result.total} · {result.score_percent}% · проходной балл{' '}
          {attempt.passing_score}%
        </p>
      </section>
      {result.review_lessons.length > 0 && (
        <section>
          <h2>Что повторить</h2>
          <ul>
            {result.review_lessons.map((lesson, index) => (
              <li key={`${lesson.lesson_id}-${index}`}>
                {lesson.lesson_id && attempt.module_id ? (
                  <Link
                    to={`/courses/${attempt.course_id}/modules/${attempt.module_id}/lessons/${lesson.lesson_id}`}
                  >
                    {lesson.title}
                  </Link>
                ) : (
                  <span>{lesson.title} (урок больше недоступен)</span>
                )}{' '}
                · ошибок: {lesson.wrong_answers}
              </li>
            ))}
          </ul>
        </section>
      )}
      <h2>Разбор твоей попытки</h2>
      {result.questions.map((question, index) => (
        <section className="authoring-card quiz-result" key={question.question_id}>
          <h3>
            {index + 1}. {question.prompt}
          </h3>
          <p>
            {question.is_correct ? 'Верно' : 'Неверно'}. Твой ответ:{' '}
            {question.selected_option
              ? `${question.selected_option}. ${question.options[question.selected_option]}`
              : 'не выбран'}
            .
          </p>
          <p>
            Правильный ответ: {question.correct_option}. {question.options[question.correct_option]}
          </p>
          <p>{question.explanation}</p>
        </section>
      ))}
    </>
  );
}
