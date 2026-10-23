import { useState } from 'react';
import type { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  useEnrollmentGateway,
  hasFullAccess,
  requestLabels,
  sourceLabels,
} from '@/entities/enrollment';
import { useCurrentUser } from '@/entities/session';
import { Button, Notice } from '@/shared/ui';
import { useAccessCommand, accessError } from './model';

type Props = { courseId: number; outline?: (fullAccess: boolean) => ReactNode };
function StudentAccess({ courseId, userId, outline }: Props & { userId: number }) {
  const gateway = useEnrollmentGateway();
  const query = useQuery(gateway.status(courseId, userId));
  const command = useAccessCommand();
  const [message, setMessage] = useState('');
  const status = query.data;
  const full = !!status && !query.isError && hasFullAccess(status);
  const base = `/courses/${courseId}`;
  const pending = status?.request?.status === 'pending';
  return (
    <>
      {outline?.(full)}
      <section className="authoring-card" aria-label="Доступ к курсу">
        <h2>Доступ к курсу</h2>
        {query.isPending ? (
          <Notice>Проверяем доступ…</Notice>
        ) : query.isError ? (
          <Notice error>
            {accessError(query.error)}{' '}
            <Button onClick={() => void query.refetch()}>Повторить</Button>
          </Notice>
        ) : (
          status && (
            <>
              {!status.available && (
                <Notice>
                  Курс временно недоступен: он не опубликован. Запись и история доступа сохранены.
                </Notice>
              )}
              {full ? (
                <Notice>
                  {status.expires_at
                    ? `Все модули доступны до ${new Date(status.expires_at).toLocaleString('ru-RU')}.`
                    : 'Все модули доступны по вашим правам администратора или назначенного преподавателя.'}
                </Notice>
              ) : (
                <p>
                  Первый модуль бесплатный. Запись на курс сохраняет его в вашем списке, но не
                  открывает остальные модули.
                </p>
              )}
              {!status.enrolled && status.available && (
                <Button
                  disabled={command.isPending}
                  onClick={() => command.mutate({ path: base + '/enrollment', method: 'POST' })}
                >
                  Записаться на курс
                </Button>
              )}
              {status.enrolled && <p>Вы записаны на этот курс.</p>}
              {status.request && (
                <p>
                  Последняя заявка: {requestLabels[status.request.status]}.
                  {status.request.decision_note && (
                    <> Комментарий: {status.request.decision_note}</>
                  )}
                </p>
              )}
              {pending && status.request && (
                <Button
                  disabled={command.isPending}
                  onClick={() =>
                    command.mutate({
                      path: base + '/access-requests/' + status.request!.id,
                      method: 'DELETE',
                    })
                  }
                >
                  Отменить заявку
                </Button>
              )}
              {status.enrolled && status.available && !full && !pending && (
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    command.mutate(
                      { path: base + '/access-requests', method: 'POST', body: { message } },
                      { onSuccess: () => setMessage('') },
                    );
                  }}
                >
                  <label>
                    Сообщение преподавателю
                    <textarea
                      rows={3}
                      maxLength={2000}
                      value={message}
                      onChange={(event) => setMessage(event.target.value)}
                    />
                  </label>
                  <small>
                    Срок доступа назначается при одобрении. Оплата в этом этапе не подключена.
                  </small>
                  <Button type="submit" disabled={command.isPending}>
                    Запросить полный доступ
                  </Button>
                </form>
              )}
              {status.grants.length > 0 && (
                <details>
                  <summary>История доступа</summary>
                  <ul className="authoring-list">
                    {status.grants.map((grant) => (
                      <li key={grant.id} className="authoring-row">
                        {sourceLabels[grant.source]} · до{' '}
                        {new Date(grant.expires_at).toLocaleString('ru-RU')} ·{' '}
                        {grant.revoked_at
                          ? 'Отозван'
                          : Date.parse(grant.expires_at) <= Date.now()
                            ? 'Истёк'
                            : 'Действует'}
                      </li>
                    ))}
                  </ul>
                  <small>
                    Показаны последние 50 записей. Активный доступ рассчитывается по всем
                    действующим основаниям.
                  </small>
                </details>
              )}
              {status.enrolled && (
                <Button
                  disabled={command.isPending}
                  onClick={() => {
                    if (
                      window.confirm(
                        'Покинуть курс? Все выданные вам разрешения будут отозваны, а ожидающая заявка отменена. Повторная запись не восстановит доступ.',
                      )
                    )
                      command.mutate({ path: base + '/enrollment', method: 'DELETE' });
                  }}
                >
                  Покинуть курс
                </Button>
              )}
            </>
          )
        )}
        {command.isError && <Notice error>{accessError(command.error)}</Notice>}
        {command.isSuccess && <Notice>Изменения сохранены.</Notice>}
      </section>
    </>
  );
}
export function CourseAccess({ courseId, outline }: Props) {
  const user = useCurrentUser();
  if (!user)
    return (
      <>
        {outline?.(false)}
        <Notice>
          Первый модуль доступен без регистрации. <Link to="/login">Войдите</Link>, чтобы записаться
          на курс и запросить полный доступ.
        </Notice>
      </>
    );
  return (
    <StudentAccess
      key={user.id + '-' + courseId}
      courseId={courseId}
      userId={user.id}
      outline={outline}
    />
  );
}
