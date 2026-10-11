import { createContext, useContext } from 'react';
import type { CourseQueries } from './api';
export const CourseContext = createContext<CourseQueries | null>(null);
export function useCourseQueries() {
  const queries = useContext(CourseContext);
  if (!queries) throw new Error('Course provider is missing');
  return queries;
}
