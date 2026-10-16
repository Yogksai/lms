import { Navigate, useSearchParams } from 'react-router-dom';
import { useCurrentUser } from '@/entities/session';
import { LoginForm } from '@/features/auth';
import { Heading, Notice } from '@/shared/ui';
export default function LoginPage() {
  const user = useCurrentUser();
  const [params] = useSearchParams();
  if (user) return <Navigate to="/courses" replace />;
  return (
    <section className="form-panel">
      <Heading>Войти</Heading>
      {params.get('registered') === '1' && <Notice>Аккаунт создан. Теперь можно войти.</Notice>}
      {params.get('logout') === 'failed' && (
        <Notice error>
          Вы вышли на этом устройстве, но сервер не подтвердил завершение сессии. Войдите снова
          после восстановления связи.
        </Notice>
      )}
      <LoginForm />
    </section>
  );
}
