import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useEnrollmentGateway } from '@/entities/enrollment';
import type { AccessCommand } from '@/entities/enrollment';
import { useAccount } from '@/entities/session';
import { HttpError } from '@/shared/api';
export function accessError(error: unknown): string {
  if (error instanceof HttpError) {
    if (error.status === 401) return 'Войдите в аккаунт снова.';
    if (error.status === 403) return 'Недостаточно прав для управления этим доступом.';
    if (error.status === 404)
      return 'Курс или запись не найдены либо назначение преподавателя отозвано.';
    if (error.status === 409)
      return 'Состояние изменилось: проверьте запись на курс, текущий доступ, статус заявки и публикацию курса. Обновите данные.';
    if (error.status === 422) return 'Проверьте срок (1–365 дней), поля и активность аккаунта.';
  }
  return 'Не удалось связаться с сервером. Попробуйте снова.';
}
export function useAccessCommand() {
  const gateway = useEnrollmentGateway();
  const { session } = useAccount();
  const client = useQueryClient();
  return useMutation({
    onMutate: () => ({ epoch: session.identityVersion() }),
    mutationFn: async (command: AccessCommand) => {
      const epoch = session.identityVersion();
      await gateway.command(command);
      if (epoch !== session.identityVersion()) throw new HttpError(401, 'Session changed');
    },
    onSuccess: async (_result, _command, context) => {
      if (context.epoch !== session.identityVersion()) return;
      await client.cancelQueries({ queryKey: ['private', 'enrollment'] });
      if (context.epoch !== session.identityVersion()) return;
      // Drop loaded lesson bodies before checking the updated authorization state.
      await client.cancelQueries({ queryKey: ['private', 'lesson'] });
      await client.resetQueries({ queryKey: ['private', 'lesson'] });
      if (context.epoch !== session.identityVersion()) return;
      await client.invalidateQueries({ queryKey: ['private', 'enrollment'] });
    },
  });
}
