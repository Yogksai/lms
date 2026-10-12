import { createContext, useContext } from 'react';
import type { EnrollmentGateway } from './api';
export const EnrollmentContext = createContext<EnrollmentGateway | null>(null);
export function useEnrollmentGateway() {
  const value = useContext(EnrollmentContext);
  if (!value) throw new Error('Enrollment provider is missing');
  return value;
}
