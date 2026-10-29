import type { ReactNode } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { AccountContext } from '@/entities/session';
import { CourseContext } from '@/entities/course';
import { AuthoringContext } from '@/entities/authoring';
import { EnrollmentContext } from '@/entities/enrollment';
import { QuizContext } from '@/entities/quiz';
import { NotificationContext } from '@/entities/notification';
import {
  authoringGateway,
  enrollmentGateway,
  quizGateway,
  notificationGateway,
  courseQueries,
  gateway,
  queryClient,
  session,
} from './runtime';
export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <AccountContext.Provider value={{ session, gateway }}>
        <CourseContext.Provider value={courseQueries}>
          <AuthoringContext.Provider value={authoringGateway}>
            <EnrollmentContext.Provider value={enrollmentGateway}>
              <QuizContext.Provider value={quizGateway}>
                <NotificationContext.Provider value={notificationGateway}>
                  {children}
                </NotificationContext.Provider>
              </QuizContext.Provider>
            </EnrollmentContext.Provider>
          </AuthoringContext.Provider>
        </CourseContext.Provider>
      </AccountContext.Provider>
    </QueryClientProvider>
  );
}
