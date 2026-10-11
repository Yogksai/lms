import { readdirSync, readFileSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';

const layers = ['shared', 'entities', 'features', 'widgets', 'pages', 'app'];
const root = resolve('src');
const errors = [];
function walk(directory) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const file = join(directory, entry.name);
    if (entry.isDirectory()) walk(file);
    else if (/\.(ts|tsx)$/.test(file)) {
      const source = relative(root, file).split('/');
      const sourceRank = layers.indexOf(source[0]);
      if (sourceRank < 0 || file.endsWith('.test.ts') || file.endsWith('.test.tsx')) continue;
      for (const match of readFileSync(file, 'utf8').matchAll(
        /(?:from\s*|import\s*\()(['"])([^'"]+)\1/g,
      )) {
        const specifier = match[2];
        if (!specifier.startsWith('@/') && !specifier.startsWith('.')) continue;
        const target = (
          specifier.startsWith('@/')
            ? specifier.slice(2)
            : relative(root, resolve(directory, specifier))
        ).split('/');
        const targetRank = layers.indexOf(target[0]);
        if (
          targetRank > sourceRank ||
          (targetRank === sourceRank && sourceRank > 0 && sourceRank < 5 && target[1] !== source[1])
        )
          errors.push(`${relative(root, file)}: forbidden layer/slice import ${specifier}`);
        if (
          targetRank > 0 &&
          targetRank < 5 &&
          (source[0] !== target[0] || source[1] !== target[1]) &&
          target.length > 2 &&
          !/^index\.(ts|tsx)$/.test(target[2])
        )
          errors.push(`${relative(root, file)}: use the slice public API: ${specifier}`);
        if (file.includes('/model/') && targetRank === sourceRank && target[2] === 'ui')
          errors.push(`${relative(root, file)}: model cannot import UI`);
      }
    }
  }
}
walk(root);
if (errors.length) {
  console.error(errors.join('\n'));
  process.exitCode = 1;
} else console.log('Architecture boundaries passed.');
