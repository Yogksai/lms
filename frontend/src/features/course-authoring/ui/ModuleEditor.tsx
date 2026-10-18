import { Link } from 'react-router-dom';
import type { Command, EditorModule } from '@/entities/authoring';
import { Button } from '@/shared/ui';
import { ModuleForm } from './Forms';
import { moveItem } from '../model/forms';
export function ModuleEditor({
  module,
  courseId,
  disabled,
  run,
}: {
  module: EditorModule;
  courseId: number;
  disabled: boolean;
  run: (command: Command) => Promise<unknown>;
}) {
  const path = `/modules/${module.id}`;
  const base = `/authoring/courses/${courseId}${path}/lessons`;
  return (
    <details className="authoring-card">
      <summary>
        {module.position}. {module.title} · {module.lessons.length} уроков
      </summary>
      <ModuleForm
        initial={{ title: module.title, description: module.description }}
        disabled={disabled}
        save={(body) => run({ path, method: 'PUT', body })}
      />
      <h3>Уроки</h3>
      {module.lessons.length === 0 && <p>В этом модуле пока нет уроков.</p>}
      <ol className="authoring-list">
        {module.lessons.map((lesson, index) => (
          <li key={lesson.id} className="authoring-row">
            <Link to={`${base}/${lesson.id}`}>{lesson.title}</Link>
            <div className="actions">
              <Button
                disabled={disabled || index === 0}
                aria-label={`Поднять урок ${lesson.title}`}
                onClick={() =>
                  void run({
                    path: path + '/lessons/order',
                    method: 'PUT',
                    body: {
                      ids: moveItem(
                        module.lessons.map((item) => item.id),
                        lesson.id,
                        -1,
                      ),
                    },
                  }).catch(() => undefined)
                }
              >
                ↑
              </Button>
              <Button
                disabled={disabled || index === module.lessons.length - 1}
                aria-label={`Опустить урок ${lesson.title}`}
                onClick={() =>
                  void run({
                    path: path + '/lessons/order',
                    method: 'PUT',
                    body: {
                      ids: moveItem(
                        module.lessons.map((item) => item.id),
                        lesson.id,
                        1,
                      ),
                    },
                  }).catch(() => undefined)
                }
              >
                ↓
              </Button>
              <Button
                disabled={disabled}
                onClick={() => {
                  if (
                    window.confirm(`Удалить урок «${lesson.title}»? Это действие нельзя отменить.`)
                  )
                    void run({ path: `${path}/lessons/${lesson.id}`, method: 'DELETE' }).catch(
                      () => undefined,
                    );
                }}
              >
                Удалить урок
              </Button>
            </div>
          </li>
        ))}
      </ol>
      {!disabled && <Link to={base + '/new'}>Добавить урок</Link>}
    </details>
  );
}
