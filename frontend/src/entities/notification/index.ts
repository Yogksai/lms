import { createContext, useContext } from 'react';
import { queryOptions } from '@tanstack/react-query';
import { z } from 'zod';
import type { HttpClient } from '@/shared/api';
const notificationSchema = z.object({
  id: z.number().int().positive(),
  title: z.string(),
  message: z.string(),
  link: z.string().regex(/^\/courses\/\d+\/attempts\/[0-9a-f-]{36}$/i),
  created_at: z.iso.datetime({ offset: true }),
  read_at: z.iso.datetime({ offset: true }).nullable(),
});
export const notificationPageSchema = z.object({
  items: z.array(notificationSchema),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
});
export const notificationKey = (userId: number) => ['private', 'notifications', userId] as const;
export function createNotificationGateway(http: HttpClient) {
  return {
    inbox(userId: number, offset: number) {
      return queryOptions({
        queryKey: [...notificationKey(userId), offset],
        staleTime: 0,
        refetchInterval: 30000,
        queryFn: async ({ signal }) =>
          notificationPageSchema.parse(
            await http.request(`/me/notifications?limit=20&offset=${offset}`, {
              authenticated: true,
              signal,
            }),
          ),
      });
    },
    async read(id: number) {
      await http.request(`/me/notifications/${id}/read`, { method: 'POST', authenticated: true });
    },
  };
}
type NotificationGateway = ReturnType<typeof createNotificationGateway>;
export const NotificationContext = createContext<NotificationGateway | null>(null);
export function useNotificationGateway() {
  const gateway = useContext(NotificationContext);
  if (!gateway) throw new Error('Notification provider is missing');
  return gateway;
}
