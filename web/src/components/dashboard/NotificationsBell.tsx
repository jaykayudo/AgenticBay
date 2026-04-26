"use client";

import { Bell, CheckCheck, LoaderCircle, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useNotifications } from "@/hooks/useNotifications";
import { cn } from "@/lib/utils";

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

export function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const notifications = useNotifications();

  useEffect(() => {
    if (!open) {
      return;
    }

    const handlePointerDown = (event: PointerEvent) => {
      if (!panelRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    window.addEventListener("pointerdown", handlePointerDown);
    return () => window.removeEventListener("pointerdown", handlePointerDown);
  }, [open]);

  return (
    <div ref={panelRef} className="relative">
      <button
        type="button"
        aria-label="Open notifications"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="relative grid h-11 w-11 place-items-center rounded-full border border-[var(--border)] bg-[var(--surface)] text-[var(--text)] shadow-[var(--shadow-soft)] transition hover:bg-[var(--surface-2)]"
      >
        <Bell className="h-4.5 w-4.5" />
        {notifications.unreadCount > 0 ? (
          <span className="absolute -top-1 -right-1 grid min-h-5 min-w-5 place-items-center rounded-full bg-[var(--danger)] px-1.5 text-[11px] font-semibold text-white">
            {notifications.unreadCount > 99 ? "99+" : notifications.unreadCount}
          </span>
        ) : null}
      </button>

      {open ? (
        <section className="absolute right-0 z-50 mt-3 w-[min(24rem,calc(100vw-2rem))] overflow-hidden rounded-[1.25rem] border border-[var(--border)] bg-[var(--surface)] shadow-[0_24px_80px_rgba(15,23,42,0.18)]">
          <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] px-4 py-3">
            <div>
              <p className="font-semibold text-[var(--text)]">Notifications</p>
              <p className="mt-0.5 text-xs text-[var(--text-muted)]">
                {notifications.unreadCount} unread
              </p>
            </div>
            <button
              type="button"
              disabled={notifications.unreadCount === 0}
              onClick={() => void notifications.markAllRead()}
              className="inline-flex h-9 items-center gap-2 rounded-full border border-[var(--border)] px-3 text-xs font-medium text-[var(--text-muted)] transition hover:text-[var(--text)] disabled:opacity-45"
            >
              <CheckCheck className="h-3.5 w-3.5" />
              Mark all
            </button>
          </div>

          <div className="max-h-[28rem] overflow-y-auto p-2">
            {notifications.isLoading ? (
              <div className="flex items-center gap-3 p-4 text-sm text-[var(--text-muted)]">
                <LoaderCircle className="h-4 w-4 animate-spin text-[var(--primary)]" />
                Loading notifications
              </div>
            ) : null}

            {!notifications.isLoading && notifications.notifications.length === 0 ? (
              <div className="p-4 text-sm leading-6 text-[var(--text-muted)]">
                No notifications yet.
              </div>
            ) : null}

            {notifications.notifications.map((notification) => (
              <article
                key={notification.id}
                className={cn(
                  "group rounded-2xl border p-3 transition",
                  notification.isRead
                    ? "border-transparent bg-transparent hover:bg-[var(--surface-2)]"
                    : "border-[var(--primary-soft)] bg-[var(--primary-soft)]"
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <button
                    type="button"
                    onClick={() =>
                      notification.isRead ? undefined : void notifications.markRead(notification.id)
                    }
                    className="min-w-0 flex-1 text-left"
                  >
                    <p className="text-sm font-semibold text-[var(--text)]">{notification.title}</p>
                    <p className="mt-1 line-clamp-2 text-sm leading-6 text-[var(--text-muted)]">
                      {notification.body}
                    </p>
                    <p className="mt-2 text-xs text-[var(--text-muted)]">
                      {dateFormatter.format(new Date(notification.createdAt))}
                    </p>
                  </button>
                  <button
                    type="button"
                    aria-label="Delete notification"
                    onClick={() => void notifications.deleteNotification(notification.id)}
                    className="grid h-8 w-8 shrink-0 place-items-center rounded-full text-[var(--text-muted)] opacity-80 transition group-hover:opacity-100 hover:bg-[var(--surface)] hover:text-[var(--danger)]"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
