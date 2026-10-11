import { Link } from 'react-router-dom';
import type { CourseDetail } from '@/entities/course';
import styles from './CourseOutline.module.css';
export function CourseOutline({ course }: { course: CourseDetail }) {
  return (
    <div className={styles.outline}>
      {course.modules.map((module) => (
        <section key={module.id} className={styles.module}>
          <div className={styles.title}>
            <h2>
              {module.position}. {module.title}
            </h2>
            <span className={module.is_preview ? styles.preview : styles.locked}>
              {module.is_preview ? 'Бесплатный просмотр' : 'Закрытый модуль'}
            </span>
          </div>
          <p>{module.description}</p>
          {module.lessons.length ? (
            <ol>
              {module.lessons.map((lesson) => (
                <li key={lesson.id}>
                  <Link
                    to={'/courses/' + course.id + '/modules/' + module.id + '/lessons/' + lesson.id}
                  >
                    {lesson.title}
                  </Link>
                  {!module.is_preview && <span className={styles.locked}> · Недоступно</span>}
                </li>
              ))}
            </ol>
          ) : (
            <p>В этом модуле пока нет уроков.</p>
          )}
        </section>
      ))}
    </div>
  );
}
