import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { quizError, useQuizGateway } from '@/entities/quiz';
import { useCurrentUser } from '@/entities/session';
import { QuizStart } from '@/features/quiz-taking';
import { Button, Heading, Notice } from '@/shared/ui';
function Quiz({
  userId,
  courseId,
  moduleId,
}: {
  userId: number;
  courseId: number;
  moduleId: number;
}) {
  const gateway = useQuizGateway();
  const [offset, setOffset] = useState(0);
  const info = useQuery(gateway.info(userId, courseId, moduleId));
  const history = useQuery({
    ...gateway.history(userId, courseId, moduleId, offset),
    enabled: info.isSuccess,
  });
  return (
    <>
      <Link to={`/courses/${courseId}`}>← К курсу</Link>
      <Heading>Тест по модулю</Heading>
      {info.isPending ? (
        <Notice>Загружаем тест…</Notice>
      ) : info.isError ? (
        <Notice error>
          {quizError(info.error)} <Button onClick={() => void info.refetch()}>Повторить</Button>
        </Notice>
      ) : (
        <QuizStart key={`${courseId}-${moduleId}`} info={info.data} courseId={courseId} />
      )}
      <h2>Твои попытки</h2>
      {history.isError ? (
        <Notice error>
          {quizError(history.error)}{' '}
          <Button onClick={() => void history.refetch()}>Повторить</Button>
        </Notice>
      ) : history.data ? (
        <>
          <ul className="authoring-list">
            {history.data.items.map((attempt) => (
              <li className="authoring-row" key={attempt.attempt_id}>
                <Link to={`/courses/${courseId}/attempts/${attempt.attempt_id}`}>
                  {new Date(attempt.started_at).toLocaleString('ru-RU')} ·{' '}
                  {attempt.status === 'in_progress'
                    ? 'Начата'
                    : attempt.status === 'expired'
                      ? 'Время истекло'
                      : `${attempt.score_percent}% · ${attempt.passed ? 'пройден' : 'не пройден'}`}
                </Link>
              </li>
            ))}
          </ul>
          {!history.data.total && <p>Пока нет попыток.</p>}
          <div className="actions">
            <Button disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 20))}>
              Назад
            </Button>
            <span>{history.data.total} попыток</span>
            <Button
              disabled={offset + 20 >= history.data.total}
              onClick={() => setOffset(offset + 20)}
            >
              Далее
            </Button>
          </div>
        </>
      ) : null}
    </>
  );
}
export default function QuizPage() {
  const params = useParams();
  const user = useCurrentUser();
  const courseId = Number(params.courseId),
    moduleId = Number(params.moduleId);
  if (![courseId, moduleId].every((id) => Number.isSafeInteger(id) && id > 0))
    return <Notice error>Некорректный адрес теста.</Notice>;
  if (!user)
    return (
      <Notice>
        Для прохождения теста <Link to="/login">войди в аккаунт</Link>.
      </Notice>
    );
  return (
    <Quiz
      key={`${user.id}-${courseId}-${moduleId}`}
      userId={user.id}
      courseId={courseId}
      moduleId={moduleId}
    />
  );
}
