import { describe, expect, it } from 'vitest';
import { registerSchema, profileSchema } from './forms';
const valid = {
  name: ' Student ',
  email: 'student@example.com',
  password: 'valid-password',
  confirmPassword: 'valid-password',
};
describe('account form validation', () => {
  it('trims the display name', () => {
    expect(registerSchema.parse(valid).name).toBe('Student');
  });
  it('rejects mismatched confirmation', () => {
    expect(registerSchema.safeParse({ ...valid, confirmPassword: 'different' }).success).toBe(
      false,
    );
  });
  it('enforces the bcrypt UTF-8 byte limit', () => {
    const password = 'я'.repeat(37);
    expect(
      registerSchema.safeParse({ ...valid, password, confirmPassword: password }).success,
    ).toBe(false);
  });
  it('rejects blank profile names', () => {
    expect(profileSchema.safeParse({ name: '  ' }).success).toBe(false);
  });
});
