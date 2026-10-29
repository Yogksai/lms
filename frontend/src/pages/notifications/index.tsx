import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { notificationKey, useNotificationGateway } from '@/entities/notification';
import { useAccount, useCurrentUser } from '@/entities/session';
import { errorMessage } from '@/shared/api';
import { Button, Heading, Notice } from '@/shared/ui';
function Inbox({ userId }: { userId: number }) {
  const gateway = useNotificationGateway(),
    client = useQueryClient();
  const { session } = useAccount();
  const [offset, setOffset] = useState(0);
  const query = useQuery(gateway.inbox(userId, offset));
  const read = useMutation({
    mutationFn: async (id: number) => {
      const identity = session.identityVersion();
      await gateway.read(id);
      if (identity === session.identityVersion())
        await client.invalidateQueries({ queryKey: notificationKey(userId) });
    },
  });
  return (
    <>
      <Heading>Уведомления</Heading>
      <p>
        Результат теста доступен сразу. Уведомление доставляется отдельно и может появиться чуть
        позже.
      </p>
      {read.isError && <Notice error>{errorMessage(read.error)}</Notice>}
      {query.isPending ? (
        <Notice>Загружаем…</Notice>
      ) : query.isError ? (
        <Notice error>
          {errorMessage(query.error)}{' '}
          <Button onClick={() => void query.refetch()}>Повторить</Button>
        </Notice>
      ) : (
        <>
          {!query.data.total && <Notice>Пока нет уведомлений.</Notice>}
          {query.data.items.map((item) => (
            <section className="authoring-card" key={item.id}>
              <h2>
                {item.title}
                {!item.read_at && ' · новое'}
              </h2>
              <p>{item.message}</p>
              <small>{new Date(item.created_at).toLocaleString('ru-RU')}</small>
              <div className="actions">
                <Link to={item.link}>Открыть результат</Link>
                {!item.read_at && (
                  <Button disabled={read.isPending} onClick={() => read.mutate(item.id)}>
                    Отметить прочитанным
                  </Button>
                )}
              </div>
            </section>
          ))}
          <div className="actions">
            <Button disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 20))}>
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
    </>
  );
}
export default function NotificationsPage() {
  const user = useCurrentUser();
  return user ? (
    <Inbox key={user.id} userId={user.id} />
  ) : (
    <Notice>
      <Link to="/login">Войди</Link>, чтобы увидеть уведомления.
    </Notice>
  );
}
