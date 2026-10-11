import type { ReactNode } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { AccountContext } from '@/entities/session';
import { CourseContext } from '@/entities/course';
import { AuthoringContext } from '@/entities/authoring';
import { authoringGateway, courseQueries, gateway, queryClient, session } from './runtime';
export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <AccountContext.Provider value={{ session, gateway }}>
        <CourseContext.Provider value={courseQueries}>
          <AuthoringContext.Provider value={authoringGateway}>{children}</AuthoringContext.Provider>
        </CourseContext.Provider>
      </AccountContext.Provider>
    </QueryClientProvider>
  );
}
