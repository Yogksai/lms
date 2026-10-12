import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { useCourseQueries } from '@/entities/course';
import { CourseOutline } from '@/widgets/course-outline';
import { CourseAccess } from '@/features/course-access';
import { errorMessage } from '@/shared/api';
import { Button, Heading, Notice } from '@/shared/ui';
export default function CoursePage() {
  const { courseId } = useParams();
  const id = Number(courseId);
  const query = useQuery(useCourseQueries().detail(id));
  if (!Number.isInteger(id) || id <= 0) return <Notice error>Курс не найден.</Notice>;
  return (
    <>
      <p>
        <Link to="/courses">← Все курсы</Link>
      </p>
      {query.isPending ? (
        <Notice>Загружаем курс…</Notice>
      ) : query.isError ? (
        <Notice error>
          {errorMessage(query.error)}{' '}
          <Button onClick={() => void query.refetch()}>Повторить</Button>
        </Notice>
      ) : (
        <>
          <Heading>{query.data.title}</Heading>
          <p>{query.data.description}</p>
          <p>
            <small>
              Количество модулей: {query.data.modules.length}. Первый модуль доступен бесплатно.
            </small>
          </p>
          {query.data.modules.length ? (
            <CourseAccess
              courseId={id}
              outline={(fullAccess) => (
                <CourseOutline course={query.data} fullAccess={fullAccess} />
              )}
            />
          ) : (
            <Notice>Материалы курса пока не добавлены.</Notice>
          )}
        </>
      )}
    </>
  );
}
