"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";

import { wsClient, type WSMessage } from "@/lib/websocket";

export function useWebSocket(clientId: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);

  useEffect(() => {
    wsClient.connect(clientId);

    const offConnect = wsClient.on("connect", () => setIsConnected(true));
    const offDisconnect = wsClient.on("disconnect", () => setIsConnected(false));
    const offAll = wsClient.on("*", (msg) => setLastMessage(msg as WSMessage));

    return () => {
      offConnect();
      offDisconnect();
      offAll();
      wsClient.disconnect();
    };
  }, [clientId]);

  return { isConnected, lastMessage, ws: wsClient };
}

export function useWSEvent<T = unknown>(event: string, handler: (data: T) => void) {
  const handlerRef = useRef(handler);

  // Sync the latest handler after paint so we never read a stale closure,
  // and never mutate the ref during the render phase.
  useLayoutEffect(() => {
    handlerRef.current = handler;
  });

  useEffect(() => {
    const off = wsClient.on(event, (data) => handlerRef.current(data as T));
    return off;
  }, [event]);
}
