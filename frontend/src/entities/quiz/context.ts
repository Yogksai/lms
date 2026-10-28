import { createContext, useContext } from 'react';
import type { QuizGateway } from './api';
export const QuizContext = createContext<QuizGateway | null>(null);
export function useQuizGateway() {
  const gateway = useContext(QuizContext);
  if (!gateway) throw new Error('Quiz provider is missing');
  return gateway;
}
