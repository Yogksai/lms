import { describe, expect, it } from 'vitest';
import { accessSchema, hasFullAccess } from './model';
import type { CourseAccess } from './model';
const access: CourseAccess = {
  course_id: 10,
  available: true,
  enrolled: true,
  full_access: true,
  reasons: ['teacher_approval'],
  expires_at: '2026-10-12T10:00:00Z',
  request: null,
  grants: [],
};
describe('effective access', () => {
  it('treats the exact expiry instant as expired', () => {
    expect(hasFullAccess(access, Date.parse('2026-10-12T09:59:59Z'))).toBe(true);
    expect(hasFullAccess(access, Date.parse('2026-10-12T10:00:00Z'))).toBe(false);
    expect(hasFullAccess(access, Date.parse('2026-10-13T10:00:00Z'))).toBe(false);
  });
  it('does not confuse enrollment with full access', () => {
    expect(hasFullAccess({ ...access, full_access: false, reasons: [], expires_at: null })).toBe(
      false,
    );
  });
  it('supports staff access without a timed grant but never unpublished access', () => {
    const staff = {
      ...access,
      enrolled: false,
      reasons: ['admin'] as CourseAccess['reasons'],
      expires_at: null,
    };
    expect(hasFullAccess(staff)).toBe(true);
    expect(hasFullAccess({ ...staff, available: false })).toBe(false);
  });
  it('rejects unknown access reasons and malformed dates', () => {
    expect(accessSchema.safeParse({ ...access, reasons: ['paid'] }).success).toBe(false);
    expect(accessSchema.safeParse({ ...access, expires_at: 'tomorrow' }).success).toBe(false);
  });
});
