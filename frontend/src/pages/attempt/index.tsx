import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { useQuizGateway } from '@/entities/quiz';
import { useCurrentUser } from '@/entities/session';
import { AttemptForm, AttemptReview } from '@/features/quiz-taking';
import { errorMessage } from '@/shared/api';
import { Button, Heading, Notice } from '@/shared/ui';
function Attempt({
  userId,
  courseId,
  attemptId,
}: {
  userId: number;
  courseId: number;
  attemptId: string;
}) {
  const query = useQuery({
    ...useQuizGateway().attempt(userId, courseId, attemptId),
    refetchOnWindowFocus: false,
  });
  if (query.isPending || (!query.isFetchedAfterMount && query.isFetching))
    return <Notice>Загружаем попытку…</Notice>;
  if (query.isError)
    return (
      <Notice error>
        {errorMessage(query.error)} <Button onClick={() => void query.refetch()}>Повторить</Button>
      </Notice>
    );
  const attempt = query.data;
  return (
    <>
      <Link to={`/courses/${courseId}`}>← К курсу</Link>
      <Heading>{attempt.module_title}</Heading>
      {attempt.status === 'in_progress' ? (
        <AttemptForm key={`${userId}-${attemptId}`} attempt={attempt} />
      ) : (
        <AttemptReview attempt={attempt} />
      )}
      {attempt.module_id && (
        <p>
          <Link to={`/courses/${courseId}/modules/${attempt.module_id}/quiz`}>
            Тест и история попыток
          </Link>
        </p>
      )}
    </>
  );
}
export default function AttemptPage() {
  const params = useParams();
  const user = useCurrentUser();
  const courseId = Number(params.courseId);
  const attemptId = params.attemptId ?? '';
  if (
    !Number.isSafeInteger(courseId) ||
    courseId <= 0 ||
    !/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(attemptId)
  )
    return <Notice error>Некорректный адрес попытки.</Notice>;
  if (!user)
    return (
      <Notice>
        <Link to="/login">Войди</Link>, чтобы увидеть свою попытку.
      </Notice>
    );
  return (
    <Attempt
      key={`${user.id}-${courseId}-${attemptId}`}
      userId={user.id}
      courseId={courseId}
      attemptId={attemptId}
    />
  );
}
