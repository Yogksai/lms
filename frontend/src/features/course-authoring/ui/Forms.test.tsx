import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { CourseForm, LessonForm } from './Forms';
describe('authoring forms', () => {
  it('blocks invalid course data before submitting', async () => {
    const save = vi.fn();
    render(<CourseForm initial={{ title: '', slug: '', description: '' }} save={save} />);
    await userEvent.click(screen.getByRole('button', { name: 'Сохранить курс' }));
    expect(await screen.findByText('Введите название')).toBeInTheDocument();
    expect(save).not.toHaveBeenCalled();
  });
  it('preserves unsaved text when the API rejects a save', async () => {
    const save = vi.fn().mockRejectedValue(new Error('conflict'));
    render(
      <LessonForm
        initial={{
          title: 'Lesson',
          summary: 'Original',
          video_url: 'https://youtu.be/dQw4w9WgXcQ',
        }}
        save={save}
      />,
    );
    await userEvent.clear(screen.getByLabelText('Текст конспекта'));
    await userEvent.type(screen.getByLabelText('Текст конспекта'), 'Unsaved summary');
    await userEvent.click(screen.getByRole('button', { name: 'Сохранить урок' }));
    expect(save).toHaveBeenCalledWith({
      title: 'Lesson',
      summary: 'Unsaved summary',
      video_url: 'https://youtu.be/dQw4w9WgXcQ',
    });
    expect(screen.getByLabelText('Текст конспекта')).toHaveValue('Unsaved summary');
  });
  it('disables editing for non-draft courses', () => {
    render(
      <LessonForm
        initial={{ title: 'Lesson', summary: 'Text', video_url: 'https://youtu.be/dQw4w9WgXcQ' }}
        save={vi.fn()}
        disabled
      />,
    );
    expect(screen.getByLabelText('Название урока')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Сохранить урок' })).toBeDisabled();
  });
});
