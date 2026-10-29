import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useQuizGateway } from '@/entities/quiz';
import { useAccount, useCurrentUser } from '@/entities/session';
import { errorMessage } from '@/shared/api';
import { Button, Notice } from '@/shared/ui';

export function CourseProgress({ courseId }: { courseId: number }) {
  const user = useCurrentUser();
  const query = useQuery({
    ...useQuizGateway().progress(user?.id ?? 0, courseId),
    enabled: !!user,
  });
  if (!user) return null;
  if (query.isPending) return <Notice>Загружаем прогресс…</Notice>;
  if (query.isError)
    return (
      <Notice error>
        {errorMessage(query.error)}{' '}
        <Button onClick={() => void query.refetch()}>Обновить прогресс</Button>
      </Notice>
    );
  const progress = query.data;
  return (
    <section className="authoring-card">
      <h2>Твой прогресс</h2>
      <label>
        Пройдено тестов: {progress.passed_modules} / {progress.module_count}
        <progress className="learning-meter" value={progress.quiz_percent} max={100} />
      </label>
      <p>
        Уроков отмечено: {progress.completed_lessons} / {progress.lesson_count} (
        {progress.lesson_percent}%).
      </p>
      <p>
        {progress.complete
          ? 'Курс пройден!'
          : 'Для завершения курса нужно сдать тест каждого модуля. Отметки о прочтении уроков учитываются отдельно.'}
      </p>
      <ul>
        {progress.modules.map((module) => (
          <li key={module.module_id}>
            {module.title}:{' '}
            {module.quiz_passed
              ? 'тест пройден'
              : module.quiz_enabled
                ? 'тест ещё не пройден'
                : 'тест пока не включён'}
            {module.best_score !== null && ` · лучший результат ${module.best_score}%`}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Completion({
  courseId,
  moduleId,
  lessonId,
  userId,
}: {
  courseId: number;
  moduleId: number;
  lessonId: number;
  userId: number;
}) {
  const gateway = useQuizGateway();
  const { session } = useAccount();
  const client = useQueryClient();
  const options = gateway.progress(userId, courseId);
  const query = useQuery(options);
  const completed =
    query.data?.modules
      .find((module) => module.module_id === moduleId)
      ?.completed_lesson_ids.includes(lessonId) ?? false;
  const mutation = useMutation({
    mutationFn: async () => {
      const identity = session.identityVersion();
      const progress = await gateway.completeLesson(courseId, moduleId, lessonId, !completed);
      if (identity === session.identityVersion()) client.setQueryData(options.queryKey, progress);
    },
  });
  return (
    <section className="authoring-card">
      <h2>Изучение урока</h2>
      {query.isError ? (
        <Notice error>
          {errorMessage(query.error)}{' '}
          <Button onClick={() => void query.refetch()}>Повторить</Button>
        </Notice>
      ) : (
        <Button disabled={query.isPending || mutation.isPending} onClick={() => mutation.mutate()}>
          {completed ? 'Урок изучен — снять отметку' : 'Отметить урок изученным'}
        </Button>
      )}
      {mutation.isError && <Notice error>{errorMessage(mutation.error)}</Notice>}
      <p>
        <Link to={`/courses/${courseId}/modules/${moduleId}/quiz`}>Перейти к тесту по модулю</Link>
      </p>
      <small>Отметка о прочтении не заменяет сдачу теста.</small>
    </section>
  );
}
export function LessonCompletion({
  courseId,
  moduleId,
  lessonId,
}: {
  courseId: number;
  moduleId: number;
  lessonId: number;
}) {
  const user = useCurrentUser();
  if (!user)
    return (
      <Notice>
        <Link to="/login">Войди</Link>, чтобы сохранять прогресс и проходить тесты.
      </Notice>
    );
  return (
    <Completion
      key={`${user.id}-${courseId}-${moduleId}-${lessonId}`}
      userId={user.id}
      courseId={courseId}
      moduleId={moduleId}
      lessonId={lessonId}
    />
  );
}
