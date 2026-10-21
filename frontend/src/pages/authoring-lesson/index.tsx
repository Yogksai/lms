import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useAuthoringGateway } from '@/entities/authoring';
import type { EditorCourse } from '@/entities/authoring';
import { LessonForm, useCourseCommand, authoringError } from '@/features/course-authoring';
import { RoleAccess } from '@/features/role-access';
import { LessonViewer } from '@/widgets/lesson-viewer';
import { Button, Heading, Notice } from '@/shared/ui';

function Editor({
  course,
  moduleId,
  lessonId,
}: {
  course: EditorCourse;
  moduleId: number;
  lessonId: string;
}) {
  const navigate = useNavigate();
  const command = useCourseCommand(course.id, course.revision);
  const module = course.modules.find((item) => item.id === moduleId);
  const lesson = module?.lessons.find((item) => item.id === Number(lessonId));
  const isNew = lessonId === 'new';
  if (!module || (!isNew && !lesson))
    return <Notice error>Урок или модуль не найден в этом курсе.</Notice>;
  return (
    <>
      <Link to={'/authoring/courses/' + course.id}>← К редактору курса</Link>
      <Heading>{isNew ? 'Новый урок' : 'Редактор урока'}</Heading>
      <p>
        Модуль: {module.title} · версия курса {course.revision}
      </p>
      {course.status !== 'draft' && (
        <Notice>Сначала верните курс в черновик в редакторе курса.</Notice>
      )}
      {command.isError && (
        <Notice error>
          {authoringError(command.error)} Вернитесь к курсу, обновите данные и повторите сохранение.
        </Notice>
      )}
      {command.isSuccess && <Notice>Урок сохранён.</Notice>}
      <section className="authoring-card">
        <LessonForm
          initial={
            lesson
              ? { title: lesson.title, summary: lesson.summary, video_url: lesson.video_url }
              : { title: '', summary: '', video_url: '' }
          }
          disabled={course.status !== 'draft' || command.isPending}
          save={async (body) => {
            const result = await command.mutateAsync({
              path: `/modules/${module.id}/lessons${isNew ? '' : '/' + lessonId}`,
              method: isNew ? 'POST' : 'PUT',
              body,
            });
            if (isNew) navigate('/authoring/courses/' + result.id);
          }}
        />
      </section>
      {lesson && (
        <details className="authoring-card">
          <summary>Предпросмотр сохранённого урока</summary>
          <LessonViewer lesson={lesson} />
        </details>
      )}
    </>
  );
}
function Lesson() {
  const { courseId, moduleId, lessonId = '' } = useParams();
  const gateway = useAuthoringGateway();
  const [generation, setGeneration] = useState(0);
  const id = Number(courseId);
  const query = useQuery({ ...gateway.detail(id), refetchOnWindowFocus: false });
  if (
    ![id, Number(moduleId)].every((value) => Number.isSafeInteger(value) && value > 0) ||
    (lessonId !== 'new' && (!Number.isSafeInteger(Number(lessonId)) || Number(lessonId) <= 0))
  )
    return <Notice error>Некорректный адрес урока.</Notice>;
  if (query.isPending || (!query.isFetchedAfterMount && query.isFetching))
    return <Notice>Загружаем урок…</Notice>;
  if (query.isError) return <Notice error>{authoringError(query.error)}</Notice>;
  return (
    <>
      <Button
        disabled={query.isFetching}
        onClick={() => {
          if (window.confirm('Обновить данные и сбросить несохранённые поля?'))
            void query.refetch().then((result) => {
              if (result.isSuccess) setGeneration((value) => value + 1);
            });
        }}
      >
        Обновить данные
      </Button>
      <Editor
        key={`${id}-${moduleId}-${lessonId}-${generation}`}
        course={query.data}
        moduleId={Number(moduleId)}
        lessonId={lessonId}
      />
    </>
  );
}
export default function AuthoringLessonPage() {
  return (
    <RoleAccess>
      <Lesson />
    </RoleAccess>
  );
}
