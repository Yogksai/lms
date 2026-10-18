import { createContext, useContext } from 'react';
import type { AuthoringGateway } from './api';
export const AuthoringContext = createContext<AuthoringGateway | null>(null);
export function useAuthoringGateway() {
  const value = useContext(AuthoringContext);
  if (!value) throw new Error('Authoring provider is missing');
  return value;
}
