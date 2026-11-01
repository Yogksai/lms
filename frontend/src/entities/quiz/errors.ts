import { errorMessage, HttpError } from '@/shared/api';
export function quizError(error: unknown): string {
  if (error instanceof HttpError) {
    if (error.status === 409)
      return 'Тест изменился, недоступен или попытка уже сдана. Обнови данные перед повторным действием.';
    if (error.status === 403) return 'Для этого модуля нужен действующий доступ к курсу.';
    if (error.status === 429)
      return 'Достигнут лимит новых попыток или частоты запросов. Проверь дневной остаток и попробуй позже.';
  }
  return errorMessage(error);
}
