import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAccount } from '@/entities/session';
import { Button } from '@/shared/ui';
export function LogoutButton() {
  const { session } = useAccount();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  async function logout() {
    setBusy(true);
    try {
      await session.signOut();
      navigate('/login', { replace: true });
    } catch {
      navigate('/login?logout=failed', { replace: true });
    } finally {
      setBusy(false);
    }
  }
  return (
    <Button onClick={() => void logout()} disabled={busy}>
      Выйти
    </Button>
  );
}
