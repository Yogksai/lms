import type { ReactNode } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { AccountContext } from '@/entities/session';
import { CourseContext } from '@/entities/course';
import { courseQueries, gateway, queryClient, session } from './runtime';
export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <AccountContext.Provider value={{ session, gateway }}>
        <CourseContext.Provider value={courseQueries}>{children}</CourseContext.Provider>
      </AccountContext.Provider>
    </QueryClientProvider>
  );
}
