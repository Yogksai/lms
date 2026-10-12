import { z } from 'zod';
import { userSchema } from '@/shared/model/identity';

const id = z.number().int().positive();
const timestamp = z.iso.datetime({ offset: true });
export const requestStatusSchema = z.enum(['pending', 'approved', 'rejected', 'cancelled']);
export const requestSchema = z.object({
  id,
  course_id: id,
  user_id: id,
  message: z.string(),
  status: requestStatusSchema,
  created_at: timestamp,
  decided_at: timestamp.nullable(),
  decided_by: id.nullable(),
  decision_note: z.string(),
});
export const grantSchema = z.object({
  id,
  course_id: id,
  user_id: id,
  source: z.enum(['teacher_approval', 'admin_grant']),
  request_id: id.nullable(),
  granted_by: id.nullable(),
  created_at: timestamp,
  expires_at: timestamp,
  revoked_at: timestamp.nullable(),
  revoked_by: id.nullable(),
});
export const accessSchema = z.object({
  course_id: id,
  available: z.boolean(),
  enrolled: z.boolean(),
  full_access: z.boolean(),
  reasons: z.array(z.enum(['admin', 'assigned_teacher', 'teacher_approval', 'admin_grant'])),
  expires_at: timestamp.nullable(),
  request: requestSchema.nullable(),
  grants: z.array(grantSchema),
});
const pagination = z.object({
  total: z.number().int().nonnegative(),
  limit: id,
  offset: z.number().int().nonnegative(),
});
export const enrollmentPageSchema = pagination.extend({
  items: z.array(
    z.object({
      course: z.object({ id, slug: z.string(), title: z.string(), description: z.string() }),
      enrolled_at: timestamp,
      available: z.boolean(),
    }),
  ),
});
export const requestPageSchema = pagination.extend({
  items: z.array(requestSchema.extend({ student: userSchema })),
});
export const grantPageSchema = pagination.extend({
  items: z.array(grantSchema.extend({ student: userSchema, active: z.boolean() })),
});
export type CourseAccess = z.infer<typeof accessSchema>;
export type AccessRequest = z.infer<typeof requestSchema>;
export type ManagedRequest = z.infer<typeof requestPageSchema>['items'][number];
export type ManagedGrant = z.infer<typeof grantPageSchema>['items'][number];
export type RequestStatus = z.infer<typeof requestStatusSchema>;
export type AccessCommand = { path: string; method: 'POST' | 'PUT' | 'DELETE'; body?: unknown };
export const requestLabels: Record<RequestStatus, string> = {
  pending: 'На рассмотрении',
  approved: 'Одобрена',
  rejected: 'Отклонена',
  cancelled: 'Отменена',
};
export const sourceLabels = {
  teacher_approval: 'Одобрение заявки',
  admin_grant: 'Доступ от администратора',
};
export function hasFullAccess(access: CourseAccess, now = Date.now()): boolean {
  return (
    access.available &&
    access.full_access &&
    (access.expires_at === null || Date.parse(access.expires_at) > now)
  );
}
