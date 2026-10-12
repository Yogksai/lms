import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { Link } from 'react-router-dom';
import styles from './Ui.module.css';
export function Button({ className = '', ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={styles.button + ' ' + className} {...props} />;
}
export function LinkButton({ to, children }: { to: string; children: ReactNode }) {
  return (
    <Link className={styles.button} to={to}>
      {children}
    </Link>
  );
}
export function Notice({ children, error = false }: { children: ReactNode; error?: boolean }) {
  return (
    <div className={styles.notice} role={error ? 'alert' : 'status'}>
      {children}
    </div>
  );
}
export function Heading({ children }: { children: ReactNode }) {
  return (
    <h1 className={styles.heading}>
      <span>{children}</span>
    </h1>
  );
}
