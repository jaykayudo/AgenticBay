"use client";

import { useEffect } from "react";
import useSWR from "swr";

import {
  notificationsApi,
  type Notification,
  type NotificationListResponse,
} from "@/lib/api/notifications";
import { connectNotificationsSocket } from "@/lib/ws/notificationsSocket";

export function useNotifications(page = 1) {
  const { data, error, isLoading, mutate } = useSWR(["/notifications", page], () =>
    notificationsApi.list(page).then((response) => response.data)
  );

  const { data: countData, mutate: mutateCount } = useSWR("/notifications/unread-count", () =>
    notificationsApi.unreadCount().then((response) => response.data)
  );

  useEffect(() => {
    const ws = connectNotificationsSocket((newNotification) => {
      void mutate(
        (current): NotificationListResponse | undefined => {
          if (!current) {
            return current;
          }

          if (current.items.some((item) => item.id === newNotification.id)) {
            return current;
          }

          return {
            ...current,
            items: [newNotification, ...current.items],
            unreadCount: current.unreadCount + (newNotification.isRead ? 0 : 1),
            total: current.total + 1,
          };
        },
        { revalidate: true }
      );
      void mutateCount();
    });

    return () => ws.close();
  }, [mutate, mutateCount]);

  const refreshAll = async () => {
    await Promise.all([mutate(), mutateCount()]);
  };

  const markRead = async (id: string) => {
    const previous = data;
    const wasUnread = previous?.items.find((item) => item.id === id)?.isRead === false;
    await mutate(
      previous
        ? {
            ...previous,
            items: previous.items.map((item) =>
              item.id === id ? { ...item, isRead: true, readAt: new Date().toISOString() } : item
            ),
            unreadCount: Math.max(0, previous.unreadCount - (wasUnread ? 1 : 0)),
          }
        : previous,
      false
    );
    await mutateCount(
      (current) => ({
        count: Math.max(0, (current?.count ?? previous?.unreadCount ?? 0) - (wasUnread ? 1 : 0)),
      }),
      false
    );

    try {
      const { data: updated } = await notificationsApi.markRead(id);
      await mutate(
        (current) =>
          current
            ? {
                ...current,
                items: current.items.map((item) => (item.id === id ? updated : item)),
              }
            : current,
        { revalidate: true }
      );
      await mutateCount();
    } catch (error) {
      await mutate(previous, false);
      await mutateCount();
      throw error;
    }
  };

  const markAllRead = async () => {
    await notificationsApi.markAllRead();
    await mutate((current) => {
      if (!current) {
        return current;
      }

      return {
        ...current,
        items: current.items.map((item) => ({
          ...item,
          isRead: true,
          readAt: item.readAt ?? new Date().toISOString(),
        })),
        unreadCount: 0,
      };
    });
    await mutateCount({ count: 0 }, { revalidate: true });
  };

  const deleteNotification = async (id: string) => {
    await notificationsApi.delete(id);
    await refreshAll();
  };

  return {
    notifications: data?.items ?? ([] as Notification[]),
    unreadCount: countData?.count ?? data?.unreadCount ?? 0,
    total: data?.total ?? 0,
    page: data?.page ?? page,
    pageSize: data?.page_size ?? 20,
    hasNext: data?.has_next ?? false,
    isLoading,
    error,
    refresh: refreshAll,
    markRead,
    markAllRead,
    deleteNotification,
  };
}
