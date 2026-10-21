import { useMutation, useQueryClient } from '@tanstack/react-query';
import { authoringKey, useAuthoringGateway } from '@/entities/authoring';
import type { Command } from '@/entities/authoring';
import { useAccount } from '@/entities/session';
import { HttpError } from '@/shared/api';
export function authoringError(error: unknown): string {
  if (error instanceof HttpError) {
    if (error.status === 409)
      return 'Не удалось сохранить: курс изменён, slug занят или курс не в черновике. Обновите данные и проверьте статус.';
    if (error.status === 403) return 'Недостаточно прав для этого действия.';
    if (error.status === 404) return 'Материал не найден или назначение преподавателя отозвано.';
    if (error.status === 422)
      return 'Проверьте поля, порядок и наличие уроков во всех модулях. Назначать можно только активных преподавателей.';
    if (error.status === 401) return 'Войдите в аккаунт снова.';
  }
  return 'Не удалось выполнить действие. Проверьте соединение.';
}
export function useCourseCommand(id: number, revision: number) {
  const gateway = useAuthoringGateway();
  const client = useQueryClient();
  const { session } = useAccount();
  return useMutation({
    onMutate: () => ({ epoch: session.identityVersion() }),
    mutationFn: async (command: Command) => {
      const epoch = session.identityVersion();
      const course = await gateway.command(id, revision, command);
      if (session.identityVersion() !== epoch) throw new HttpError(401, 'Session changed');
      return course;
    },
    onSuccess: async (course, _command, context) => {
      if (context.epoch !== session.identityVersion()) return;
      await client.cancelQueries({ queryKey: authoringKey(id) });
      if (context.epoch !== session.identityVersion()) return;
      client.setQueryData(authoringKey(id), course);
      await Promise.all([
        client.invalidateQueries({ queryKey: ['private', 'authoring', 'list'] }),
        client.invalidateQueries({ queryKey: ['courses'] }),
      ]);
    },
  });
}
