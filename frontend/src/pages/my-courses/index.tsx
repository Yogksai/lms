import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, Navigate } from 'react-router-dom';
import { useEnrollmentGateway } from '@/entities/enrollment';
import { useCurrentUser } from '@/entities/session';
import { CourseAccess, accessError } from '@/features/course-access';
import { Button, Heading, Notice } from '@/shared/ui';
export default function MyCoursesPage() {
  const user = useCurrentUser();
  const gateway = useEnrollmentGateway();
  const [offset, setOffset] = useState(0);
  const [open, setOpen] = useState<number | null>(null);
  const query = useQuery({ ...gateway.mine(user?.id ?? 0, offset), enabled: !!user });
  if (!user) return <Navigate to="/login" replace />;
  return (
    <section>
      <Heading>Мои курсы</Heading>
      <p>Запись сохраняет курс в этом списке. Полный доступ определяется отдельно.</p>
      {query.isPending ? (
        <Notice>Загружаем ваши курсы…</Notice>
      ) : query.isError ? (
        <Notice error>
          {accessError(query.error)} <Button onClick={() => void query.refetch()}>Повторить</Button>
        </Notice>
      ) : (
        <>
          {query.data.items.length === 0 && (
            <Notice>
              Вы ещё не записаны на курсы. <Link to="/courses">Открыть каталог</Link>.
            </Notice>
          )}
          {query.data.items.map(({ course, available }) => (
            <section key={course.id} className="authoring-card">
              <div className="authoring-row">
                {available ? (
                  <Link to={'/courses/' + course.id}>{course.title}</Link>
                ) : (
                  <span>{course.title} · временно недоступен</span>
                )}
                <Button
                  aria-expanded={open === course.id}
                  onClick={() => setOpen(open === course.id ? null : course.id)}
                >
                  Доступ и заявка
                </Button>
              </div>
              {open === course.id && <CourseAccess courseId={course.id} />}
            </section>
          ))}
          <div className="actions">
            <Button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 20))}>
              Назад
            </Button>
            <span>Всего: {query.data.total}</span>
            <Button
              disabled={offset + 20 >= query.data.total}
              onClick={() => setOffset(offset + 20)}
            >
              Далее
            </Button>
          </div>
        </>
      )}
    </section>
  );
}
