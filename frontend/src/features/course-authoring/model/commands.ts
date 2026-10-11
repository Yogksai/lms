import { useMutation, useQueryClient } from '@tanstack/react-query';
import { authoringKey, useAuthoringGateway } from '@/entities/authoring';
import type { Command } from '@/entities/authoring';
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
  return useMutation({
    mutationFn: (command: Command) => gateway.command(id, revision, command),
    onSuccess: async (course) => {
      await client.cancelQueries({ queryKey: authoringKey(id) });
      client.setQueryData(authoringKey(id), course);
      await Promise.all([
        client.invalidateQueries({ queryKey: ['private', 'authoring', 'list'] }),
        client.invalidateQueries({ queryKey: ['courses'] }),
      ]);
    },
  });
}
