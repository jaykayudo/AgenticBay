export type JobSessionSocketState = "idle" | "connecting" | "connected" | "reconnecting" | "closed";

export type JobSessionMessage = {
  type?: string;
  event?: string;
  data?: unknown;
  payload?: unknown;
  message?: string | null;
  [key: string]: unknown;
};

type MessageListener = (msg: JobSessionMessage) => void;
type StateListener = (state: JobSessionSocketState) => void;

function buildSocketUrl(sessionId: string, token: string, socketUrl?: string) {
  if (socketUrl) {
    const url = new URL(socketUrl);
    url.searchParams.set("token", token);
    return url.toString();
  }

  const wsBase = (
    process.env.NEXT_PUBLIC_WS_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    "ws://localhost:8000"
  ).replace(/^http/, "ws");
  return `${wsBase}/ws/user-agent/${encodeURIComponent(sessionId)}?token=${encodeURIComponent(token)}`;
}

export class JobSessionSocket {
  private ws: WebSocket | null = null;
  private listeners: Set<MessageListener> = new Set();
  private stateListeners: Set<StateListener> = new Set();
  private reconnectTimer: number | null = null;
  private reconnectAttempts = 0;
  private maxReconnect = 5;
  private closedByClient = false;
  private state: JobSessionSocketState = "idle";

  constructor(
    private sessionId: string,
    private token: string,
    private socketUrl?: string
  ) {}

  connect(): Promise<void> {
    this.closedByClient = false;
    return this.openSocket();
  }

  sendCommand(type: string, data?: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }));
    }
  }

  subscribe(cb: MessageListener): () => void {
    this.listeners.add(cb);
    return () => {
      this.listeners.delete(cb);
    };
  }

  subscribeState(cb: StateListener): () => void {
    this.stateListeners.add(cb);
    cb(this.state);
    return () => {
      this.stateListeners.delete(cb);
    };
  }

  close(): void {
    this.closedByClient = true;
    this.maxReconnect = 0;
    if (this.reconnectTimer) {
      window.clearTimeout(this.reconnectTimer);
    }
    this.setState("closed");
    this.ws?.close();
  }

  private openSocket(): Promise<void> {
    this.setState(this.reconnectAttempts > 0 ? "reconnecting" : "connecting");

    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(buildSocketUrl(this.sessionId, this.token, this.socketUrl));

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.setState("connected");
        resolve();
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data as string) as JobSessionMessage;
          this.listeners.forEach((cb) => cb(msg));
        } catch {
          this.listeners.forEach((cb) =>
            cb({ type: "RAW", data: event.data, message: String(event.data) })
          );
        }
      };

      this.ws.onerror = (event) => {
        if (this.state === "connecting") {
          reject(event);
        }
      };

      this.ws.onclose = () => {
        if (this.closedByClient) {
          this.setState("closed");
          return;
        }

        this.scheduleReconnect();
      };
    });
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnect) {
      this.setState("closed");
      return;
    }

    this.reconnectAttempts += 1;
    this.setState("reconnecting");
    const delay = Math.min(1000 * 2 ** (this.reconnectAttempts - 1), 30_000);

    this.reconnectTimer = window.setTimeout(() => {
      void this.openSocket().catch(() => this.scheduleReconnect());
    }, delay);
  }

  private setState(state: JobSessionSocketState) {
    this.state = state;
    this.stateListeners.forEach((cb) => cb(state));
  }
}
