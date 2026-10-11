import { useState } from 'react';
import { youtubeEmbedUrl } from '@/entities/course';
import type { Lesson } from '@/entities/course';
import { Button, Notice } from '@/shared/ui';
import styles from './LessonViewer.module.css';
export function LessonViewer({ lesson }: { lesson: Lesson }) {
  const [playing, setPlaying] = useState(false);
  const embed = youtubeEmbedUrl(lesson.video_url);
  return (
    <>
      {embed ? (
        <div className={styles.video}>
          {playing ? (
            <iframe
              src={embed}
              title={lesson.title + ' — видеогид'}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              referrerPolicy="strict-origin-when-cross-origin"
            />
          ) : (
            <div className={styles.placeholder}>
              <Button aria-label="Загрузить видео" onClick={() => setPlaying(true)}>
                <span className={styles.play} aria-hidden="true">
                  ▶
                </span>
                <span className={styles.caption}>Смотреть видео</span>
              </Button>
              <p>Видео загружается с YouTube после нажатия.</p>
            </div>
          )}
        </div>
      ) : (
        <Notice error>Ссылка на видеогид недоступна.</Notice>
      )}
      <section className={styles.summary}>
        <h2>
          <span>Конспект</span> урока
        </h2>
        <div className={styles.text}>{lesson.summary}</div>
      </section>
    </>
  );
}
