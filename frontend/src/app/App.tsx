import { Component, lazy, Suspense } from 'react';
import type { ReactNode } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Header } from '@/widgets/header';
import { Button, Notice } from '@/shared/ui';
import { Providers } from './Providers';
const CatalogPage = lazy(() => import('@/pages/catalog'));
const CoursePage = lazy(() => import('@/pages/course'));
const LessonPage = lazy(() => import('@/pages/lesson'));
const LoginPage = lazy(() => import('@/pages/login'));
const RegisterPage = lazy(() => import('@/pages/register'));
const ProfilePage = lazy(() => import('@/pages/profile'));
const AuthoringCatalogPage = lazy(() => import('@/pages/authoring-catalog'));
const AuthoringCoursePage = lazy(() => import('@/pages/authoring-course'));
const AuthoringLessonPage = lazy(() => import('@/pages/authoring-lesson'));
const AdminUsersPage = lazy(() => import('@/pages/admin-users'));
const MyCoursesPage = lazy(() => import('@/pages/my-courses'));
class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <Notice error>
        Не удалось загрузить страницу.{' '}
        <Button onClick={() => window.location.reload()}>Перезагрузить</Button>
      </Notice>
    ) : (
      this.props.children
    );
  }
}
export function App() {
  return (
    <ErrorBoundary>
      <Providers>
        <BrowserRouter>
          <Header />
          <main id="main-content">
            <Suspense fallback={<Notice>Загружаем страницу…</Notice>}>
              <Routes>
                <Route path="/" element={<Navigate to="/courses" replace />} />
                <Route path="/courses" element={<CatalogPage />} />
                <Route path="/courses/:courseId" element={<CoursePage />} />
                <Route
                  path="/courses/:courseId/modules/:moduleId/lessons/:lessonId"
                  element={<LessonPage />}
                />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route path="/profile" element={<ProfilePage />} />
                <Route path="/authoring/courses" element={<AuthoringCatalogPage />} />
                <Route path="/authoring/courses/:courseId" element={<AuthoringCoursePage />} />
                <Route
                  path="/authoring/courses/:courseId/modules/:moduleId/lessons/:lessonId"
                  element={<AuthoringLessonPage />}
                />
                <Route path="/admin/users" element={<AdminUsersPage />} />
                <Route path="/my-courses" element={<MyCoursesPage />} />
                <Route
                  path="*"
                  element={
                    <Notice error>
                      Страница не найдена. <a href="/courses">К курсам</a>
                    </Notice>
                  }
                />
              </Routes>
            </Suspense>
          </main>
        </BrowserRouter>
      </Providers>
    </ErrorBoundary>
  );
}
