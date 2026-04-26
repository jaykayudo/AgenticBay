"use client";

import {
  ArrowDownToLine,
  ArrowLeft,
  Bot,
  Check,
  CircleAlert,
  CircleDot,
  Clock3,
  Copy,
  FileJson,
  History,
  LoaderCircle,
  Logs,
  MessageSquare,
  Paperclip,
  Pause,
  Play,
  RefreshCw,
  RotateCcw,
  Send,
  ShieldCheck,
  Sparkles,
  SquareCheckBig,
  TerminalSquare,
  UserRound,
  Wallet,
  X,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import {
  startTransition,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import useSWR from "swr";

import { useApiQuery } from "@/hooks/useApi";
import { useJobSession } from "@/hooks/useJobSession";
import { jobsApi } from "@/lib/api/jobs";
import { reviewsApi } from "@/lib/api/reviews";
import { formatUsdc } from "@/lib/marketplace-data";
import {
  buildMockJobResultPayload,
  patchMockMarketplaceSession,
  type MockMarketplaceSessionRecord,
} from "@/lib/mock-api";
import { cn } from "@/lib/utils";

type MarketplaceSessionRead = {
  sessionId: string;
  agentSlug: string;
  agentName: string;
  actionId: string;
  actionName: string;
  priceUsdc: number;
  estimatedDurationLabel: string;
  inputSummary: string;
  amountLockedUsdc: number;
  status: JobStatus;
  mode: "hire" | "demo";
  createdAt: string;
  redirectPath: string;
  sessionToken: string;
  socketUrl: string;
  resultPayload: Record<string, unknown> | null;
};

type JobStatus =
  | "queued"
  | "processing"
  | "awaiting_payment"
  | "completed"
  | "cancelled"
  | "closed";

type PaymentState = "not_required" | "pending" | "funded" | "settled" | "refunded";
type ConnectionState = "connecting" | "connected" | "reconnecting" | "disconnected";
type Sender = "user" | "orchestrator" | "agent" | "system";

type FeedKind =
  | "user"
  | "orchestrator"
  | "agent"
  | "payment_confirmation"
  | "payment_prompt"
  | "processing"
  | "approval_request"
  | "tool_update"
  | "result"
  | "error";

type PaymentDetails = {
  amount: number;
  description: string;
  invoiceId: string;
  contractAddress: string;
  functionName: string;
};

type ApprovalDetails = {
  requestId: string;
  title: string;
  summary: string;
  options?: string[];
};

type FeedItem = {
  id: string;
  kind: FeedKind;
  type: string;
  sender: Sender;
  title: string;
  body: string;
  timestamp: string;
  payload?: Record<string, unknown> | string | null;
  payment?: PaymentDetails;
  approval?: ApprovalDetails;
};

type LogItem = {
  id: string;
  tone: "info" | "warning" | "error";
  message: string;
  timestamp: string;
};

type TimelineStep = {
  key: "created" | "escrow" | "processing" | "input" | "complete" | "settled";
  label: string;
  description: string;
};

type OrchestratorEnvelope = {
  type?: string;
  event?: string;
  message?: string | null;
  data?: Record<string, unknown> | string | null;
  payload?: Record<string, unknown> | string | null;
};

const dateTimeFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

const timeFormatter = new Intl.DateTimeFormat("en-US", {
  hour: "numeric",
  minute: "2-digit",
  second: "2-digit",
});

const statusLabel: Record<JobStatus, string> = {
  queued: "Queued",
  processing: "Processing",
  awaiting_payment: "Awaiting input",
  completed: "Complete",
  cancelled: "Cancelled",
  closed: "Closed",
};

const timelineSteps: TimelineStep[] = [
  {
    key: "created",
    label: "Created",
    description: "Session opened",
  },
  {
    key: "escrow",
    label: "Escrow Funded",
    description: "USDC locked",
  },
  {
    key: "processing",
    label: "Processing",
    description: "Agent working",
  },
  {
    key: "input",
    label: "Awaiting User Input",
    description: "Decision needed",
  },
  {
    key: "complete",
    label: "Complete",
    description: "Result ready",
  },
  {
    key: "settled",
    label: "Settled",
    description: "Funds released",
  },
];

function safeStringify(value: unknown) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function makeId(prefix = "item") {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function isTerminalStatus(status: JobStatus) {
  return status === "cancelled" || status === "closed";
}

function isActionableStatus(status: JobStatus) {
  return status !== "cancelled" && status !== "closed";
}

function getEnvelopeType(envelope: OrchestratorEnvelope) {
  return String(envelope.type ?? envelope.event ?? "MESSAGE").toUpperCase();
}

function getEnvelopeData(envelope: OrchestratorEnvelope) {
  return envelope.data ?? envelope.payload ?? null;
}

function maybeRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function getString(record: Record<string, unknown> | null, key: string, fallback = "") {
  const value = record?.[key];
  return typeof value === "string" ? value : fallback;
}

function getNumber(record: Record<string, unknown> | null, key: string, fallback = 0) {
  const value = record?.[key];
  return typeof value === "number" ? value : fallback;
}

function feedTone(kind: FeedKind) {
  switch (kind) {
    case "user":
      return "border-[var(--primary)]/30 bg-[var(--primary-soft)]";
    case "agent":
      return "border-sky-200 bg-sky-50";
    case "payment_prompt":
      return "border-emerald-200 bg-emerald-50";
    case "payment_confirmation":
      return "border-blue-200 bg-blue-50";
    case "approval_request":
      return "border-amber-200 bg-amber-50";
    case "result":
      return "border-[var(--primary)] bg-[color-mix(in_srgb,var(--primary-soft)_76%,white)]";
    case "error":
      return "border-rose-200 bg-rose-50";
    case "processing":
    case "tool_update":
      return "border-[var(--border)] bg-[var(--surface-2)]";
    case "orchestrator":
    default:
      return "border-[var(--border)] bg-[var(--surface)]";
  }
}

function SenderIcon({ sender, kind }: { sender: Sender; kind: FeedKind }) {
  if (kind === "payment_prompt" || kind === "payment_confirmation") {
    return <Wallet className="h-5 w-5" />;
  }

  if (kind === "tool_update") {
    return <TerminalSquare className="h-5 w-5" />;
  }

  if (kind === "approval_request") {
    return <SquareCheckBig className="h-5 w-5" />;
  }

  if (kind === "result") {
    return <FileJson className="h-5 w-5" />;
  }

  if (kind === "error") {
    return <CircleAlert className="h-5 w-5" />;
  }

  if (sender === "user") {
    return <UserRound className="h-5 w-5" />;
  }

  if (sender === "agent") {
    return <Bot className="h-5 w-5" />;
  }

  return <Sparkles className="h-5 w-5" />;
}

function paymentStateLabel(paymentState: PaymentState) {
  const labels: Record<PaymentState, string> = {
    not_required: "Not required",
    pending: "Payment pending",
    funded: "Escrow funded",
    settled: "Settled",
    refunded: "Refunded",
  };

  return labels[paymentState];
}

function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/45 px-4 py-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <section className="app-panel w-full max-w-xl p-5 sm:p-6">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-lg font-semibold text-[var(--text)]">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="grid h-10 w-10 place-items-center rounded-full border border-[var(--border)] text-[var(--text-muted)] transition hover:text-[var(--text)]"
            aria-label="Close modal"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}

function FeedCard({
  item,
  activePaymentId,
  activeApprovalId,
  onPayNow,
  onApproval,
  onCopyPayload,
}: {
  item: FeedItem;
  activePaymentId: string | null;
  activeApprovalId: string | null;
  onPayNow: (invoiceId: string) => void;
  onApproval: (requestId: string, accepted: boolean) => void;
  onCopyPayload: (payload: unknown) => void;
}) {
  const payment = item.payment;
  const approval = item.approval;
  const showPayButton =
    item.kind === "payment_prompt" && payment && activePaymentId === payment.invoiceId;
  const showApprovalButtons =
    item.kind === "approval_request" && approval && activeApprovalId === approval.requestId;

  return (
    <article className={cn("rounded-[1.4rem] border p-4 sm:p-5", feedTone(item.kind))}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl bg-white/75 text-[var(--primary)] shadow-sm">
            <SenderIcon sender={item.sender} kind={item.kind} />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-semibold text-[var(--text)]">{item.title}</p>
              <span className="rounded-full border border-[var(--border)] bg-white/60 px-2 py-0.5 text-[11px] font-semibold tracking-[0.14em] text-[var(--text-muted)] uppercase">
                {item.kind.replaceAll("_", " ")}
              </span>
            </div>
            <p className="mt-2 text-sm leading-7 text-[var(--text-muted)]">{item.body}</p>
          </div>
        </div>
        <span className="shrink-0 text-xs font-medium tracking-[0.18em] text-[var(--text-muted)] uppercase">
          {timeFormatter.format(new Date(item.timestamp))}
        </span>
      </div>

      {payment ? (
        <div className="mt-4 rounded-[1.2rem] border border-[var(--border)] bg-white/75 p-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                Amount
              </p>
              <p className="mt-2 font-semibold text-[var(--text)]">{formatUsdc(payment.amount)}</p>
            </div>
            <div>
              <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                Invoice
              </p>
              <p className="mt-2 text-sm font-medium break-all text-[var(--text)]">
                {payment.invoiceId}
              </p>
            </div>
          </div>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div>
              <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                Contract
              </p>
              <p className="mt-2 text-sm break-all text-[var(--text)]">{payment.contractAddress}</p>
            </div>
            <div>
              <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                Function
              </p>
              <p className="mt-2 text-sm break-all text-[var(--text)]">{payment.functionName}</p>
            </div>
          </div>
          {showPayButton ? (
            <button
              type="button"
              onClick={() => onPayNow(payment.invoiceId)}
              className="mt-4 inline-flex h-11 items-center justify-center gap-2 rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] transition hover:opacity-95"
            >
              <Wallet className="h-4 w-4" />
              Pay Now
            </button>
          ) : null}
        </div>
      ) : null}

      {approval ? (
        <div className="mt-4 rounded-[1.2rem] border border-[var(--border)] bg-white/75 p-4">
          <p className="font-semibold text-[var(--text)]">{approval.title}</p>
          <p className="mt-2 text-sm leading-7 text-[var(--text-muted)]">{approval.summary}</p>
          {approval.options?.length ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {approval.options.map((option) => (
                <span
                  key={option}
                  className="rounded-full border border-[var(--border)] bg-white px-3 py-1 text-xs font-medium text-[var(--text-muted)]"
                >
                  {option}
                </span>
              ))}
            </div>
          ) : null}
          {showApprovalButtons ? (
            <div className="mt-4 flex flex-col gap-2 sm:flex-row">
              <button
                type="button"
                onClick={() => onApproval(approval.requestId, true)}
                className="inline-flex h-10 items-center justify-center gap-2 rounded-full bg-[var(--primary)] px-4 text-sm font-semibold text-[var(--primary-foreground)]"
              >
                <Check className="h-4 w-4" />
                Accept
              </button>
              <button
                type="button"
                onClick={() => onApproval(approval.requestId, false)}
                className="inline-flex h-10 items-center justify-center gap-2 rounded-full border border-[var(--border)] bg-white px-4 text-sm font-semibold text-[var(--text)]"
              >
                <RotateCcw className="h-4 w-4" />
                Reject
              </button>
            </div>
          ) : null}
        </div>
      ) : null}

      {item.payload ? (
        <details className="mt-4">
          <summary className="cursor-pointer text-sm font-medium text-[var(--text-muted)]">
            View payload
          </summary>
          <div className="mt-3 rounded-[1rem] border border-[var(--border)] bg-white/70 p-3">
            <button
              type="button"
              onClick={() => onCopyPayload(item.payload)}
              className="mb-3 inline-flex h-8 items-center gap-2 rounded-full border border-[var(--border)] px-3 text-xs font-medium text-[var(--text-muted)]"
            >
              <Copy className="h-3.5 w-3.5" />
              Copy payload
            </button>
            <pre className="overflow-x-auto text-xs leading-6 text-[var(--text-muted)]">
              {typeof item.payload === "string" ? item.payload : safeStringify(item.payload)}
            </pre>
          </div>
        </details>
      ) : null}
    </article>
  );
}

function Timeline({
  session,
  status,
  paymentState,
  activeApprovalId,
}: {
  session: MarketplaceSessionRead;
  status: JobStatus;
  paymentState: PaymentState;
  activeApprovalId: string | null;
}) {
  function isComplete(step: TimelineStep["key"]) {
    if (step === "created") {
      return true;
    }
    if (step === "escrow") {
      return paymentState === "funded" || paymentState === "settled" || session.mode === "demo";
    }
    if (step === "processing") {
      return status === "processing" || status === "awaiting_payment" || status === "completed";
    }
    if (step === "input") {
      return Boolean(activeApprovalId) || status === "completed";
    }
    if (step === "complete") {
      return status === "completed";
    }
    return paymentState === "settled";
  }

  return (
    <div className="mt-4 space-y-3">
      {timelineSteps.map((step) => {
        const complete = isComplete(step.key);

        return (
          <div key={step.key} className="flex gap-3">
            <div
              className={cn(
                "mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full border",
                complete
                  ? "border-[var(--primary)] bg-[var(--primary)] text-white"
                  : "border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)]"
              )}
            >
              {complete ? <Check className="h-3.5 w-3.5" /> : <CircleDot className="h-3.5 w-3.5" />}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-[var(--text)]">{step.label}</p>
              <p className="text-xs leading-5 text-[var(--text-muted)]">{step.description}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Composer({
  value,
  disabled,
  onChange,
  onSend,
  onQuickAction,
}: {
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
  onSend: () => void;
  onQuickAction: (action: WorkspaceAction) => void;
}) {
  const quickActions: Array<{ action: WorkspaceAction; label: string; icon: typeof Check }> = [
    { action: "APPROVE_RESULT", label: "Approve Result", icon: Check },
    { action: "REQUEST_REVISION", label: "Request Revision", icon: RotateCcw },
    { action: "PAUSE_JOB", label: "Pause Job", icon: Pause },
    { action: "RESUME_JOB", label: "Resume Job", icon: Play },
    { action: "RETRY_STEP", label: "Retry Step", icon: RefreshCw },
    { action: "SUMMARIZE_PROGRESS", label: "Summarize Progress", icon: History },
  ];

  return (
    <div className="sticky bottom-3 z-20 mt-5 rounded-[1.6rem] border border-[var(--border)] bg-[var(--surface)] p-3 shadow-[var(--shadow-soft)]">
      <div className="flex flex-wrap gap-2 pb-3">
        {quickActions.map((item) => {
          const Icon = item.icon;

          return (
            <button
              key={item.action}
              type="button"
              disabled={disabled}
              onClick={() => onQuickAction(item.action)}
              className="inline-flex h-8 items-center gap-1.5 rounded-full border border-[var(--border)] px-3 text-xs font-medium text-[var(--text-muted)] transition hover:text-[var(--text)] disabled:opacity-45"
            >
              <Icon className="h-3.5 w-3.5" />
              {item.label}
            </button>
          );
        })}
      </div>
      <div className="flex items-end gap-2">
        <button
          type="button"
          className="grid h-11 w-11 shrink-0 place-items-center rounded-full border border-[var(--border)] text-[var(--text-muted)] transition hover:text-[var(--text)]"
          aria-label="Attach file placeholder"
        >
          <Paperclip className="h-4 w-4" />
        </button>
        <textarea
          value={value}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
              event.preventDefault();
              onSend();
            }
          }}
          className="min-h-11 flex-1 resize-none rounded-[1.1rem] border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3 text-sm leading-6 text-[var(--text)] transition outline-none focus:border-[var(--primary)] disabled:opacity-60"
          placeholder="Give instructions or ask the agent..."
          rows={1}
        />
        <button
          type="button"
          disabled={disabled || !value.trim()}
          onClick={onSend}
          className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] transition hover:opacity-95 disabled:opacity-45"
        >
          <Send className="h-4 w-4" />
          Send
        </button>
      </div>
      <p className="mt-2 text-xs text-[var(--text-muted)]">
        Press Ctrl+Enter or Cmd+Enter to send. Attachments are reserved for the next integration.
      </p>
    </div>
  );
}

type WorkspaceAction =
  | "APPROVE_RESULT"
  | "REQUEST_REVISION"
  | "PAUSE_JOB"
  | "RESUME_JOB"
  | "RETRY_STEP"
  | "SUMMARIZE_PROGRESS"
  | "CLOSE_JOB";

export function JobSessionPage({ sessionId }: { sessionId: string }) {
  const sessionQuery = useApiQuery<MarketplaceSessionRead>(
    ["marketplace-job-session", sessionId],
    `/marketplace/sessions/${encodeURIComponent(sessionId)}`,
    {
      enabled: Boolean(sessionId),
    }
  );

  const session = sessionQuery.data;
  const realtimeSession = useJobSession(
    session?.sessionId ?? "",
    session?.sessionToken ?? "",
    session?.socketUrl?.startsWith("mock://") ? undefined : session?.socketUrl
  );
  const [connectionState, setConnectionState] = useState<ConnectionState>("connecting");
  const [sessionStatus, setSessionStatus] = useState<JobStatus>("queued");
  const [paymentState, setPaymentState] = useState<PaymentState>("pending");
  const [amountLockedUsdc, setAmountLockedUsdc] = useState(0);
  const [latestProgress, setLatestProgress] = useState<number | null>(null);
  const [activePaymentId, setActivePaymentId] = useState<string | null>(null);
  const [activeApprovalId, setActiveApprovalId] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState("Opening workspace");
  const [resultPayload, setResultPayload] = useState<Record<string, unknown> | null>(null);
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [composerValue, setComposerValue] = useState("");
  const [cancelOpen, setCancelOpen] = useState(false);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [reviewRating, setReviewRating] = useState(5);
  const [reviewBody, setReviewBody] = useState("");
  const [reviewSubmitting, setReviewSubmitting] = useState(false);
  const [reviewSubmitted, setReviewSubmitted] = useState(false);
  const [paused, setPaused] = useState(false);
  const [copied, setCopied] = useState("");
  const messagesQuery = useSWR(sessionId ? ["/jobs/messages", sessionId] : null, () =>
    jobsApi.getMessages(sessionId).then((response) => response.data.messages)
  );

  const bottomRef = useRef<HTMLDivElement | null>(null);
  const manualShutdownRef = useRef(false);
  const initializedRef = useRef(false);
  const sessionStartedRef = useRef(false);
  const currentStatusRef = useRef<JobStatus>("queued");
  const mockTimersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    currentStatusRef.current = sessionStatus;
  }, [sessionStatus]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [feed.length]);

  const appendLog = useCallback((message: string, tone: LogItem["tone"] = "info") => {
    setLogs((current) => [
      ...current,
      {
        id: makeId("log"),
        tone,
        message,
        timestamp: new Date().toISOString(),
      },
    ]);
  }, []);

  const appendFeed = useCallback((item: Omit<FeedItem, "id" | "timestamp">) => {
    setFeed((current) => [
      ...current,
      {
        ...item,
        id: makeId("feed"),
        timestamp: new Date().toISOString(),
      },
    ]);
  }, []);

  const clearMockTimers = useCallback(() => {
    mockTimersRef.current.forEach((timer) => clearTimeout(timer));
    mockTimersRef.current = [];
  }, []);

  const queueMockTimer = useCallback((delay: number, callback: () => void) => {
    const timer = setTimeout(callback, delay);
    mockTimersRef.current.push(timer);
  }, []);

  const persistMockSession = useCallback(
    (updates: Partial<MockMarketplaceSessionRecord>): MockMarketplaceSessionRecord | null => {
      if (!session) {
        return null;
      }

      return patchMockMarketplaceSession(session.sessionId, updates);
    },
    [session]
  );

  const sendPayload = useCallback(
    (payload: Record<string, unknown>) => {
      if (session?.socketUrl.startsWith("mock://")) {
        appendLog(`Mock WebSocket sent ${String(payload.type)}.`);
        return true;
      }

      if (realtimeSession.connectionState !== "connected") {
        appendLog(
          `Could not send ${String(payload.type)} because the WebSocket is not open.`,
          "error"
        );
        return false;
      }

      realtimeSession.sendCommand(String(payload.type), payload.data);
      appendLog(`Sent ${String(payload.type)} to the orchestrator.`);
      return true;
    },
    [appendLog, realtimeSession, session]
  );

  const completeMockSession = useCallback(
    (baseSession: MarketplaceSessionRead, amountLocked: number) => {
      const nextSession =
        persistMockSession({
          status: "completed",
          amountLockedUsdc: amountLocked,
        }) ??
        ({
          ...baseSession,
          amountLockedUsdc: amountLocked,
          status: "completed",
        } as MockMarketplaceSessionRecord);

      const result = buildMockJobResultPayload(nextSession);
      persistMockSession({
        status: "completed",
        amountLockedUsdc: amountLocked,
        resultPayload: result,
      });
      setAmountLockedUsdc(amountLocked);
      setPaymentState(amountLocked > 0 ? "settled" : "not_required");
      setSessionStatus("completed");
      setLatestProgress(100);
      setCurrentStep("Final result ready");
      setResultPayload(result);
      setActiveApprovalId("approval-final-result");
      appendFeed({
        kind: "result",
        type: "RESULT",
        sender: "agent",
        title: "Final result published",
        body: `${baseSession.actionName} is complete. Review the result package and approve or request a revision.`,
        payload: result,
      });
      appendFeed({
        kind: "approval_request",
        type: "APPROVAL_REQUEST",
        sender: "orchestrator",
        title: "Approval required",
        body: "The orchestration agent is asking for your decision before settlement is finalized.",
        approval: {
          requestId: "approval-final-result",
          title: "Accept final result?",
          summary: "Approve to settle the job, or reject to request another pass from the agent.",
          options: ["Accept result", "Request revision"],
        },
      });
    },
    [appendFeed, persistMockSession]
  );

  const scheduleMockCompletionFlow = useCallback(
    (baseSession: MarketplaceSessionRead, amountLocked: number, delayOffset = 0) => {
      const steps = [
        {
          delay: 600,
          progress: 44,
          title: "Tool update",
          body: "Orchestrator selected the execution plan and delegated research to a specialist sub-agent.",
          stage: "delegated_research",
        },
        {
          delay: 1300,
          progress: 67,
          title: "Agent message",
          body: "The active agent is validating outputs against the original input summary.",
          stage: "validation",
        },
        {
          delay: 2100,
          progress: 86,
          title: "Processing",
          body: "Packaging result preview, confidence checks, and handoff notes.",
          stage: "packaging",
        },
      ];

      steps.forEach((step) => {
        queueMockTimer(delayOffset + step.delay, () => {
          setSessionStatus("processing");
          setLatestProgress(step.progress);
          setCurrentStep(step.stage.replaceAll("_", " "));
          appendLog(`Mock event ${step.stage} at ${step.progress}%.`);
          appendFeed({
            kind: step.title === "Tool update" ? "tool_update" : "processing",
            type: step.title === "Tool update" ? "TOOL_UPDATE" : "PROCESSING",
            sender: step.title === "Agent message" ? "agent" : "orchestrator",
            title: step.title,
            body: step.body,
            payload: {
              progress: step.progress,
              stage: step.stage,
            },
          });
        });
      });

      queueMockTimer(delayOffset + 2900, () => completeMockSession(baseSession, amountLocked));
    },
    [appendFeed, appendLog, completeMockSession, queueMockTimer]
  );

  const handleIncomingEnvelope = useCallback(
    (envelope: OrchestratorEnvelope) => {
      const type = getEnvelopeType(envelope);
      const rawData = getEnvelopeData(envelope);
      const data = maybeRecord(rawData);
      const message = envelope.message ?? getString(data, "message");

      appendLog(`Received ${type} from orchestrator.`);

      switch (type) {
        case "USER_MESSAGE":
          appendFeed({
            kind: "user",
            type,
            sender: "user",
            title: "User message",
            body: message || "User sent an instruction.",
            payload: rawData,
          });
          break;
        case "ORCHESTRATOR_MESSAGE":
        case "START":
          appendFeed({
            kind: "orchestrator",
            type,
            sender: "orchestrator",
            title: type === "START" ? "Orchestrator started" : "Orchestrator message",
            body: message || "The orchestrator updated the session.",
            payload: rawData,
          });
          break;
        case "AGENT_MESSAGE":
        case "SERVICE_AGENT":
          appendFeed({
            kind: "agent",
            type,
            sender: "agent",
            title: "Agent message",
            body: message || "The selected agent sent an update.",
            payload: rawData,
          });
          break;
        case "PAYMENT": {
          const contractData = maybeRecord(data?.contract_data);
          const invoiceId = getString(contractData, "invoice_id", `invoice-${Date.now()}`);
          setSessionStatus("awaiting_payment");
          setPaymentState("pending");
          setActivePaymentId(invoiceId);
          setCurrentStep("Awaiting escrow payment");
          appendFeed({
            kind: "payment_prompt",
            type,
            sender: "orchestrator",
            title: "Payment required",
            body: getString(
              data,
              "description",
              "Escrow payment is required before execution can continue."
            ),
            payload: rawData,
            payment: {
              amount: getNumber(data, "amount", session?.priceUsdc ?? 0),
              description: getString(data, "description", "Escrow payment"),
              invoiceId,
              contractAddress: getString(contractData, "invoice_contract", "0xESCROW"),
              functionName: getString(contractData, "function_name", "payInvoice"),
            },
          });
          break;
        }
        case "PAYMENT_SUCCESSFUL":
          setPaymentState("funded");
          setSessionStatus("processing");
          setActivePaymentId(null);
          setAmountLockedUsdc(session?.priceUsdc ?? amountLockedUsdc);
          appendFeed({
            kind: "payment_confirmation",
            type,
            sender: "orchestrator",
            title: "Payment confirmed",
            body: `Escrow funding confirmed for invoice ${getString(data, "invoice_id", "current invoice")}.`,
            payload: rawData,
          });
          break;
        case "APPROVAL_REQUEST": {
          const requestId = getString(data, "request_id", `approval-${Date.now()}`);
          setSessionStatus("awaiting_payment");
          setActiveApprovalId(requestId);
          setCurrentStep("Awaiting user decision");
          appendFeed({
            kind: "approval_request",
            type,
            sender: "orchestrator",
            title: "Approval requested",
            body: message || "The orchestrator needs your approval to continue.",
            payload: rawData,
            approval: {
              requestId,
              title: getString(data, "title", "Approve next step?"),
              summary: getString(
                data,
                "summary",
                "Review the details and choose whether to proceed."
              ),
            },
          });
          break;
        }
        case "TOOL_UPDATE":
        case "ACTION_UPDATE":
          setLatestProgress(getNumber(data, "progress", latestProgress ?? 0));
          setCurrentStep(getString(data, "stage", getString(data, "action", "Tool update")));
          appendFeed({
            kind: "tool_update",
            type,
            sender: "orchestrator",
            title: "Tool/action update",
            body: message || "A tool or action step changed state.",
            payload: rawData,
          });
          break;
        case "PROCESSING":
          setSessionStatus("processing");
          setLatestProgress(getNumber(data, "progress", latestProgress ?? 0));
          setCurrentStep(getString(data, "stage", "Processing"));
          appendFeed({
            kind: "processing",
            type,
            sender: "orchestrator",
            title: "Processing update",
            body: message || "The orchestration agent is processing the job.",
            payload: rawData,
          });
          break;
        case "RESULT":
        case "CLOSE_APPEAL":
          setSessionStatus("completed");
          setLatestProgress(100);
          setCurrentStep("Final result ready");
          setResultPayload((data ?? { result: rawData }) as Record<string, unknown>);
          appendFeed({
            kind: "result",
            type,
            sender: "agent",
            title: "Result ready",
            body: message || "The final result is ready for review.",
            payload: rawData,
          });
          break;
        case "ERROR":
          appendFeed({
            kind: "error",
            type,
            sender: "orchestrator",
            title: getString(data, "error_type", "Orchestrator error"),
            body: getString(data, "message", message || "An orchestration error occurred."),
            payload: rawData,
          });
          appendLog(getString(data, "message", "Orchestrator error received."), "error");
          break;
        default:
          appendFeed({
            kind: "orchestrator",
            type,
            sender: "orchestrator",
            title: "Orchestrator event",
            body: message || `Received ${type}.`,
            payload: rawData,
          });
      }
    },
    [amountLockedUsdc, appendFeed, appendLog, latestProgress, session]
  );

  useEffect(() => {
    if (!session || initializedRef.current) {
      return;
    }

    initializedRef.current = true;
    queueMicrotask(() => {
      setSessionStatus(session.status);
      setAmountLockedUsdc(session.amountLockedUsdc);
      setResultPayload(session.resultPayload);
      setPaymentState(
        session.mode === "demo"
          ? "not_required"
          : session.amountLockedUsdc > 0
            ? session.status === "completed"
              ? "settled"
              : "funded"
            : "pending"
      );
      setCurrentStep(
        session.status === "completed"
          ? "Final result ready"
          : session.status === "awaiting_payment"
            ? "Awaiting payment"
            : "Opening workspace"
      );
      appendFeed({
        kind: "orchestrator",
        type: "SESSION_OPENED",
        sender: "orchestrator",
        title: "Workspace opened",
        body: `Connected to ${session.agentName} for ${session.actionName}.`,
        payload: {
          sessionId: session.sessionId,
          inputSummary: session.inputSummary,
          mode: session.mode,
        },
      });

      if (session.status === "completed" && session.resultPayload) {
        appendFeed({
          kind: "result",
          type: "RESULT",
          sender: "agent",
          title: "Existing result restored",
          body: `${session.actionName} is already complete.`,
          payload: session.resultPayload,
        });
      }
    });
  }, [appendFeed, session]);

  useEffect(() => {
    if (!session || session.socketUrl.startsWith("mock://")) {
      return;
    }

    if (realtimeSession.connectionState === "connected") {
      setConnectionState("connected");
    } else if (realtimeSession.connectionState === "reconnecting") {
      setConnectionState("reconnecting");
    } else if (realtimeSession.connectionState === "closed") {
      setConnectionState("disconnected");
    } else if (realtimeSession.connectionState === "connecting") {
      setConnectionState("connecting");
    }
  }, [realtimeSession.connectionState, session]);

  useEffect(() => {
    if (
      !session ||
      session.socketUrl.startsWith("mock://") ||
      realtimeSession.connectionState !== "connected" ||
      sessionStartedRef.current ||
      session.status !== "queued"
    ) {
      return;
    }

    sessionStartedRef.current = true;
    realtimeSession.sendCommand("START", {
      job_session_id: session.sessionId,
      job_session_auth_token: session.sessionToken,
      action_id: session.actionId,
      input_summary: session.inputSummary,
    });
  }, [realtimeSession, session]);

  useEffect(() => {
    if (!session || session.socketUrl.startsWith("mock://") || realtimeSession.feed.length === 0) {
      return;
    }

    const latest = realtimeSession.feed[realtimeSession.feed.length - 1];
    handleIncomingEnvelope({
      type: latest.type,
      data: latest.data as Record<string, unknown> | string | null,
    });
  }, [handleIncomingEnvelope, realtimeSession.feed, session]);

  useEffect(() => {
    if (!messagesQuery.data?.length) {
      return;
    }

    const messages = messagesQuery.data;
    startTransition(() => {
      setFeed((current) => {
        const existingIds = new Set(current.map((item) => item.id));
        const fromApi = messages
          .filter((message) => !existingIds.has(`api-message-${message.id}`))
          .map<FeedItem>((message) => ({
            id: `api-message-${message.id}`,
            kind: message.sender === "user" ? "user" : "orchestrator",
            type: "MESSAGE",
            sender:
              message.sender === "user"
                ? "user"
                : message.sender === "agent"
                  ? "agent"
                  : "orchestrator",
            title: message.sender,
            body: message.body,
            timestamp: message.createdAt,
          }));
        return fromApi.length ? [...fromApi, ...current] : current;
      });
    });
  }, [messagesQuery.data]);

  useEffect(() => {
    if (!session?.sessionToken || !session.socketUrl || !session.socketUrl.startsWith("mock://")) {
      return;
    }

    manualShutdownRef.current = false;
    let disposed = false;

    if (session.socketUrl.startsWith("mock://")) {
      clearMockTimers();
      queueMockTimer(0, () => {
        setConnectionState("connecting");
        appendLog(`Opening mock WebSocket with token ${session.sessionToken}.`);
      });

      queueMockTimer(250, () => {
        if (disposed) {
          return;
        }

        setConnectionState("connected");
        appendLog("Mock WebSocket connected.");

        if (!sessionStartedRef.current && session.status === "queued") {
          sessionStartedRef.current = true;
          persistMockSession({ status: "processing" });
          setSessionStatus("processing");
          setCurrentStep("Planning execution");
          appendFeed({
            kind: "processing",
            type: "PROCESSING",
            sender: "orchestrator",
            title: "Execution started",
            body: "Orchestrator is analyzing the job brief, required tools, and escrow state.",
            payload: {
              progress: 18,
              stage: "planning",
            },
          });
          setLatestProgress(18);

          queueMockTimer(900, () => {
            appendFeed({
              kind: "tool_update",
              type: "TOOL_UPDATE",
              sender: "orchestrator",
              title: "Sub-agent hired",
              body: "Research runner joined the workspace to gather supporting context.",
              payload: {
                subAgent: "Research Runner",
                status: "active",
              },
            });
            setLatestProgress(28);
            setCurrentStep("Sub-agent gathering context");
          });

          if (session.mode === "demo" || session.priceUsdc === 0) {
            scheduleMockCompletionFlow(session, 0, 1200);
          } else {
            queueMockTimer(1500, () => {
              const invoiceId = `mock-invoice-${session.sessionId.slice(0, 8)}`;
              persistMockSession({ status: "awaiting_payment" });
              setSessionStatus("awaiting_payment");
              setPaymentState("pending");
              setActivePaymentId(invoiceId);
              setCurrentStep("Awaiting escrow payment");
              appendFeed({
                kind: "payment_prompt",
                type: "PAYMENT",
                sender: "orchestrator",
                title: "Escrow payment requested",
                body: `Lock ${formatUsdc(session.priceUsdc)} in escrow before the agent continues.`,
                payload: {
                  amount: session.priceUsdc,
                  description: `Escrow deposit for ${session.actionName}`,
                },
                payment: {
                  amount: session.priceUsdc,
                  description: `Escrow deposit for ${session.actionName}`,
                  invoiceId,
                  contractAddress: "0xDEMOESCROW0000000000000000000000000000",
                  functionName: "payInvoice",
                },
              });
            });
          }
        }
      });

      return () => {
        disposed = true;
        manualShutdownRef.current = true;
        clearMockTimers();
      };
    }
  }, [
    appendFeed,
    appendLog,
    clearMockTimers,
    persistMockSession,
    queueMockTimer,
    scheduleMockCompletionFlow,
    session,
  ]);

  function sendWorkspaceAction(action: WorkspaceAction, data: Record<string, unknown> = {}) {
    if (!session) {
      return false;
    }

    const payload = {
      type: action,
      data: {
        job_session_id: session.sessionId,
        ...data,
      },
    };

    return sendPayload(payload);
  }

  function sendUserMessage() {
    if (!session || !composerValue.trim()) {
      return;
    }

    const body = composerValue.trim();
    setComposerValue("");
    appendFeed({
      kind: "user",
      type: "USER_MESSAGE",
      sender: "user",
      title: "You",
      body,
      payload: {
        message: body,
      },
    });

    const sent = sendPayload({
      type: "USER_MESSAGE",
      data: {
        job_session_id: session.sessionId,
        message: body,
      },
    });

    if (session.socketUrl.startsWith("mock://") && sent) {
      queueMockTimer(450, () => {
        appendFeed({
          kind: "orchestrator",
          type: "ORCHESTRATOR_MESSAGE",
          sender: "orchestrator",
          title: "Orchestrator acknowledged",
          body: "Instruction received. I will fold this into the current execution plan.",
          payload: {
            acknowledgedMessage: body,
          },
        });
      });
    }
  }

  function handlePayNow(invoiceId: string) {
    if (!session) {
      return;
    }

    const sent = sendPayload({
      type: "PAYMENT_SUCCESSFUL",
      data: {
        job_session_id: session.sessionId,
        invoice_id: invoiceId,
      },
    });

    if (!sent) {
      return;
    }

    clearMockTimers();
    persistMockSession({
      status: "processing",
      amountLockedUsdc: session.priceUsdc,
    });
    setActivePaymentId(null);
    setAmountLockedUsdc(session.priceUsdc);
    setPaymentState("funded");
    setSessionStatus("processing");
    setCurrentStep("Payment confirmed, resuming execution");
    appendFeed({
      kind: "payment_confirmation",
      type: "PAYMENT_SUCCESSFUL",
      sender: "orchestrator",
      title: "Payment confirmed",
      body: `Invoice ${invoiceId} has been confirmed and funds are now locked in escrow.`,
      payload: {
        invoiceId,
        amountLockedUsdc: session.priceUsdc,
      },
    });

    if (session.socketUrl.startsWith("mock://")) {
      scheduleMockCompletionFlow(session, session.priceUsdc, 350);
    }
  }

  function handleApproval(requestId: string, accepted: boolean) {
    const action = accepted ? "APPROVE_RESULT" : "REQUEST_REVISION";
    const sent = sendWorkspaceAction(action, {
      request_id: requestId,
      accepted,
    });

    if (!sent || !session) {
      return;
    }

    setActiveApprovalId(null);
    appendFeed({
      kind: "user",
      type: action,
      sender: "user",
      title: accepted ? "Result approved" : "Revision requested",
      body: accepted
        ? "You approved the result. The orchestrator can proceed with settlement."
        : "You rejected the current result and asked the agent for another pass.",
      payload: {
        requestId,
        accepted,
      },
    });

    if (accepted) {
      setPaymentState(amountLockedUsdc > 0 ? "settled" : "not_required");
      appendLog("User approved final result.");
      return;
    }

    setSessionStatus("processing");
    setCurrentStep("Revision requested");
    setLatestProgress(72);
    appendLog("User requested revision.", "warning");
    if (session.socketUrl.startsWith("mock://")) {
      queueMockTimer(800, () => {
        appendFeed({
          kind: "agent",
          type: "AGENT_MESSAGE",
          sender: "agent",
          title: "Revision pass started",
          body: "The agent is revising the output using your feedback.",
          payload: {
            stage: "revision",
          },
        });
      });
      queueMockTimer(1900, () => completeMockSession(session, amountLockedUsdc));
    }
  }

  function handleQuickAction(action: WorkspaceAction) {
    if (!session) {
      return;
    }

    if (action === "PAUSE_JOB") {
      setPaused(true);
      setCurrentStep("Paused by user");
    }

    if (action === "RESUME_JOB") {
      setPaused(false);
      setCurrentStep("Resuming execution");
    }

    if (action === "RETRY_STEP") {
      setCurrentStep("Retrying current step");
    }

    if (action === "APPROVE_RESULT" && activeApprovalId) {
      handleApproval(activeApprovalId, true);
      return;
    }

    if (action === "REQUEST_REVISION" && activeApprovalId) {
      handleApproval(activeApprovalId, false);
      return;
    }

    const sent = sendWorkspaceAction(action, {
      reason: action === "SUMMARIZE_PROGRESS" ? "user_requested_summary" : "user_action",
      current_step: currentStep,
    });

    if (!sent) {
      return;
    }

    appendFeed({
      kind: "user",
      type: action,
      sender: "user",
      title: action.replaceAll("_", " "),
      body: `You sent ${action.replaceAll("_", " ").toLowerCase()} to the orchestrator.`,
      payload: {
        currentStep,
      },
    });

    if (session.socketUrl.startsWith("mock://") && action === "SUMMARIZE_PROGRESS") {
      queueMockTimer(350, () => {
        appendFeed({
          kind: "orchestrator",
          type: "ORCHESTRATOR_MESSAGE",
          sender: "orchestrator",
          title: "Progress summary",
          body: `Current step: ${currentStep}. Status: ${statusLabel[sessionStatus]}. Escrow: ${paymentStateLabel(paymentState)}.`,
        });
      });
    }
  }

  async function confirmCancelJob() {
    if (!session) {
      return;
    }

    try {
      await jobsApi.cancelJob(session.sessionId);
    } catch {
      // Some current sessions are mock-backed; still close the local workspace state.
    }

    const sent = sendWorkspaceAction("CLOSE_JOB", {
      reason: "user_cancelled",
    });

    if (!sent) {
      return;
    }

    clearMockTimers();
    persistMockSession({ status: "cancelled" });
    setSessionStatus("cancelled");
    setPaymentState(amountLockedUsdc > 0 ? "refunded" : "not_required");
    setCurrentStep("Cancelled by user");
    setCancelOpen(false);
    appendLog("Cancel job request sent.", "warning");
    appendFeed({
      kind: "user",
      type: "CLOSE_JOB",
      sender: "user",
      title: "Cancel requested",
      body: "You asked the orchestrator to stop this job session.",
    });
  }

  async function submitReview() {
    if (!session || reviewSubmitting) {
      return;
    }

    setReviewSubmitting(true);
    try {
      await reviewsApi.submit(session.sessionId, {
        rating: reviewRating,
        body: reviewBody.trim() || undefined,
      });
      setReviewSubmitted(true);
      setReviewOpen(false);
      appendLog("Review submitted.");
    } finally {
      setReviewSubmitting(false);
    }
  }

  function downloadResult(format: "json" | "txt") {
    if (!resultPayload || !session) {
      return;
    }

    const fileName = `job-session-${session.sessionId}.${format}`;
    const content =
      format === "json"
        ? `${safeStringify(resultPayload)}\n`
        : [
            `Job: ${session.sessionId}`,
            `Agent: ${session.agentName}`,
            `Action: ${session.actionName}`,
            `Status: ${statusLabel[sessionStatus]}`,
            "",
            typeof resultPayload.resultText === "string"
              ? resultPayload.resultText
              : safeStringify(resultPayload),
          ].join("\n");

    const blob = new Blob([content], {
      type: format === "json" ? "application/json" : "text/plain;charset=utf-8",
    });
    const href = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = href;
    anchor.download = fileName;
    anchor.click();
    URL.revokeObjectURL(href);
    appendLog(`Downloaded result as ${fileName}.`);
  }

  async function copyPayload(payload: unknown) {
    await navigator.clipboard.writeText(
      typeof payload === "string" ? payload : safeStringify(payload)
    );
    setCopied("payload");
    window.setTimeout(() => setCopied(""), 1400);
  }

  const connectionLabel = useMemo(() => {
    switch (connectionState) {
      case "connected":
        return "Live";
      case "reconnecting":
        return "Reconnecting";
      case "disconnected":
        return "Disconnected";
      case "connecting":
      default:
        return "Connecting";
    }
  }, [connectionState]);

  const subAgents = useMemo(
    () => [
      {
        name: "Research Runner",
        status: latestProgress && latestProgress > 25 ? "active" : "queued",
      },
      {
        name: "Quality Checker",
        status: latestProgress && latestProgress > 70 ? "active" : "waiting",
      },
      {
        name: "Result Packager",
        status: resultPayload ? "complete" : "waiting",
      },
    ],
    [latestProgress, resultPayload]
  );

  const composerDisabled =
    !session || connectionState === "disconnected" || isTerminalStatus(sessionStatus) || paused;

  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--foreground)]">
      <div className="mx-auto max-w-[var(--layout-max)] px-4 py-4 md:px-6 xl:px-8">
        <Link
          href="/marketplace"
          className="inline-flex items-center gap-2 text-sm font-medium text-[var(--text-muted)] transition hover:text-[var(--text)]"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to marketplace
        </Link>

        {sessionQuery.isLoading ? (
          <section className="app-panel mt-6 flex items-center gap-3 p-5 sm:p-6">
            <LoaderCircle className="h-5 w-5 animate-spin text-[var(--primary)]" />
            <p className="text-sm text-[var(--text-muted)]">Loading session details...</p>
          </section>
        ) : null}

        {sessionQuery.isError ? (
          <section className="app-panel mt-6 p-5 sm:p-6">
            <div className="rounded-[1.4rem] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              <div className="flex items-start gap-2">
                <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
                <p>The job session could not be loaded. It may have expired.</p>
              </div>
            </div>
          </section>
        ) : null}

        {session ? (
          <div className="mt-5 space-y-5">
            <section className="app-panel p-4 sm:p-5">
              <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="app-status-badge" data-tone="accent">
                      Job {session.sessionId}
                    </span>
                    <span className="app-status-badge" data-tone="default">
                      {statusLabel[sessionStatus]}
                    </span>
                    <span
                      className="app-status-badge"
                      data-tone={connectionState === "connected" ? "accent" : "default"}
                    >
                      {connectionLabel}
                    </span>
                    {paused ? (
                      <span className="app-status-badge" data-tone="default">
                        Paused
                      </span>
                    ) : null}
                  </div>
                  <h1 className="mt-3 truncate text-2xl font-semibold tracking-[-0.04em] text-[var(--text)] sm:text-3xl">
                    {session.agentName}
                  </h1>
                  <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                    Active agent for {session.actionName}
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={!isActionableStatus(sessionStatus)}
                    onClick={() => handleQuickAction(paused ? "RESUME_JOB" : "PAUSE_JOB")}
                    className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--border)] px-4 text-sm font-semibold text-[var(--text)] transition hover:bg-[var(--surface-2)] disabled:opacity-45"
                  >
                    {paused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
                    {paused ? "Resume Job" : "Pause Job"}
                  </button>
                  <button
                    type="button"
                    disabled={!isActionableStatus(sessionStatus)}
                    onClick={() => handleQuickAction("RETRY_STEP")}
                    className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--border)] px-4 text-sm font-semibold text-[var(--text)] transition hover:bg-[var(--surface-2)] disabled:opacity-45"
                  >
                    <RefreshCw className="h-4 w-4" />
                    Retry
                  </button>
                  <button
                    type="button"
                    disabled={!isActionableStatus(sessionStatus)}
                    onClick={() => setCancelOpen(true)}
                    className="inline-flex h-10 items-center gap-2 rounded-full border border-rose-200 px-4 text-sm font-semibold text-rose-700 transition hover:bg-rose-50 disabled:opacity-45"
                  >
                    <XCircle className="h-4 w-4" />
                    Cancel Job
                  </button>
                </div>
              </div>
            </section>

            <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
              <main className="min-w-0 space-y-5">
                <section className="app-panel p-4 sm:p-5">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <h2 className="text-lg font-semibold text-[var(--text)]">Session feed</h2>
                      <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
                        Chronological workspace messages, payments, decisions, tool updates, logs,
                        and final results.
                      </p>
                    </div>
                    {latestProgress !== null ? (
                      <div className="rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1 text-sm font-semibold text-[var(--text-muted)]">
                        {latestProgress}% progress
                      </div>
                    ) : null}
                  </div>

                  <div className="mt-5 max-h-[68vh] space-y-4 overflow-y-auto pr-1">
                    {feed.length === 0 ? (
                      <div className="rounded-[1.2rem] border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3 text-sm text-[var(--text-muted)]">
                        Waiting for the first orchestrator event.
                      </div>
                    ) : null}
                    {feed.map((item) => (
                      <FeedCard
                        key={item.id}
                        item={item}
                        activePaymentId={activePaymentId}
                        activeApprovalId={activeApprovalId}
                        onPayNow={handlePayNow}
                        onApproval={handleApproval}
                        onCopyPayload={(payload) => void copyPayload(payload)}
                      />
                    ))}
                    <div ref={bottomRef} />
                  </div>

                  <Composer
                    value={composerValue}
                    disabled={composerDisabled}
                    onChange={setComposerValue}
                    onSend={sendUserMessage}
                    onQuickAction={handleQuickAction}
                  />
                  {copied ? (
                    <p className="mt-2 text-xs font-medium text-[var(--accent)]">Payload copied.</p>
                  ) : null}
                </section>

                <section className="app-panel p-4 sm:p-5">
                  <details>
                    <summary className="flex cursor-pointer items-center gap-2 text-sm font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                      <Logs className="h-4 w-4" />
                      Live logs
                    </summary>
                    <div className="mt-4 max-h-72 space-y-3 overflow-y-auto">
                      {logs.length === 0 ? (
                        <div className="rounded-[1.2rem] border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3 text-sm text-[var(--text-muted)]">
                          Waiting for connection and session events.
                        </div>
                      ) : (
                        logs.map((log) => (
                          <div
                            key={log.id}
                            className={cn(
                              "rounded-[1.1rem] border px-4 py-3 text-sm",
                              log.tone === "error"
                                ? "border-rose-200 bg-rose-50 text-rose-900"
                                : log.tone === "warning"
                                  ? "border-orange-200 bg-orange-50 text-orange-900"
                                  : "border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-muted)]"
                            )}
                          >
                            <div className="flex items-start justify-between gap-3">
                              <p>{log.message}</p>
                              <span className="shrink-0 text-xs tracking-[0.16em] uppercase">
                                {timeFormatter.format(new Date(log.timestamp))}
                              </span>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </details>
                </section>

                {resultPayload ? (
                  <section className="app-panel p-4 sm:p-5">
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <h2 className="text-lg font-semibold text-[var(--text)]">Result preview</h2>
                        <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
                          Final result is available. Download it, approve settlement, or request a
                          revision from the agent.
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => downloadResult("json")}
                          className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text)]"
                        >
                          <ArrowDownToLine className="h-4 w-4" />
                          JSON
                        </button>
                        <button
                          type="button"
                          onClick={() => downloadResult("txt")}
                          className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text)]"
                        >
                          <ArrowDownToLine className="h-4 w-4" />
                          Text
                        </button>
                        <button
                          type="button"
                          disabled={reviewSubmitted}
                          onClick={() => setReviewOpen(true)}
                          className="inline-flex h-10 items-center gap-2 rounded-full bg-[var(--primary)] px-4 text-sm font-semibold text-[var(--primary-foreground)] disabled:opacity-55"
                        >
                          <MessageSquare className="h-4 w-4" />
                          {reviewSubmitted ? "Reviewed" : "Review"}
                        </button>
                      </div>
                    </div>

                    <pre className="mt-5 max-h-80 overflow-x-auto rounded-[1.4rem] border border-[var(--border)] bg-[var(--surface-2)] p-4 text-xs leading-6 text-[var(--text-muted)]">
                      {safeStringify(resultPayload)}
                    </pre>

                    <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                      <button
                        type="button"
                        onClick={() => handleQuickAction("APPROVE_RESULT")}
                        className="inline-flex h-11 items-center justify-center gap-2 rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)]"
                      >
                        <Check className="h-4 w-4" />
                        Approve Result
                      </button>
                      <button
                        type="button"
                        onClick={() => handleQuickAction("REQUEST_REVISION")}
                        className="inline-flex h-11 items-center justify-center gap-2 rounded-full border border-[var(--border)] px-5 text-sm font-semibold text-[var(--text)]"
                      >
                        <RotateCcw className="h-4 w-4" />
                        Request Revision
                      </button>
                    </div>
                  </section>
                ) : null}
              </main>

              <aside className="space-y-5 xl:sticky xl:top-4 xl:self-start">
                <section className="app-panel p-5">
                  <div className="flex items-center gap-3">
                    <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[var(--primary-soft)] text-[var(--primary)]">
                      <MessageSquare className="h-5 w-5" />
                    </div>
                    <div>
                      <h2 className="font-semibold text-[var(--text)]">Job details</h2>
                      <p className="text-sm text-[var(--text-muted)]">Live execution context</p>
                    </div>
                  </div>

                  <div className="mt-5 space-y-3">
                    <div className="app-subtle p-4">
                      <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                        Action
                      </p>
                      <p className="mt-2 font-semibold text-[var(--text)]">{session.actionName}</p>
                    </div>
                    <div className="app-subtle p-4">
                      <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                        Input summary
                      </p>
                      <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                        {session.inputSummary}
                      </p>
                    </div>
                    <div className="app-subtle p-4">
                      <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                        Selected agent
                      </p>
                      <p className="mt-2 font-semibold text-[var(--text)]">{session.agentName}</p>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                      <div className="app-subtle p-4">
                        <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                          Escrow
                        </p>
                        <p className="mt-2 font-semibold text-[var(--text)]">
                          {formatUsdc(amountLockedUsdc)}
                        </p>
                      </div>
                      <div className="app-subtle p-4">
                        <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                          Payment
                        </p>
                        <p className="mt-2 font-semibold text-[var(--text)]">
                          {paymentStateLabel(paymentState)}
                        </p>
                      </div>
                    </div>
                  </div>
                </section>

                <section className="app-panel p-5">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-[var(--primary)]" />
                    <h3 className="text-sm font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                      Job timeline
                    </h3>
                  </div>
                  <Timeline
                    session={session}
                    status={sessionStatus}
                    paymentState={paymentState}
                    activeApprovalId={activeApprovalId}
                  />
                </section>

                <section className="app-panel p-5">
                  <div className="flex items-center gap-2">
                    <Bot className="h-4 w-4 text-[var(--primary)]" />
                    <h3 className="text-sm font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                      Sub-agents hired
                    </h3>
                  </div>
                  <div className="mt-4 space-y-3">
                    {subAgents.map((agent) => (
                      <div
                        key={agent.name}
                        className="flex items-center justify-between gap-3 rounded-2xl border border-[var(--border)] bg-[var(--surface-2)] p-3"
                      >
                        <span className="text-sm font-medium text-[var(--text)]">{agent.name}</span>
                        <span className="text-xs font-semibold tracking-[0.14em] text-[var(--text-muted)] uppercase">
                          {agent.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </section>

                <section className="app-panel p-5">
                  <div className="flex items-center gap-2">
                    <Clock3 className="h-4 w-4 text-[var(--primary)]" />
                    <h3 className="text-sm font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                      Current execution step
                    </h3>
                  </div>
                  <p className="mt-4 text-lg font-semibold text-[var(--text)]">{currentStep}</p>
                  <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                    Created {dateTimeFormatter.format(new Date(session.createdAt))}. Estimated
                    duration {session.estimatedDurationLabel}.
                  </p>
                </section>
              </aside>
            </div>
          </div>
        ) : null}
      </div>

      {cancelOpen ? (
        <Modal title="Cancel this job?" onClose={() => setCancelOpen(false)}>
          <div className="mt-5 space-y-4">
            <p className="text-sm leading-6 text-[var(--text-muted)]">
              This sends a CLOSE_JOB request to the orchestrator and stops further execution. Escrow
              status will be updated based on the current payment state.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                onClick={() => setCancelOpen(false)}
                className="inline-flex h-11 flex-1 items-center justify-center rounded-full border border-[var(--border)] px-5 text-sm font-semibold text-[var(--text)]"
              >
                Keep job running
              </button>
              <button
                type="button"
                onClick={confirmCancelJob}
                className="inline-flex h-11 flex-1 items-center justify-center gap-2 rounded-full bg-rose-600 px-5 text-sm font-semibold text-white"
              >
                <XCircle className="h-4 w-4" />
                Cancel Job
              </button>
            </div>
          </div>
        </Modal>
      ) : null}

      {reviewOpen ? (
        <Modal title="Review this agent" onClose={() => setReviewOpen(false)}>
          <div className="mt-5 space-y-4">
            <label className="grid gap-2 text-sm">
              <span className="font-medium text-[var(--text)]">Rating</span>
              <select
                value={reviewRating}
                onChange={(event) => setReviewRating(Number(event.target.value))}
                className="h-11 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-[var(--text)]"
              >
                {[5, 4, 3, 2, 1].map((rating) => (
                  <option key={rating} value={rating}>
                    {rating} stars
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-2 text-sm">
              <span className="font-medium text-[var(--text)]">Review</span>
              <textarea
                value={reviewBody}
                onChange={(event) => setReviewBody(event.target.value)}
                className="min-h-28 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-[var(--text)]"
                placeholder="What went well? Anything the agent should improve?"
              />
            </label>
            <button
              type="button"
              disabled={reviewSubmitting}
              onClick={() => void submitReview()}
              className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] disabled:opacity-55"
            >
              {reviewSubmitting ? (
                <LoaderCircle className="h-4 w-4 animate-spin" />
              ) : (
                <MessageSquare className="h-4 w-4" />
              )}
              {reviewSubmitting ? "Submitting..." : "Submit review"}
            </button>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
