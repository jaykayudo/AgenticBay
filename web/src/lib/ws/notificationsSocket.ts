import { normalizeNotification, type Notification, type RawNotification } from "@/lib/api/notifications";
import { tokenManager } from "@/lib/auth/tokenManager";

type NotificationHandler = (notification: Notification) => void;

type NotificationsSocket = {
  close: () => void;
};

function buildNotificationsSocketUrl(token: string) {
  const wsBase = (process.env.NEXT_PUBLIC_WS_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "ws://localhost:8000").replace(
    /^http/,
    "ws"
  );
  return `${wsBase}/api/notifications/ws?token=${encodeURIComponent(token)}`;
}

export function connectNotificationsSocket(onNotification: NotificationHandler): NotificationsSocket {
  let socket: WebSocket | null = null;
  let reconnectTimer: number | null = null;
  let reconnectDelay = 1000;
  let closedByClient = false;

  const connect = () => {
    const token = tokenManager.getAccessToken();
    if (!token || closedByClient) {
      return;
    }

    socket = new WebSocket(buildNotificationsSocketUrl(token));

    socket.onopen = () => {
      reconnectDelay = 1000;
    };

    socket.onmessage = (event) => {
      try {
        onNotification(normalizeNotification(JSON.parse(event.data as string) as RawNotification));
      } catch {
        // Ignore malformed push payloads and wait for the next message.
      }
    };

    socket.onclose = () => {
      if (closedByClient) {
        return;
      }

      reconnectTimer = window.setTimeout(() => {
        reconnectDelay = Math.min(reconnectDelay * 2, 30_000);
        connect();
      }, reconnectDelay);
    };
  };

  connect();

  return {
    close: () => {
      closedByClient = true;
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
      }
      socket?.close();
    },
  };
}
