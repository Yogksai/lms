import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { useQuizGateway } from '@/entities/quiz';
import { useCurrentUser } from '@/entities/session';
import { QuizEditor } from '@/features/quiz-authoring';
import { RoleAccess } from '@/features/role-access';
import { errorMessage } from '@/shared/api';
import { Button, Heading, Notice } from '@/shared/ui';
function Editor() {
  const params = useParams();
  const courseId = Number(params.courseId),
    moduleId = Number(params.moduleId);
  const user = useCurrentUser();
  const gateway = useQuizGateway();
  const [offset, setOffset] = useState(0);
  const [generation, setGeneration] = useState(0);
  const valid = [courseId, moduleId].every((id) => Number.isSafeInteger(id) && id > 0);
  const query = useQuery({
    ...gateway.bank(user?.id ?? 0, courseId, moduleId, offset),
    enabled: !!user && valid,
  });
  if (!valid) return <Notice error>Некорректный адрес теста.</Notice>;
  if (query.isPending || (!query.isFetchedAfterMount && query.isFetching))
    return <Notice>Загружаем банк вопросов…</Notice>;
  if (query.isError)
    return (
      <Notice error>
        {errorMessage(query.error)} <Button onClick={() => void query.refetch()}>Повторить</Button>
      </Notice>
    );
  return (
    <>
      <Link to={`/authoring/courses/${courseId}`}>← К редактору курса</Link>
      <Heading>Тест: {query.data.title}</Heading>
      <QuizEditor
        key={`${user?.id}-${courseId}-${moduleId}-${offset}-${generation}`}
        courseId={courseId}
        bank={query.data}
        reload={() => {
          if (window.confirm('Сбросить несохранённые поля и загрузить актуальную версию?'))
            void query.refetch().then((result) => {
              if (result.isSuccess) setGeneration((value) => value + 1);
            });
        }}
      />
      <div className="actions">
        <Button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 20))}>
          Назад
        </Button>
        <span>
          {offset + 1}–{Math.min(offset + 20, query.data.total)} из {query.data.total}
        </span>
        <Button disabled={offset + 20 >= query.data.total} onClick={() => setOffset(offset + 20)}>
          Далее
        </Button>
      </div>
    </>
  );
}
export default function AuthoringQuizPage() {
  return (
    <RoleAccess>
      <Editor />
    </RoleAccess>
  );
}
