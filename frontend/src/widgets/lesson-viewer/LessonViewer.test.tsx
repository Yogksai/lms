import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { LessonViewer } from './LessonViewer';
const lesson = {
  id: 1,
  module_id: 1,
  title: 'Values',
  position: 1,
  summary: 'Summary text',
  video_url: 'https://youtu.be/rfscVS0vtbw',
};
describe('lesson viewer', () => {
  it('loads an external player only after user consent', () => {
    const { container } = render(<LessonViewer lesson={lesson} />);
    expect(container.querySelector('iframe')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Загрузить видео' }));
    expect(screen.getByTitle('Values — видеогид')).toHaveAttribute(
      'src',
      'https://www.youtube-nocookie.com/embed/rfscVS0vtbw',
    );
  });
  it('renders summaries as text, never as HTML', () => {
    const { container } = render(
      <LessonViewer lesson={{ ...lesson, summary: '<script>alert(1)</script>' }} />,
    );
    expect(screen.getByText('<script>alert(1)</script>')).toBeInTheDocument();
    expect(container.querySelector('script')).toBeNull();
  });
});
