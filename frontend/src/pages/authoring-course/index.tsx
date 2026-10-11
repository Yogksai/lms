import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { useAuthoringGateway, statusLabels } from '@/entities/authoring';
import type { EditorCourse, Status } from '@/entities/authoring';
import { useCurrentUser } from '@/entities/session';
import {
  CourseForm,
  ModuleForm,
  ModuleEditor,
  useCourseCommand,
  authoringError,
  moveItem,
} from '@/features/course-authoring';
import { RoleAccess } from '@/features/role-access';
import { Button, Heading, Notice } from '@/shared/ui';

function CourseEditor({ course, reload }: { course: EditorCourse; reload: () => void }) {
  const user = useCurrentUser();
  const command = useCourseCommand(course.id, course.revision);
  const [teacherId, setTeacherId] = useState('');
  const disabled = course.status !== 'draft' || command.isPending;
  const changeStatus = (status: Status) => {
    if (
      window.confirm(
        `Изменить статус курса на «${statusLabels[status]}»? Несохранённые правки в это действие не входят.`,
      )
    )
      void command
        .mutateAsync({ path: '/status', method: 'PUT', body: { status } })
        .catch(() => undefined);
  };
  return (
    <>
      <Link to="/authoring/courses">← К редактору курсов</Link>
      <Heading>{course.title}</Heading>
      <p>
        <span className="authoring-status">{statusLabels[course.status]}</span> · Версия{' '}
        {course.revision}
      </p>
      <div className="actions">
        {course.status !== 'draft' && (
          <Button disabled={command.isPending} onClick={() => changeStatus('draft')}>
            Вернуть в черновик
          </Button>
        )}
        {course.status === 'draft' && (
          <Button disabled={command.isPending} onClick={() => changeStatus('published')}>
            Опубликовать
          </Button>
        )}
        {course.status !== 'archived' && (
          <Button disabled={command.isPending} onClick={() => changeStatus('archived')}>
            Архивировать
          </Button>
        )}
        {course.status === 'published' && (
          <Link to={'/courses/' + course.id}>Открыть публичный курс</Link>
        )}
        <Button disabled={command.isPending} onClick={reload}>
          Обновить данные
        </Button>
      </div>
      {course.status !== 'draft' && (
        <Notice>
          Для редактирования содержания верните курс в черновик. Это уберёт его из публичного
          каталога.
        </Notice>
      )}
      {command.isError && (
        <Notice error>{authoringError(command.error)} Несохранённые поля остаются в форме.</Notice>
      )}
      {command.isSuccess && <Notice>Изменения сохранены.</Notice>}
      <section className="authoring-card">
        <h2>Данные курса</h2>
        <CourseForm
          initial={{ title: course.title, slug: course.slug, description: course.description }}
          disabled={disabled}
          save={(body) => command.mutateAsync({ method: 'PUT', body })}
        />
      </section>
      <h2>Модули и уроки</h2>
      {course.modules.length === 0 && (
        <p>Добавьте первый модуль и урок. Публикация требует хотя бы один урок в каждом модуле.</p>
      )}
      {course.modules.map((module, index) => (
        <section key={module.id}>
          <div className="actions">
            <Button
              disabled={disabled || index === 0}
              aria-label={`Поднять модуль ${module.title}`}
              onClick={() =>
                command.mutate({
                  path: '/modules/order',
                  method: 'PUT',
                  body: {
                    ids: moveItem(
                      course.modules.map((item) => item.id),
                      module.id,
                      -1,
                    ),
                  },
                })
              }
            >
              ↑
            </Button>
            <Button
              disabled={disabled || index === course.modules.length - 1}
              aria-label={`Опустить модуль ${module.title}`}
              onClick={() =>
                command.mutate({
                  path: '/modules/order',
                  method: 'PUT',
                  body: {
                    ids: moveItem(
                      course.modules.map((item) => item.id),
                      module.id,
                      1,
                    ),
                  },
                })
              }
            >
              ↓
            </Button>
            <Button
              disabled={disabled}
              onClick={() => {
                if (
                  window.confirm(
                    `Удалить модуль «${module.title}» и все его уроки? Это действие нельзя отменить.`,
                  )
                )
                  command.mutate({ path: '/modules/' + module.id, method: 'DELETE' });
              }}
            >
              Удалить модуль
            </Button>
          </div>
          <ModuleEditor
            module={module}
            courseId={course.id}
            disabled={disabled}
            run={(input) => command.mutateAsync(input)}
          />
        </section>
      ))}
      {course.status === 'draft' && (
        <details className="authoring-card">
          <summary>Добавить модуль</summary>
          <ModuleForm
            initial={{ title: '', description: '' }}
            submitLabel="Добавить модуль"
            resetAfterSave
            disabled={command.isPending}
            save={(body) => command.mutateAsync({ path: '/modules', method: 'POST', body })}
          />
        </details>
      )}
      <section className="authoring-card">
        <h2>Преподаватели курса</h2>
        {course.teachers.length === 0 && <p>Преподаватели не назначены.</p>}
        <ul className="authoring-list">
          {course.teachers.map((teacher) => (
            <li key={teacher.id} className="authoring-row">
              <span>
                {teacher.name} · {teacher.email} · {teacher.role}
                {!teacher.is_active && ' · неактивен'}
              </span>
              {user?.role === 'admin' && (
                <Button
                  disabled={command.isPending}
                  onClick={() => {
                    if (window.confirm(`Отозвать назначение ${teacher.name}?`))
                      command.mutate({ path: '/teachers/' + teacher.id, method: 'DELETE' });
                  }}
                >
                  Отозвать назначение
                </Button>
              )}
            </li>
          ))}
        </ul>
        {user?.role === 'admin' && (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              command.mutate({
                path: '/teachers',
                method: 'POST',
                body: { user_id: Number(teacherId) },
              });
            }}
          >
            <label>
              ID преподавателя
              <input
                type="number"
                min={1}
                step={1}
                required
                value={teacherId}
                onChange={(event) => setTeacherId(event.target.value)}
              />
            </label>
            <small>
              ID можно найти в <Link to="/admin/users">управлении пользователями</Link>. Назначение
              действует только для этого курса.
            </small>
            <Button
              type="submit"
              disabled={
                command.isPending ||
                !Number.isSafeInteger(Number(teacherId)) ||
                Number(teacherId) <= 0
              }
            >
              Назначить преподавателя
            </Button>
          </form>
        )}
      </section>
    </>
  );
}
function Course() {
  const { courseId } = useParams();
  const id = Number(courseId);
  const gateway = useAuthoringGateway();
  const [generation, setGeneration] = useState(0);
  const query = useQuery({ ...gateway.detail(id), refetchOnWindowFocus: false });
  if (!Number.isSafeInteger(id) || id <= 0) return <Notice error>Некорректный ID курса.</Notice>;
  if (query.isPending || (!query.isFetchedAfterMount && query.isFetching))
    return <Notice>Загружаем редактор…</Notice>;
  if (query.isError)
    return (
      <Notice error>
        {authoringError(query.error)}{' '}
        <Button onClick={() => void query.refetch()}>Повторить</Button>
      </Notice>
    );
  return (
    <CourseEditor
      key={`${id}-${generation}`}
      course={query.data}
      reload={() => {
        if (window.confirm('Загрузить актуальную версию? Несохранённые поля будут сброшены.'))
          void query.refetch().then((result) => {
            if (result.isSuccess) setGeneration((value) => value + 1);
          });
      }}
    />
  );
}
export default function AuthoringCoursePage() {
  return (
    <RoleAccess>
      <Course />
    </RoleAccess>
  );
}
