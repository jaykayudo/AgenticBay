import type { AxiosResponse } from "axios";

import { authApiClient } from "@/lib/api/client";

export type Notification = {
  id: string;
  notificationType: string;
  title: string;
  body: string;
  data: Record<string, unknown>;
  isRead: boolean;
  readAt: string | null;
  createdAt: string;
};

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
};

type RawNotification = Omit<Notification, "notificationType"> & {
  notificationType?: string;
  type?: string;
};

type RawNotificationListResponse = {
  items: RawNotification[];
  unreadCount: number;
  meta: {
    total: number;
    page: number;
    pageSize?: number;
    page_size?: number;
    hasNext?: boolean;
    has_next?: boolean;
  };
};

export type NotificationListResponse = PaginatedResponse<Notification> & {
  unreadCount: number;
};

function normalizeNotification(notification: RawNotification): Notification {
  return {
    id: notification.id,
    notificationType: notification.notificationType ?? notification.type ?? "GENERAL",
    title: notification.title,
    body: notification.body,
    data: notification.data ?? {},
    isRead: notification.isRead,
    readAt: notification.readAt,
    createdAt: notification.createdAt,
  };
}

function normalizeList(response: RawNotificationListResponse): NotificationListResponse {
  return {
    items: response.items.map(normalizeNotification),
    unreadCount: response.unreadCount,
    total: response.meta.total,
    page: response.meta.page,
    page_size: response.meta.pageSize ?? response.meta.page_size ?? response.items.length,
    has_next: response.meta.hasNext ?? response.meta.has_next ?? false,
  };
}

export const notificationsApi = {
  async list(page = 1): Promise<AxiosResponse<NotificationListResponse>> {
    const response = await authApiClient.get<RawNotificationListResponse>("/notifications", {
      params: { page },
    });
    return { ...response, data: normalizeList(response.data) };
  },

  async markRead(notificationId: string): Promise<AxiosResponse<Notification>> {
    const response = await authApiClient.patch<RawNotification>(
      `/notifications/${notificationId}/read`
    );
    return { ...response, data: normalizeNotification(response.data) };
  },

  markAllRead(): Promise<AxiosResponse<{ updated: number }>> {
    return authApiClient.patch("/notifications/read-all");
  },

  delete(notificationId: string): Promise<AxiosResponse<void>> {
    return authApiClient.delete(`/notifications/${notificationId}`);
  },

  async unreadCount(): Promise<AxiosResponse<{ count: number }>> {
    const response = await this.list(1);
    return { ...response, data: { count: response.data.unreadCount } };
  },
};

export { normalizeNotification };
export type { RawNotification };
