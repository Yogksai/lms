import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuthoringGateway } from '@/entities/authoring';
import { useCurrentUser } from '@/entities/session';
import type { User } from '@/entities/session';
import { RoleAccess } from '@/features/role-access';
import { authoringError } from '@/features/course-authoring';
import { roleSchema } from '@/shared/model/identity';
import type { Role } from '@/shared/model/identity';
import { Button, Heading, Notice } from '@/shared/ui';

const labels: Record<Role, string> = {
  student: 'Студент',
  teacher: 'Преподаватель',
  admin: 'Администратор',
};
function RoleEditor({
  user,
  self,
  busy,
  save,
}: {
  user: User;
  self: boolean;
  busy: boolean;
  save: (role: Role) => Promise<unknown>;
}) {
  const [role, setRole] = useState(user.role);
  return (
    <form
      className="actions"
      onSubmit={(event) => {
        event.preventDefault();
        if (
          window.confirm(
            `Назначить ${user.email} роль «${labels[role]}»? Преподаватели получат права только на назначенные им курсы; администраторы — на все курсы и роли.`,
          )
        )
          void save(role).catch(() => undefined);
      }}
    >
      <label>
        Роль для {user.email}
        <select
          disabled={self || busy}
          value={role}
          onChange={(event) => setRole(roleSchema.parse(event.target.value))}
        >
          {roleSchema.options.map((option) => (
            <option key={option} value={option} disabled={!user.is_active && option !== 'student'}>
              {labels[option]}
            </option>
          ))}
        </select>
      </label>
      <Button type="submit" disabled={self || busy || role === user.role}>
        Сохранить роль
      </Button>
      {self && <small>Свою роль изменить нельзя.</small>}
    </form>
  );
}
function Users() {
  const gateway = useAuthoringGateway();
  const current = useCurrentUser();
  const client = useQueryClient();
  const [input, setInput] = useState('');
  const [search, setSearch] = useState('');
  const [offset, setOffset] = useState(0);
  const query = useQuery(gateway.users(search, offset));
  const mutation = useMutation({
    mutationFn: ({ id, role }: { id: number; role: Role }) => gateway.setRole(id, role),
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: ['private', 'admin', 'users'] }),
        client.invalidateQueries({ queryKey: ['private', 'authoring'] }),
      ]);
    },
  });
  return (
    <section>
      <Heading>Управление пользователями</Heading>
      <p>
        Назначение роли преподавателя не открывает доступ к чужим курсам. Назначьте конкретный курс
        в его редакторе.
      </p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          setSearch(input.trim());
          setOffset(0);
        }}
      >
        <label>
          Найти по почте
          <input
            type="search"
            maxLength={255}
            value={input}
            onChange={(event) => setInput(event.target.value)}
          />
        </label>
        <Button type="submit">Найти</Button>
      </form>
      {mutation.isError && <Notice error>{authoringError(mutation.error)}</Notice>}
      {mutation.isSuccess && <Notice>Роль обновлена.</Notice>}
      {query.isPending ? (
        <Notice>Загружаем пользователей…</Notice>
      ) : query.isError ? (
        <Notice error>
          {authoringError(query.error)}{' '}
          <Button onClick={() => void query.refetch()}>Повторить</Button>
        </Notice>
      ) : (
        <>
          {query.data.items.length === 0 && <Notice>Пользователи не найдены.</Notice>}
          {query.data.items.map((user) => (
            <section className="authoring-card" key={user.id}>
              <h2>
                {user.name} · ID {user.id}
              </h2>
              <p>
                {user.email} · {user.is_active ? 'Активен' : 'Неактивен'}
              </p>
              <RoleEditor
                key={user.id + '-' + user.role}
                user={user}
                self={user.id === current?.id}
                busy={mutation.isPending}
                save={(role) => mutation.mutateAsync({ id: user.id, role })}
              />
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
export default function AdminUsersPage() {
  return (
    <RoleAccess admin>
      <Users />
    </RoleAccess>
  );
}
