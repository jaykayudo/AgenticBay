"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useChatModal } from "@/context/ChatModalContext";
import {
  UserAgentSocket,
  type IncomingMessage,
  type UserAgentSocketState,
} from "@/lib/ws/userAgentSocket";

export type ChatMessage = {
  id: string;
  from: "user" | "agent" | "system";
  message: string;
  timestamp: string;
  payload?: unknown;
};

function makeId() {
  return (
    globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`
  );
}

function messageText(data: Record<string, unknown>) {
  return String(data.message ?? data.body ?? data.content ?? data.result ?? "Session update");
}

export function useUserAgentChat(sessionId: string, token: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [connectionState, setConnectionState] = useState<UserAgentSocketState>("idle");
  const socketRef = useRef<UserAgentSocket | null>(null);
  const { showPaymentModal, showPromptModal } = useChatModal();

  useEffect(() => {
    if (!sessionId || !token) {
      return;
    }

    const socket = new UserAgentSocket(sessionId, token);
    socketRef.current = socket;

    const unsubscribeStatus = socket.subscribeStatus(setConnectionState);
    const unsubscribe = socket.subscribe((msg: IncomingMessage) => {
      switch (msg.type) {
        case "AGENT_MESSAGE":
          setMessages((prev) => [
            ...prev,
            {
              id: makeId(),
              from: "agent",
              message: messageText(msg.data),
              timestamp: msg.data.timestamp ?? new Date().toISOString(),
              payload: msg.data,
            },
          ]);
          break;

        case "PAYMENT_CONFIRMATION_MODAL":
          showPaymentModal(msg.data, (response) => {
            socket.send({
              type: "MODAL_RESPONSE",
              data: { modal_type: "payment", ...response },
            });
          });
          break;

        case "USER_PROMPT_MODAL":
          showPromptModal(msg.data, (response) => {
            socket.send({
              type: "MODAL_RESPONSE",
              data: { modal_type: "prompt", ...response },
            });
          });
          break;

        case "SESSION_COMPLETE":
          setMessages((prev) => [
            ...prev,
            {
              id: makeId(),
              from: "system",
              message: messageText(msg.data),
              timestamp: new Date().toISOString(),
              payload: msg.data,
            },
          ]);
          setIsComplete(true);
          break;
      }
    });

    void socket.connect().catch(() => {
      setConnectionState("reconnecting");
    });

    return () => {
      unsubscribe();
      unsubscribeStatus();
      socket.close();
      socketRef.current = null;
    };
  }, [sessionId, showPaymentModal, showPromptModal, token]);

  const sendMessage = useCallback((text: string) => {
    const message = text.trim();
    if (!message) {
      return;
    }

    setMessages((prev) => [
      ...prev,
      {
        id: makeId(),
        from: "user",
        message,
        timestamp: new Date().toISOString(),
      },
    ]);
    socketRef.current?.send({
      type: "USER_MESSAGE",
      data: { message },
    });
  }, []);

  const cancel = useCallback(() => {
    socketRef.current?.send({ type: "CANCEL_SESSION" });
    setIsComplete(true);
    setMessages((prev) => [
      ...prev,
      {
        id: makeId(),
        from: "system",
        message: "Session cancelled.",
        timestamp: new Date().toISOString(),
      },
    ]);
  }, []);

  return { messages, isComplete, connectionState, sendMessage, cancel };
}
