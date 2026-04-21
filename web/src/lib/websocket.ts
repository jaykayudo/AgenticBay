type MessageHandler = (data: unknown) => void;

export interface WSMessage {
  event: string;
  payload?: unknown;
  room?: string;
  from?: string;
}

class WebSocketClient {
  private ws: WebSocket | null = null;
  private handlers: Map<string, Set<MessageHandler>> = new Map();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private url = "";
  private shouldReconnect = true;

  connect(clientId: string): void {
    const wsBase = (process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000").replace(/^http/, "ws");
    this.url = `${wsBase}/ws/${clientId}`;
    this.shouldReconnect = true;
    this._connect();
  }

  private _connect(): void {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.reconnectDelay = 1000;
      this._emit("connect", null);
    };

    this.ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data as string);
        this._emit(msg.event, msg);
        this._emit("*", msg);
      } catch {
        this._emit("raw", event.data);
      }
    };

    this.ws.onclose = () => {
      this._emit("disconnect", null);
      if (this.shouldReconnect) {
        this.reconnectTimer = setTimeout(() => {
          this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
          this._connect();
        }, this.reconnectDelay);
      }
    };

    this.ws.onerror = (err) => {
      this._emit("error", err);
    };
  }

  send(event: string, payload?: unknown, room?: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ event, payload, room }));
    }
  }

  joinRoom(room: string): void {
    this.send("join_room", undefined, room);
  }

  leaveRoom(room: string): void {
    this.send("leave_room", undefined, room);
  }

  on(event: string, handler: MessageHandler): () => void {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set());
    }
    this.handlers.get(event)!.add(handler);
    return () => this.off(event, handler);
  }

  off(event: string, handler: MessageHandler): void {
    this.handlers.get(event)?.delete(handler);
  }

  private _emit(event: string, data: unknown): void {
    this.handlers.get(event)?.forEach((h) => h(data));
  }

  disconnect(): void {
    this.shouldReconnect = false;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export const wsClient = new WebSocketClient();
