export type AgentMessageData = {
  message?: string;
  body?: string;
  content?: string;
  timestamp?: string;
  [key: string]: unknown;
};

export type PaymentModalData = {
  amount?: number;
  currency?: string;
  description?: string;
  invoice_id?: string;
  invoiceId?: string;
  [key: string]: unknown;
};

export type PromptModalData = {
  prompt?: string;
  question?: string;
  title?: string;
  options?: string[];
  [key: string]: unknown;
};

export type SessionCompleteData = {
  message?: string;
  result?: unknown;
  [key: string]: unknown;
};

export type ModalResponseData = {
  modal_type: "payment" | "prompt";
  confirmed?: boolean;
  answer?: string;
  selected_option?: string;
  [key: string]: unknown;
};

export type IncomingMessage =
  | { type: "AGENT_MESSAGE"; data: AgentMessageData }
  | { type: "PAYMENT_CONFIRMATION_MODAL"; data: PaymentModalData }
  | { type: "USER_PROMPT_MODAL"; data: PromptModalData }
  | { type: "SESSION_COMPLETE"; data: SessionCompleteData };

export type OutgoingMessage =
  | { type: "USER_MESSAGE"; data: { message: string } }
  | { type: "MODAL_RESPONSE"; data: ModalResponseData }
  | { type: "CANCEL_SESSION" };

type Listener = (msg: IncomingMessage) => void;
type StatusListener = (state: UserAgentSocketState) => void;

export type UserAgentSocketState = "idle" | "connecting" | "connected" | "reconnecting" | "closed";

function buildSocketUrl(sessionId: string, token: string) {
  const wsBase = (
    process.env.NEXT_PUBLIC_WS_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    "ws://localhost:8000"
  ).replace(/^http/, "ws");
  return `${wsBase}/ws/user-agent/${encodeURIComponent(sessionId)}?token=${encodeURIComponent(token)}`;
}

export class UserAgentSocket {
  private ws: WebSocket | null = null;
  private listeners: Set<Listener> = new Set();
  private statusListeners: Set<StatusListener> = new Set();
  private reconnectTimer: number | null = null;
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private closedByClient = false;
  private state: UserAgentSocketState = "idle";

  constructor(
    private sessionId: string,
    private token: string
  ) {}

  connect(): Promise<void> {
    this.closedByClient = false;
    return this.openSocket();
  }

  send(message: OutgoingMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  subscribe(cb: Listener): () => void {
    this.listeners.add(cb);
    return () => {
      this.listeners.delete(cb);
    };
  }

  subscribeStatus(cb: StatusListener): () => void {
    this.statusListeners.add(cb);
    cb(this.state);
    return () => {
      this.statusListeners.delete(cb);
    };
  }

  close(): void {
    this.closedByClient = true;
    if (this.reconnectTimer) {
      window.clearTimeout(this.reconnectTimer);
    }
    this.setState("closed");
    this.ws?.close();
  }

  private openSocket(): Promise<void> {
    this.setState(this.reconnectDelay > 1000 ? "reconnecting" : "connecting");

    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(buildSocketUrl(this.sessionId, this.token));

      this.ws.onopen = () => {
        this.reconnectDelay = 1000;
        this.setState("connected");
        resolve();
      };

      this.ws.onerror = (event) => {
        if (this.state === "connecting") {
          reject(event);
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data as string) as IncomingMessage;
          this.listeners.forEach((cb) => cb(msg));
        } catch {
          // Malformed socket payloads are ignored; the connection stays open.
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
    this.setState("reconnecting");
    const delay = this.reconnectDelay;
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
      void this.openSocket().catch(() => {
        this.scheduleReconnect();
      });
    }, delay);
  }

  private setState(state: UserAgentSocketState) {
    this.state = state;
    this.statusListeners.forEach((cb) => cb(state));
  }
}
