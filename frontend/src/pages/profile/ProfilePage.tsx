import { useQuery } from '@tanstack/react-query';
import { Navigate } from 'react-router-dom';
import { useAccount, useCurrentUser } from '@/entities/session';
import { ProfileForm } from '@/features/auth';
import { errorMessage } from '@/shared/api';
import { Button, Heading, Notice } from '@/shared/ui';
export default function ProfilePage() {
  const user = useCurrentUser();
  const { gateway } = useAccount();
  const query = useQuery({
    queryKey: ['private', 'profile', user?.id],
    queryFn: () => gateway.me(),
    enabled: !!user,
    staleTime: 0,
    retry: false,
  });
  if (!user) return <Navigate to="/login" replace />;
  return (
    <section className="form-panel">
      <Heading>Мой профиль</Heading>
      {query.isPending ? (
        <Notice>Загружаем профиль…</Notice>
      ) : query.isError ? (
        <Notice error>
          {errorMessage(query.error)}{' '}
          <Button onClick={() => void query.refetch()}>Повторить</Button>
        </Notice>
      ) : (
        <>
          <p>Почта: {query.data.email}</p>
          <p>
            Роль:{' '}
            {query.data.role === 'admin'
              ? 'Администратор'
              : query.data.role === 'teacher'
                ? 'Преподаватель'
                : 'Студент'}
          </p>
          <ProfileForm name={query.data.name} />
          <p>
            <small>Изменение почты и пароля появится позднее.</small>
          </p>
        </>
      )}
    </section>
  );
}
