import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { CourseContext, createCourseQueries } from '@/entities/course';
import { HttpError } from '@/shared/api';
import LessonPage from './LessonPage';
describe('lesson access states', () => {
  it('shows a locked notice instead of an invented payment flow', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const queries = createCourseQueries({
      request: vi.fn().mockRejectedValue(new HttpError(403, 'locked')),
      authorize: vi.fn(),
    });
    render(
      <QueryClientProvider client={client}>
        <CourseContext.Provider value={queries}>
          <MemoryRouter initialEntries={['/courses/1/modules/2/lessons/3']}>
            <Routes>
              <Route
                path="/courses/:courseId/modules/:moduleId/lessons/:lessonId"
                element={<LessonPage />}
              />
            </Routes>
          </MemoryRouter>
        </CourseContext.Provider>
      </QueryClientProvider>,
    );
    expect(await screen.findByRole('heading', { name: 'Закрытый урок' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /купить/i })).not.toBeInTheDocument();
    client.clear();
  });
});
