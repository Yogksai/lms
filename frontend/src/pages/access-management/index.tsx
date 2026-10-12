import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import {
  useEnrollmentGateway,
  requestLabels,
  sourceLabels,
  requestStatusSchema,
} from '@/entities/enrollment';
import type { ManagedRequest, RequestStatus } from '@/entities/enrollment';
import { useCurrentUser } from '@/entities/session';
import { useAccessCommand, accessError } from '@/features/course-access';
import { RoleAccess } from '@/features/role-access';
import { Button, Heading, Notice } from '@/shared/ui';

function RequestDecision({
  request,
  busy,
  decide,
}: {
  request: ManagedRequest;
  busy: boolean;
  decide: (decision: 'approve' | 'reject', duration: number, note: string) => void;
}) {
  const [days, setDays] = useState('90');
  const [note, setNote] = useState('');
  return (
    <section className="authoring-card">
      <h2>
        {request.student.name} · ID {request.student.id}
      </h2>
      <p>
        {request.student.email} · {requestLabels[request.status]} ·{' '}
        {new Date(request.created_at).toLocaleString('ru-RU')}
      </p>
      <p>Сообщение: {request.message || 'Без сообщения'}</p>
      {request.status === 'pending' ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const button = (event.nativeEvent as SubmitEvent).submitter;
            const decision =
              button instanceof HTMLButtonElement && button.value === 'reject'
                ? 'reject'
                : 'approve';
            decide(decision, Number(days), note);
          }}
        >
          <label>
            Срок доступа в днях
            <input
              type="number"
              min={1}
              max={365}
              step={1}
              required
              value={days}
              onChange={(event) => setDays(event.target.value)}
              disabled={busy}
            />
          </label>
          <label>
            Комментарий к решению
            <textarea
              rows={2}
              maxLength={1000}
              value={note}
              onChange={(event) => setNote(event.target.value)}
              disabled={busy}
            />
          </label>
          <div className="actions">
            <Button
              type="submit"
              name="decision"
              value="approve"
              disabled={busy || !request.student.is_active}
            >
              Одобрить
            </Button>
            <Button type="submit" name="decision" value="reject" disabled={busy}>
              Отклонить
            </Button>
          </div>
          {!request.student.is_active && <small>Неактивному аккаунту нельзя выдать доступ.</small>}
        </form>
      ) : (
        <p>
          Решение: {request.decision_note || 'Без комментария'}
          {request.decided_at && <> · {new Date(request.decided_at).toLocaleString('ru-RU')}</>}
        </p>
      )}
    </section>
  );
}
function Management() {
  const { courseId } = useParams();
  const id = Number(courseId);
  const user = useCurrentUser();
  const gateway = useEnrollmentGateway();
  const command = useAccessCommand();
  const [status, setStatus] = useState<RequestStatus | 'all'>('pending');
  const [requestOffset, setRequestOffset] = useState(0);
  const [grantOffset, setGrantOffset] = useState(0);
  const [activeOnly, setActiveOnly] = useState(true);
  const [studentId, setStudentId] = useState('');
  const [days, setDays] = useState('90');
  const requests = useQuery(gateway.requests(id, status, requestOffset));
  const grants = useQuery(gateway.grants(id, activeOnly, grantOffset));
  const base = `/access/courses/${id}`;
  if (!Number.isSafeInteger(id) || id <= 0) return <Notice error>Некорректный ID курса.</Notice>;
  return (
    <section>
      <Link to={'/authoring/courses/' + id}>← К редактору курса</Link>
      <Heading>Заявки и доступ · курс {id}</Heading>
      <p>
        Решения доступны только назначенным преподавателям и администраторам. Для выдачи доступа
        курс должен быть опубликован, а учащийся — записан на него.
      </p>
      <Button
        disabled={requests.isFetching || grants.isFetching || command.isPending}
        onClick={() => {
          void requests.refetch();
          void grants.refetch();
        }}
      >
        Обновить данные
      </Button>
      {command.isError && <Notice error>{accessError(command.error)}</Notice>}
      {command.isSuccess && <Notice>Изменения сохранены.</Notice>}
      <h2>Заявки</h2>
      <label>
        Статус заявки
        <select
          value={status}
          onChange={(event) => {
            setStatus(
              event.target.value === 'all' ? 'all' : requestStatusSchema.parse(event.target.value),
            );
            setRequestOffset(0);
          }}
        >
          <option value="all">Все</option>
          {requestStatusSchema.options.map((value) => (
            <option key={value} value={value}>
              {requestLabels[value]}
            </option>
          ))}
        </select>
      </label>
      {requests.isPending ? (
        <Notice>Загружаем заявки…</Notice>
      ) : requests.isError ? (
        <Notice error>{accessError(requests.error)}</Notice>
      ) : (
        <>
          {requests.data.items.length === 0 && <Notice>Заявок с выбранным статусом нет.</Notice>}
          {requests.data.items.map((request) => (
            <RequestDecision
              key={request.id}
              request={request}
              busy={command.isPending}
              decide={(decision, duration_days, note) =>
                command.mutate({
                  path: `${base}/requests/${request.id}`,
                  method: 'PUT',
                  body: { decision, duration_days, note },
                })
              }
            />
          ))}
          <div className="actions">
            <Button
              disabled={requestOffset === 0}
              onClick={() => setRequestOffset(Math.max(0, requestOffset - 20))}
            >
              Предыдущие заявки
            </Button>
            <span>Всего: {requests.data.total}</span>
            <Button
              disabled={requestOffset + 20 >= requests.data.total}
              onClick={() => setRequestOffset(requestOffset + 20)}
            >
              Следующие заявки
            </Button>
          </div>
        </>
      )}
      <h2>Выданные разрешения</h2>
      <p>
        Разрешения независимы: отзыв одного не отменяет остальные. Действующее разрешение не
        открывает снятый с публикации курс.
      </p>
      <label>
        Показать разрешения
        <select
          value={activeOnly ? 'active' : 'all'}
          onChange={(event) => {
            setActiveOnly(event.target.value === 'active');
            setGrantOffset(0);
          }}
        >
          <option value="active">Действующие</option>
          <option value="all">Все, включая историю</option>
        </select>
      </label>
      {grants.isPending ? (
        <Notice>Загружаем разрешения…</Notice>
      ) : grants.isError ? (
        <Notice error>{accessError(grants.error)}</Notice>
      ) : (
        <>
          {grants.data.items.length === 0 && (
            <Notice>Выданных разрешений с выбранным фильтром нет.</Notice>
          )}
          {grants.data.items.map((grant) => (
            <section key={grant.id} className="authoring-card">
              <h3>
                {grant.student.name} · {grant.student.email}
              </h3>
              <p>
                {sourceLabels[grant.source]} · до{' '}
                {new Date(grant.expires_at).toLocaleString('ru-RU')} ·{' '}
                {grant.revoked_at ? 'Отозван' : grant.active ? 'Действует' : 'Неактивен'}
              </p>
              <Button
                disabled={
                  command.isPending ||
                  !!grant.revoked_at ||
                  (grant.source === 'admin_grant' && user?.role !== 'admin')
                }
                onClick={() => {
                  if (
                    window.confirm('Отозвать это разрешение? Другие основания доступа сохранятся.')
                  )
                    command.mutate({ path: `${base}/grants/${grant.id}`, method: 'DELETE' });
                }}
              >
                Отозвать разрешение
              </Button>
              {grant.source === 'admin_grant' && user?.role !== 'admin' && (
                <small> Только администратор может отозвать это разрешение.</small>
              )}
            </section>
          ))}
          <div className="actions">
            <Button
              disabled={grantOffset === 0}
              onClick={() => setGrantOffset(Math.max(0, grantOffset - 20))}
            >
              Предыдущие разрешения
            </Button>
            <span>Всего: {grants.data.total}</span>
            <Button
              disabled={grantOffset + 20 >= grants.data.total}
              onClick={() => setGrantOffset(grantOffset + 20)}
            >
              Следующие разрешения
            </Button>
          </div>
        </>
      )}
      {user?.role === 'admin' && (
        <section className="authoring-card">
          <h2>Выдать независимый административный доступ</h2>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              command.mutate({
                path: base + '/grants',
                method: 'POST',
                body: { user_id: Number(studentId), duration_days: Number(days) },
              });
            }}
          >
            <label>
              ID записанного учащегося
              <input
                type="number"
                min={1}
                step={1}
                required
                value={studentId}
                onChange={(event) => setStudentId(event.target.value)}
                disabled={command.isPending}
              />
            </label>
            <label>
              Срок в днях
              <input
                type="number"
                min={1}
                max={365}
                step={1}
                required
                value={days}
                onChange={(event) => setDays(event.target.value)}
                disabled={command.isPending}
              />
            </label>
            <small>
              ID можно найти в <Link to="/admin/users">управлении пользователями</Link>.
              Административное разрешение не зависит от одобрения заявки.
            </small>
            <Button type="submit" disabled={command.isPending}>
              Выдать доступ
            </Button>
          </form>
        </section>
      )}
    </section>
  );
}
export default function AccessManagementPage() {
  return (
    <RoleAccess>
      <Management />
    </RoleAccess>
  );
}
