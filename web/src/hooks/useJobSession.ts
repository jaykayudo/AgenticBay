"use client";

import { useEffect, useRef, useState } from "react";

import {
  JobSessionSocket,
  type JobSessionMessage,
  type JobSessionSocketState,
} from "@/lib/ws/jobSessionSocket";

export type SessionFeedItem = {
  id: string;
  type: string;
  data: unknown;
  timestamp: string;
};

function makeId() {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function getMessageType(msg: JobSessionMessage) {
  return String(msg.type ?? msg.event ?? "MESSAGE").toUpperCase();
}

function nextPhaseForMessage(type: string) {
  if (type === "CONNECT" || type === "CONNECTED") return "CONNECTED";
  if (type === "PAYMENT" || type === "PAYMENT_REQUIRED") return "AWAITING_PAYMENT";
  if (type === "CLOSE_APPEAL" || type === "CLOSE_JOB") return "CLOSING";
  if (type === "SESSION_COMPLETE" || type === "RESULT") return "COMPLETED";
  if (type === "ERROR") return "FAILED";
  return null;
}

export function useJobSession(sessionId: string, token: string, socketUrl?: string) {
  const [feed, setFeed] = useState<SessionFeedItem[]>([]);
  const [phase, setPhase] = useState("STARTED");
  const [connectionState, setConnectionState] = useState<JobSessionSocketState>("idle");
  const socketRef = useRef<JobSessionSocket | null>(null);

  useEffect(() => {
    if (!sessionId || !token) {
      return;
    }

    const socket = new JobSessionSocket(sessionId, token, socketUrl);
    socketRef.current = socket;

    const unsubscribeState = socket.subscribeState(setConnectionState);
    const unsubscribe = socket.subscribe((msg) => {
      const type = getMessageType(msg);
      setFeed((prev) => [
        ...prev,
        {
          id: makeId(),
          type,
          data: msg.data ?? msg.payload ?? msg.message ?? msg,
          timestamp: new Date().toISOString(),
        },
      ]);

      const nextPhase = nextPhaseForMessage(type);
      if (nextPhase) {
        setPhase(nextPhase);
      }
    });

    void socket.connect().catch(() => {
      setConnectionState("reconnecting");
    });

    return () => {
      unsubscribe();
      unsubscribeState();
      socket.close();
      socketRef.current = null;
    };
  }, [sessionId, socketUrl, token]);

  return {
    feed,
    phase,
    connectionState,
    sendCommand: (type: string, data?: unknown) => socketRef.current?.sendCommand(type, data),
  };
}
