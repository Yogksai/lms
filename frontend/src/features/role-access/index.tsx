import type { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Navigate } from 'react-router-dom';
import { useAccount, useCurrentUser } from '@/entities/session';
import { Button, Notice } from '@/shared/ui';
import { errorMessage } from '@/shared/api';
export function RoleAccess({ admin = false, children }: { admin?: boolean; children: ReactNode }) {
  const user = useCurrentUser();
  const { session } = useAccount();
  const profile = useQuery({
    queryKey: ['private', 'permissions', user?.id],
    queryFn: () => session.reloadProfile(),
    enabled: !!user,
    staleTime: 0,
    refetchOnMount: 'always',
    retry: false,
  });
  if (!user) return <Navigate to="/login" replace />;
  if (profile.isPending || (!profile.isFetchedAfterMount && profile.isFetching))
    return <Notice>Проверяем права…</Notice>;
  if (profile.isError)
    return (
      <Notice error>
        {errorMessage(profile.error)}{' '}
        <Button onClick={() => void profile.refetch()}>Повторить</Button>
      </Notice>
    );
  if (
    !profile.data.is_active ||
    (admin ? profile.data.role !== 'admin' : !['teacher', 'admin'].includes(profile.data.role))
  )
    return (
      <Notice error>
        Для этой страницы нужны права {admin ? 'администратора' : 'преподавателя'}.
      </Notice>
    );
  return children;
}
