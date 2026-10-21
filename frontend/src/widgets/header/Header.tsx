import { NavLink } from 'react-router-dom';
import { useCurrentUser } from '@/entities/session';
import { LogoutButton } from '@/features/auth';
import styles from './Header.module.css';
export function Header() {
  const user = useCurrentUser();
  return (
    <>
      <a className="skip-link" href="#main-content">
        К содержимому
      </a>
      <header className={styles.header}>
        <NavLink className={styles.brand} to="/courses">
          MathWithMe
        </NavLink>
        <nav aria-label="Основная навигация" className={styles.nav}>
          <NavLink to="/courses" className={({ isActive }) => (isActive ? styles.active : '')}>
            Курсы
          </NavLink>
          {user && ['teacher', 'admin'].includes(user.role) && (
            <NavLink
              to="/authoring/courses"
              className={({ isActive }) => (isActive ? styles.active : '')}
            >
              Редактор
            </NavLink>
          )}
          {user?.role === 'admin' && (
            <NavLink
              to="/admin/users"
              className={({ isActive }) => (isActive ? styles.active : '')}
            >
              Пользователи
            </NavLink>
          )}
        </nav>
        <div className={styles.account}>
          {user ? (
            <>
              <NavLink to="/profile" className={styles.identity}>
                <span aria-hidden="true" className={styles.avatar}>
                  {user.name.slice(0, 1)}
                </span>
                <span>{user.name}</span>
              </NavLink>
              <LogoutButton />
            </>
          ) : (
            <>
              <NavLink to="/login">Войти</NavLink>
              <NavLink to="/register">Регистрация</NavLink>
            </>
          )}
        </div>
      </header>
    </>
  );
}
