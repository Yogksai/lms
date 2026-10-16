import { Navigate } from 'react-router-dom';
import { useCurrentUser } from '@/entities/session';
import { RegisterForm } from '@/features/auth';
import { Heading } from '@/shared/ui';
export default function RegisterPage() {
  const user = useCurrentUser();
  if (user) return <Navigate to="/courses" replace />;
  return (
    <section className="form-panel">
      <Heading>Регистрация</Heading>
      <RegisterForm />
    </section>
  );
}
