import { useState } from 'react';
import { Button } from '@/shared/ui';
export function CourseSearch({
  initialValue,
  onSearch,
}: {
  initialValue: string;
  onSearch: (value: string) => void;
}) {
  const [value, setValue] = useState(initialValue);
  return (
    <form
      className="actions"
      onSubmit={(event) => {
        event.preventDefault();
        onSearch(value.trim());
      }}
    >
      <label>
        Поиск курсов
        <input
          type="search"
          name="search"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          maxLength={200}
          placeholder="Название курса"
        />
      </label>
      <Button type="submit">Найти</Button>
    </form>
  );
}
