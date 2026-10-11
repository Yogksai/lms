import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthoringGateway, statusLabels } from '@/entities/authoring';
import { useAccount } from '@/entities/session';
import { HttpError } from '@/shared/api';
import { CourseForm, authoringError } from '@/features/course-authoring';
import { RoleAccess } from '@/features/role-access';
import { Button, Heading, Notice } from '@/shared/ui';

function Catalog() {
  const [offset, setOffset] = useState(0);
  const gateway = useAuthoringGateway();
  const client = useQueryClient();
  const navigate = useNavigate();
  const { session } = useAccount();
  const query = useQuery(gateway.courses(offset));
  const create = useMutation({
    onMutate: () => ({ epoch: session.identityVersion() }),
    mutationFn: async (input: Parameters<typeof gateway.create>[0]) => {
      const epoch = session.identityVersion();
      const course = await gateway.create(input);
      if (session.identityVersion() !== epoch) throw new HttpError(401, 'Session changed');
      return course;
    },
    onSuccess: async (course, _input, context) => {
      await client.invalidateQueries({ queryKey: ['private', 'authoring', 'list'] });
      if (context.epoch !== session.identityVersion()) return;
      navigate('/authoring/courses/' + course.id);
    },
  });
  return (
    <section>
      <Heading>Редактор курсов</Heading>
      <p>
        Преподаватели видят назначенные курсы. Новый курс создаётся как черновик и автоматически
        назначается его автору-преподавателю.
      </p>
      <details className="authoring-card">
        <summary>Создать курс</summary>
        <CourseForm
          initial={{ slug: '', title: '', description: '' }}
          save={(values) => create.mutateAsync(values)}
          submitLabel="Создать черновик"
        />
        {create.isError && <Notice error>{authoringError(create.error)}</Notice>}
      </details>
      {query.isPending ? (
        <Notice>Загружаем курсы…</Notice>
      ) : query.isError ? (
        <Notice error>
          {authoringError(query.error)}{' '}
          <Button onClick={() => void query.refetch()}>Повторить</Button>
        </Notice>
      ) : (
        <>
          {query.data.items.length === 0 && <Notice>Назначенных курсов пока нет.</Notice>}
          <ul className="authoring-list">
            {query.data.items.map((course) => (
              <li key={course.id} className="authoring-card authoring-row">
                <Link to={'/authoring/courses/' + course.id}>{course.title}</Link>
                <span className="authoring-status">{statusLabels[course.status]}</span>
              </li>
            ))}
          </ul>
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
export default function AuthoringCatalogPage() {
  return (
    <RoleAccess>
      <Catalog />
    </RoleAccess>
  );
}
