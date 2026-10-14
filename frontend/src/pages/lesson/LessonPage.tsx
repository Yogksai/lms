import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { useCourseQueries } from '@/entities/course';
import { LessonViewer } from '@/widgets/lesson-viewer';
import { HttpError, errorMessage } from '@/shared/api';
import { Button, Heading, LinkButton, Notice } from '@/shared/ui';
export default function LessonPage() {
  const params = useParams();
  const courseId = Number(params.courseId),
    moduleId = Number(params.moduleId),
    lessonId = Number(params.lessonId);
  const query = useQuery(useCourseQueries().lesson(courseId, moduleId, lessonId));
  const valid = [courseId, moduleId, lessonId].every((id) => Number.isInteger(id) && id > 0);
  if (!valid) return <Notice error>Урок не найден.</Notice>;
  return (
    <>
      <p>
        <LinkButton to={'/courses/' + courseId}>← К курсу</LinkButton>
      </p>
      {query.isPending ? (
        <Notice>Загружаем урок…</Notice>
      ) : query.isError ? (
        query.error instanceof HttpError && query.error.status === 403 ? (
          <>
            <Heading>Закрытый урок</Heading>
            <Notice>
              Бесплатно доступен первый модуль. Оплата и доступ по одобрению преподавателя появятся
              позднее.
            </Notice>
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
