import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { useCourseQueries } from '@/entities/course';
import { useCurrentUser } from '@/entities/session';
import { CourseAccess } from '@/features/course-access';
import { LessonViewer } from '@/widgets/lesson-viewer';
import { HttpError, errorMessage } from '@/shared/api';
import { Button, Heading, LinkButton, Notice } from '@/shared/ui';
export default function LessonPage() {
  const params = useParams();
  const courseId = Number(params.courseId),
    moduleId = Number(params.moduleId),
    lessonId = Number(params.lessonId);
  const user = useCurrentUser();
  const query = useQuery(useCourseQueries().lesson(courseId, moduleId, lessonId, user?.id));
  const valid = [courseId, moduleId, lessonId].every((id) => Number.isInteger(id) && id > 0);
  if (!valid) return <Notice error>Урок не найден.</Notice>;
  return (
    <>
      <p>
        <LinkButton to={'/courses/' + courseId}>← К курсу</LinkButton>
      </p>
      {query.isPending || (!query.isFetchedAfterMount && query.isFetching) ? (
        <Notice>Загружаем урок…</Notice>
      ) : query.isError ? (
        query.error instanceof HttpError && query.error.status === 403 ? (
          <>
            <Heading>Закрытый урок</Heading>
            <Notice>
              Бесплатно доступен первый модуль. Для остальных модулей нужен действующий полный
              доступ.
            </Notice>
            <CourseAccess courseId={courseId} />
          </>
        ) : (
          <Notice error>
            {errorMessage(query.error)}{' '}
            <Button onClick={() => void query.refetch()}>Повторить</Button>
          </Notice>
        )
      ) : (
        <>
          <Heading>{query.data.title}</Heading>
          <LessonViewer key={query.data.id} lesson={query.data} />
        </>
      )}
    </>
  );
}
