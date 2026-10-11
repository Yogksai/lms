import { useQuery } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { useCourseQueries } from '@/entities/course';
import { CourseSearch } from '@/features/course-search';
import { errorMessage } from '@/shared/api';
import { Button, Heading, Notice } from '@/shared/ui';
import styles from './Catalog.module.css';
export default function CatalogPage() {
  const queries = useCourseQueries();
  const [params, setParams] = useSearchParams();
  const search = (params.get('search') ?? '').trim().slice(0, 200);
  const rawOffset = Number(params.get('offset') ?? 0);
  const offset = Number.isSafeInteger(rawOffset) && rawOffset >= 0 ? rawOffset : 0;
  const query = useQuery(queries.catalog(search, offset));
  const move = (next: number) =>
    setParams({ ...(search ? { search } : {}), ...(next ? { offset: String(next) } : {}) });
  return (
    <>
      <Heading>Курсы</Heading>
      <CourseSearch
        key={search}
        initialValue={search}
        onSearch={(value) => setParams(value ? { search: value } : {})}
      />
      {query.isPending ? (
        <Notice>Загружаем курсы…</Notice>
      ) : query.isError ? (
        <Notice error>
          {errorMessage(query.error)}{' '}
          <Button onClick={() => void query.refetch()}>Повторить</Button>
        </Notice>
      ) : (
        <>
          {query.data.items.length ? (
            <ul className={styles.list}>
              {query.data.items.map((course) => (
                <li key={course.id}>
                  <Link className={styles.card} to={'/courses/' + course.id}>
                    <span className={styles.title}>{course.title}</span>
                    <span className={styles.description}>{course.description}</span>
                    <span className={styles.open}>К курсу →</span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <Notice>Курсы не найдены. Попробуйте другой запрос.</Notice>
          )}
          <nav className="actions" aria-label="Страницы каталога">
            <Button disabled={offset === 0} onClick={() => move(Math.max(0, offset - 10))}>
              Назад
            </Button>
            <span>Всего курсов: {query.data.total}</span>
            <Button
              disabled={offset + query.data.limit >= query.data.total}
              onClick={() => move(offset + query.data.limit)}
            >
              Далее
            </Button>
          </nav>
        </>
      )}
    </>
  );
}
