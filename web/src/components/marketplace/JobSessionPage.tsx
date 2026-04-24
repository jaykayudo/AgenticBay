"use client";

import {
  ArrowDownToLine,
  ArrowLeft,
  CircleAlert,
  LoaderCircle,
  Logs,
  ShieldCheck,
  Sparkles,
  Wallet,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { useApiQuery } from "@/hooks/useApi";
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
  status: "queued" | "processing" | "awaiting_payment" | "completed" | "cancelled" | "closed";
  mode: "hire" | "demo";
  createdAt: string;
  redirectPath: string;
  sessionToken: string;
  socketUrl: string;
  resultPayload: Record<string, unknown> | null;
};

type OrchestratorEnvelope =
  | {
      type: "START";
      data: {
        job_session_id: string;
        job_session_auth_token: string;
      };
    }
  | {
      type: "SEARCH_AGENT";
      data: {
        agents: Array<{
          id: string;
          name: string;
          description: string;
          rating: number;
          pricing: Record<string, unknown>;
        }>;
      };
    }
  | {
      type: "CONNECT";
      data: {
        agent_id: string;
        capabilities: string;
      };
    }
  | {
      type: "PAYMENT";
      data: {
        amount: number;
        description: string;
        contract_data: {
          invoice_id: string;
          invoice_contract: string;
          function_name: string;
        };
      };
    }
  | {
      type: "PAYMENT_SUCCESSFUL";
      data: {
        invoice_id: string;
      };
    }
  | {
      type: "CLOSE_APPEAL";
      data: {
        message?: string;
        details?: Record<string, unknown>;
      };
    }
  | {
      type: "SERVICE_AGENT";
      message?: string | null;
      data?: Record<string, unknown> | string | null;
    }
  | {
      type: "ERROR";
      data: {
        error_type: string;
        message: string;
      };
    };

type FeedItem = {
  id: string;
  kind: "system" | "orchestrator" | "processing" | "payment" | "confirmation" | "result" | "error";
  type: string;
  title: string;
  body: string;
  timestamp: string;
  payload?: Record<string, unknown> | string | null;
  payment?: {
    amount: number;
    description: string;
    invoiceId: string;
    contractAddress: string;
    functionName: string;
  };
};

type LogItem = {
  id: string;
  tone: "info" | "warning" | "error";
  message: string;
  timestamp: string;
};

type ConnectionState = "connecting" | "connected" | "reconnecting" | "disconnected";

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

const statusLabel: Record<MarketplaceSessionRead["status"], string> = {
  queued: "Queued",
  processing: "Processing",
  awaiting_payment: "Awaiting payment",
  completed: "Completed",
  cancelled: "Cancelled",
  closed: "Closed",
};

function buildSocketUrl(socketUrl: string, sessionToken: string) {
  const url = new URL(socketUrl);
  url.searchParams.set("token", sessionToken);
  return url.toString();
}

function safeStringify(value: unknown) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function isTerminalStatus(status: MarketplaceSessionRead["status"]) {
  return status === "cancelled" || status === "closed";
}

function toneClasses(kind: FeedItem["kind"]) {
  switch (kind) {
    case "payment":
      return "border-emerald-200 bg-emerald-50";
    case "confirmation":
      return "border-blue-200 bg-blue-50";
    case "result":
      return "border-[var(--primary)] bg-[color-mix(in_srgb,var(--primary-soft)_72%,white)]";
    case "error":
      return "border-amber-200 bg-amber-50";
    case "processing":
      return "border-[var(--border)] bg-[var(--surface-2)]";
    case "system":
    case "orchestrator":
    default:
      return "border-[var(--border)] bg-[var(--surface)]";
  }
}

function FeedCard({
  item,
  activePaymentId,
  onPayNow,
}: {
  item: FeedItem;
  activePaymentId: string | null;
  onPayNow: (invoiceId: string) => void;
}) {
  const payment = item.payment;
  const isPaymentCard = item.kind === "payment" && payment && activePaymentId === payment.invoiceId;

  return (
    <article className={cn("rounded-[1.4rem] border p-4 sm:p-5", toneClasses(item.kind))}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-[var(--text)]">{item.title}</p>
          <p className="mt-2 text-sm leading-7 text-[var(--text-muted)]">{item.body}</p>
        </div>
        <span className="text-xs font-medium tracking-[0.18em] text-[var(--text-muted)] uppercase">
          {timeFormatter.format(new Date(item.timestamp))}
        </span>
      </div>

      {payment ? (
        <div className="mt-4 rounded-[1.2rem] border border-[var(--border)] bg-white/70 p-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                Amount
              </p>
              <p className="mt-2 text-base font-semibold text-[var(--text)]">
                {formatUsdc(payment.amount)}
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                Function
              </p>
              <p className="mt-2 text-sm font-medium break-all text-[var(--text)]">
                {payment.functionName}
              </p>
            </div>
          </div>
          <div className="mt-3">
            <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
              Contract
            </p>
            <p className="mt-2 text-sm break-all text-[var(--text)]">{payment.contractAddress}</p>
          </div>

          {isPaymentCard ? (
            <button
              type="button"
              onClick={() => onPayNow(payment.invoiceId)}
              className="mt-4 inline-flex h-11 items-center justify-center rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] transition hover:opacity-90"
            >
              Pay Now
            </button>
          ) : null}
        </div>
      ) : null}

      {item.payload ? (
        <details className="mt-4">
          <summary className="cursor-pointer text-sm font-medium text-[var(--text-muted)]">
            View payload
          </summary>
          <pre className="mt-3 overflow-x-auto rounded-[1rem] border border-[var(--border)] bg-[var(--surface-2)] p-4 text-xs leading-6 text-[var(--text-muted)]">
            {typeof item.payload === "string" ? item.payload : safeStringify(item.payload)}
          </pre>
        </details>
      ) : null}
    </article>
  );
}

export function JobSessionPage({ sessionId }: { sessionId: string }) {
  const sessionQuery = useApiQuery<MarketplaceSessionRead>(
    ["marketplace-job-session", sessionId],
    `/marketplace/sessions/${encodeURIComponent(sessionId)}`,
    {
      enabled: Boolean(sessionId),
    }
  );

  const session = sessionQuery.data;
  const [connectionState, setConnectionState] = useState<ConnectionState>("connecting");
  const [sessionStatus, setSessionStatus] = useState<MarketplaceSessionRead["status"]>("queued");
  const [amountLockedUsdc, setAmountLockedUsdc] = useState(0);
  const [latestProgress, setLatestProgress] = useState<number | null>(null);
  const [activePaymentId, setActivePaymentId] = useState<string | null>(null);
  const [resultPayload, setResultPayload] = useState<Record<string, unknown> | null>(null);
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [logs, setLogs] = useState<LogItem[]>([]);

  const bottomRef = useRef<HTMLDivElement | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelayRef = useRef(1000);
  const manualShutdownRef = useRef(false);
  const sessionStartedRef = useRef(false);
  const initializedRef = useRef(false);
  const currentStatusRef = useRef<MarketplaceSessionRead["status"]>("queued");
  const mockTimersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    currentStatusRef.current = sessionStatus;
  }, [sessionStatus]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [feed.length]);

  function appendLog(message: string, tone: LogItem["tone"] = "info") {
    setLogs((current) => [
      ...current,
      {
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        tone,
        message,
        timestamp: new Date().toISOString(),
      },
    ]);
  }

  function appendFeed(item: Omit<FeedItem, "id" | "timestamp">) {
    setFeed((current) => [
      ...current,
      {
        ...item,
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        timestamp: new Date().toISOString(),
      },
    ]);
  }

  function clearMockTimers() {
    mockTimersRef.current.forEach((timer) => clearTimeout(timer));
    mockTimersRef.current = [];
  }

  function persistMockSession(
    updates: Partial<MockMarketplaceSessionRecord>
  ): MockMarketplaceSessionRecord | null {
    if (!session) {
      return null;
    }

    return patchMockMarketplaceSession(session.sessionId, updates);
  }

  function queueMockTimer(delay: number, callback: () => void) {
    const timer = setTimeout(callback, delay);
    mockTimersRef.current.push(timer);
  }

  function scheduleMockCompletionFlow(
    baseSession: MarketplaceSessionRead,
    amountLocked: number,
    delayOffset = 0
  ) {
    const steps = [
      {
        delay: 600,
        progress: 56,
        message:
          "Orchestrator handed the scoped brief into the execution lane and is collecting outputs.",
        stage: "execution_started",
      },
      {
        delay: 1250,
        progress: 78,
        message:
          "Outputs are being normalized into the delivery package and confidence checks are running.",
        stage: "packaging_results",
      },
      {
        delay: 1900,
        progress: 94,
        message:
          "Final result package is ready. Preparing completion payload for the session feed.",
        stage: "finalizing",
      },
    ];

    steps.forEach((step) => {
      queueMockTimer(delayOffset + step.delay, () => {
        setSessionStatus("processing");
        setLatestProgress(step.progress);
        appendFeed({
          kind: "processing",
          type: "SERVICE_AGENT",
          title: `Processing ${step.progress}%`,
          body: step.message,
          payload: {
            progress: step.progress,
            stage: step.stage,
          },
        });
      });
    });

    queueMockTimer(delayOffset + 2550, () => {
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
      setSessionStatus("completed");
      setLatestProgress(100);
      setResultPayload(result);
      appendFeed({
        kind: "result",
        type: "CLOSE_APPEAL",
        title: "Job completed",
        body: `${baseSession.actionName} completed for ${baseSession.agentName}.`,
        payload: result,
      });
    });
  }

  useEffect(() => {
    if (!session || initializedRef.current) {
      return;
    }

    initializedRef.current = true;
    queueMicrotask(() => {
      setSessionStatus(session.status);
      setAmountLockedUsdc(session.amountLockedUsdc);
      setResultPayload(session.resultPayload);
      appendFeed({
        kind: "system",
        type: "SESSION_OPENED",
        title: "Session opened",
        body: `Connected to ${session.agentName} for ${session.actionName}.`,
        payload: {
          inputSummary: session.inputSummary,
          mode: session.mode,
        },
      });

      if (session.status === "awaiting_payment") {
        const invoiceId = `mock-invoice-${session.sessionId.slice(0, 8)}`;
        appendFeed({
          kind: "payment",
          type: "PAYMENT",
          title: "Escrow payment requested",
          body: `Escrow deposit for ${session.actionName}.`,
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
      }

      if (session.status === "completed" && session.resultPayload) {
        appendFeed({
          kind: "result",
          type: "CLOSE_APPEAL",
          title: "Job completed",
          body: `${session.actionName} completed for ${session.agentName}.`,
          payload: session.resultPayload,
        });
      }
    });
  }, [session]);

  useEffect(() => {
    if (!session?.sessionToken || !session.socketUrl) {
      return;
    }

    manualShutdownRef.current = false;
    let disposed = false;

    if (session.socketUrl.startsWith("mock://")) {
      clearMockTimers();
      queueMockTimer(0, () => {
        setConnectionState("connecting");
        appendLog("Using mocked marketplace session data.");
      });

      queueMockTimer(180, () => {
        if (disposed) {
          return;
        }

        setConnectionState("connected");
        appendLog("Mock session connected.");

        if (session.status === "queued") {
          sessionStartedRef.current = true;
          persistMockSession({ status: "processing" });
          setSessionStatus("processing");
          appendFeed({
            kind: "system",
            type: "SERVICE_AGENT",
            title: "User agent kickoff",
            body: `Requested execution for ${session.actionName}.`,
            payload: {
              actionId: session.actionId,
              inputSummary: session.inputSummary,
              mode: session.mode,
            },
          });
          appendFeed({
            kind: "processing",
            type: "SERVICE_AGENT",
            title: "Processing 18%",
            body: "Orchestrator is analyzing the job brief and preparing execution steps.",
            payload: {
              progress: 18,
              stage: "planning",
            },
          });
          setLatestProgress(18);

          queueMockTimer(700, () => {
            setLatestProgress(28);
            appendFeed({
              kind: "processing",
              type: "SERVICE_AGENT",
              title: "Processing 28%",
              body: "Initial plan assembled. The next step is validating scope and escrow requirements.",
              payload: {
                progress: 28,
                stage: "scope_validated",
              },
            });
          });

          if (session.mode === "demo" || session.priceUsdc === 0) {
            scheduleMockCompletionFlow(session, 0, 1050);
          } else {
            queueMockTimer(1250, () => {
              const invoiceId = `mock-invoice-${session.sessionId.slice(0, 8)}`;
              persistMockSession({ status: "awaiting_payment" });
              setSessionStatus("awaiting_payment");
              setActivePaymentId(invoiceId);
              appendFeed({
                kind: "payment",
                type: "PAYMENT",
                title: "Escrow payment requested",
                body: `Escrow deposit for ${session.actionName}.`,
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
        } else if (session.status === "processing") {
          setLatestProgress((current) => current ?? 42);
          appendLog("Restored mock session in processing state.");
        } else if (session.status === "awaiting_payment") {
          setActivePaymentId(`mock-invoice-${session.sessionId.slice(0, 8)}`);
          appendLog("Restored mock session waiting for payment.");
        } else if (session.status === "completed") {
          appendLog("Restored mock session with completed result.");
        }
      });

      return () => {
        disposed = true;
        manualShutdownRef.current = true;
        clearMockTimers();
      };
    }

    const connect = () => {
      const nextState = reconnectDelayRef.current > 1000 ? "reconnecting" : "connecting";
      setConnectionState(nextState);
      appendLog(
        nextState === "reconnecting"
          ? "Attempting to reconnect to the orchestrator WebSocket."
          : "Opening orchestrator WebSocket for this job session."
      );

      const ws = new WebSocket(buildSocketUrl(session.socketUrl, session.sessionToken));
      socketRef.current = ws;

      ws.onopen = () => {
        if (disposed) {
          return;
        }

        reconnectDelayRef.current = 1000;
        setConnectionState("connected");
        appendLog("WebSocket connected.");

        if (!sessionStartedRef.current && session.status === "queued") {
          sessionStartedRef.current = true;

          const kickoff = {
            type: "SERVICE_AGENT",
            data: {
              command: session.actionName,
              arguments: {
                actionId: session.actionId,
                inputSummary: session.inputSummary,
                mode: session.mode,
              },
            },
          };

          ws.send(JSON.stringify(kickoff));
          appendLog(`Sent SERVICE_AGENT kickoff for ${session.actionName}.`);
          appendFeed({
            kind: "system",
            type: "SERVICE_AGENT",
            title: "User agent kickoff",
            body: `Requested execution for ${session.actionName}.`,
            payload: kickoff.data,
          });
          setSessionStatus("processing");
        }
      };

      ws.onmessage = (event) => {
        appendLog("Received orchestrator message.");

        let parsed: OrchestratorEnvelope;
        try {
          parsed = JSON.parse(String(event.data)) as OrchestratorEnvelope;
        } catch {
          appendLog("Received a non-JSON message from the WebSocket.", "warning");
          appendFeed({
            kind: "error",
            type: "RAW",
            title: "Unrecognized message",
            body: String(event.data),
          });
          return;
        }

        switch (parsed.type) {
          case "START":
            appendFeed({
              kind: "system",
              type: parsed.type,
              title: "Session token confirmed",
              body: `Session ${parsed.data.job_session_id} is ready for orchestrator traffic.`,
              payload: parsed.data,
            });
            break;
          case "SEARCH_AGENT":
            appendFeed({
              kind: "orchestrator",
              type: parsed.type,
              title: "Search response",
              body: `The orchestrator returned ${parsed.data.agents.length} candidate agents.`,
              payload: parsed.data,
            });
            break;
          case "CONNECT":
            appendFeed({
              kind: "orchestrator",
              type: parsed.type,
              title: "Agent connected",
              body: `Connected to agent ${parsed.data.agent_id}.`,
              payload: {
                agentId: parsed.data.agent_id,
                capabilities: parsed.data.capabilities,
              },
            });
            setSessionStatus("processing");
            break;
          case "PAYMENT":
            setSessionStatus("awaiting_payment");
            setActivePaymentId(parsed.data.contract_data.invoice_id);
            appendFeed({
              kind: "payment",
              type: parsed.type,
              title: "Escrow payment requested",
              body: parsed.data.description,
              payload: parsed.data,
              payment: {
                amount: parsed.data.amount,
                description: parsed.data.description,
                invoiceId: parsed.data.contract_data.invoice_id,
                contractAddress: parsed.data.contract_data.invoice_contract,
                functionName: parsed.data.contract_data.function_name,
              },
            });
            break;
          case "PAYMENT_SUCCESSFUL":
            setSessionStatus("processing");
            setAmountLockedUsdc(session.priceUsdc);
            setActivePaymentId(null);
            appendFeed({
              kind: "confirmation",
              type: parsed.type,
              title: "Payment confirmed",
              body: `Invoice ${parsed.data.invoice_id} has been confirmed and funds are now locked in escrow.`,
              payload: parsed.data,
            });
            break;
          case "CLOSE_APPEAL":
            setSessionStatus("completed");
            setResultPayload((parsed.data.details as Record<string, unknown> | undefined) ?? null);
            appendFeed({
              kind: "result",
              type: parsed.type,
              title: "Job completed",
              body: parsed.data.message ?? "The orchestrator returned a final result package.",
              payload: parsed.data.details ?? parsed.data,
            });
            break;
          case "SERVICE_AGENT": {
            const payload = parsed.data && typeof parsed.data === "object" ? parsed.data : null;
            const status = payload?.status;
            const progressValue = typeof payload?.progress === "number" ? payload.progress : null;
            const amountLocked =
              typeof payload?.amountLockedUsdc === "number" ? payload.amountLockedUsdc : null;

            if (progressValue !== null) {
              setLatestProgress(progressValue);
            }
            if (amountLocked !== null) {
              setAmountLockedUsdc(amountLocked);
            }
            if (status === "cancelled" || status === "closed") {
              setSessionStatus(status);
            } else if (currentStatusRef.current !== "awaiting_payment") {
              setSessionStatus("processing");
            }

            appendFeed({
              kind: progressValue !== null ? "processing" : "orchestrator",
              type: parsed.type,
              title:
                progressValue !== null ? `Processing ${progressValue}%` : "Orchestrator update",
              body:
                parsed.message ??
                (typeof parsed.data === "string"
                  ? parsed.data
                  : "The orchestrator sent an execution update."),
              payload: parsed.data ?? null,
            });
            break;
          }
          case "ERROR":
            appendFeed({
              kind: "error",
              type: parsed.type,
              title: parsed.data.error_type,
              body: parsed.data.message,
              payload: parsed.data,
            });
            appendLog(`Orchestrator error: ${parsed.data.message}`, "error");
            break;
          default:
            appendFeed({
              kind: "orchestrator",
              type: "UNKNOWN",
              title: "Unknown message",
              body: "The orchestrator sent a message type this page does not explicitly recognize.",
              payload: parsed,
            });
        }
      };

      ws.onerror = () => {
        appendLog("WebSocket error detected.", "warning");
      };

      ws.onclose = () => {
        if (disposed) {
          return;
        }

        setConnectionState("disconnected");
        appendLog("WebSocket disconnected.", "warning");

        if (!manualShutdownRef.current && !isTerminalStatus(currentStatusRef.current)) {
          const delay = reconnectDelayRef.current;
          appendLog(`Scheduling reconnect in ${Math.round(delay / 1000)}s.`, "warning");
          reconnectTimerRef.current = setTimeout(() => {
            reconnectDelayRef.current = Math.min(reconnectDelayRef.current * 2, 30000);
            connect();
          }, delay);
        }
      };
    };

    connect();

    return () => {
      disposed = true;
      manualShutdownRef.current = true;
      clearMockTimers();
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      socketRef.current?.close();
    };
  }, [session]);

  function sendPayload(payload: Record<string, unknown>) {
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      appendLog("Tried to send a message while the WebSocket was not open.", "error");
      return false;
    }

    socket.send(JSON.stringify(payload));
    appendLog(`Sent ${String(payload.type)} message to the orchestrator.`);
    return true;
  }

  function handlePayNow(invoiceId: string) {
    if (session?.socketUrl.startsWith("mock://")) {
      clearMockTimers();
      persistMockSession({
        status: "processing",
        amountLockedUsdc: session.priceUsdc,
      });
      setActivePaymentId(null);
      setAmountLockedUsdc(session.priceUsdc);
      setSessionStatus("processing");
      appendFeed({
        kind: "confirmation",
        type: "PAYMENT_SUCCESSFUL",
        title: "Payment confirmed",
        body: `Invoice ${invoiceId} has been confirmed and funds are now locked in escrow.`,
        payload: {
          invoiceId,
          amountLockedUsdc: session.priceUsdc,
        },
      });
      scheduleMockCompletionFlow(session, session.priceUsdc);
      return;
    }

    const sent = sendPayload({
      type: "PAYMENT_SUCCESSFUL",
      data: {
        invoice_id: invoiceId,
      },
    });

    if (sent) {
      appendFeed({
        kind: "system",
        type: "PAYMENT_SUCCESSFUL",
        title: "Payment submitted",
        body: `Submitted payment confirmation for invoice ${invoiceId}.`,
      });
    }
  }

  function handleCancelJob() {
    if (!session || isTerminalStatus(sessionStatus) || sessionStatus === "completed") {
      return;
    }

    if (
      !window.confirm("Cancel this job session? The orchestrator will stop further processing.")
    ) {
      return;
    }

    if (session.socketUrl.startsWith("mock://")) {
      clearMockTimers();
      persistMockSession({ status: "cancelled" });
      setSessionStatus("cancelled");
      appendLog("Mock session canceled by the user.", "warning");
      appendFeed({
        kind: "system",
        type: "CLOSE",
        title: "Cancel requested",
        body: "The user agent asked the orchestrator to close this job session.",
      });
      appendFeed({
        kind: "orchestrator",
        type: "SERVICE_AGENT",
        title: "Session cancelled",
        body: "The mocked orchestrator stopped further processing for this job.",
        payload: {
          status: "cancelled",
        },
      });
      return;
    }

    const sent = sendPayload({
      type: "CLOSE",
      data: {
        reason: "user_cancelled",
      },
    });

    if (sent) {
      appendFeed({
        kind: "system",
        type: "CLOSE",
        title: "Cancel requested",
        body: "The user agent asked the orchestrator to close this job session.",
      });
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

  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--foreground)]">
      <div className="mx-auto max-w-[var(--layout-max)] px-4 py-6 md:px-6 xl:px-8">
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
          <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
            <div className="space-y-6">
              <section className="app-panel p-5 sm:p-6">
                <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="app-status-badge" data-tone="accent">
                        Job {session.sessionId.slice(0, 8)}
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
                    </div>
                    <h1 className="mt-4 text-[clamp(1.8rem,3vw,2.6rem)] font-semibold tracking-[-0.05em] text-[var(--text)]">
                      Real-time job session
                    </h1>
                    <p className="mt-3 max-w-3xl text-sm leading-7 text-[var(--text-muted)] sm:text-[15px]">
                      This page keeps a live WebSocket open to the orchestration agent so you can
                      watch progress, respond to payment prompts, and review final results.
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={handleCancelJob}
                    disabled={
                      sessionStatus === "completed" ||
                      sessionStatus === "cancelled" ||
                      sessionStatus === "closed"
                    }
                    className="inline-flex h-11 items-center justify-center gap-2 rounded-full border border-rose-200 px-5 text-sm font-semibold text-rose-700 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-45"
                  >
                    <XCircle className="h-4 w-4" />
                    Cancel Job
                  </button>
                </div>
              </section>

              <section className="app-panel p-5 sm:p-6">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <h2 className="text-lg font-semibold tracking-[-0.03em] text-[var(--text)]">
                      Session feed
                    </h2>
                    <p className="mt-2 text-sm leading-7 text-[var(--text-muted)]">
                      Live chronological updates from the orchestrator, including payment and result
                      events.
                    </p>
                  </div>
                  {latestProgress !== null ? (
                    <div className="rounded-full border border-[var(--border)] px-3 py-1 text-sm font-medium text-[var(--text-muted)]">
                      {latestProgress}% progress
                    </div>
                  ) : null}
                </div>

                <div className="mt-6 space-y-4">
                  {feed.map((item) => (
                    <FeedCard
                      key={item.id}
                      item={item}
                      activePaymentId={activePaymentId}
                      onPayNow={handlePayNow}
                    />
                  ))}
                  <div ref={bottomRef} />
                </div>
              </section>

              <section className="app-panel p-5 sm:p-6">
                <details>
                  <summary className="flex cursor-pointer items-center gap-2 text-sm font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                    <Logs className="h-4 w-4" />
                    Live logs
                  </summary>
                  <div className="mt-4 space-y-3">
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
                              ? "border-amber-200 bg-amber-50 text-amber-900"
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
                <section className="app-panel p-5 sm:p-6">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <h2 className="text-lg font-semibold tracking-[-0.03em] text-[var(--text)]">
                        Result package
                      </h2>
                      <p className="mt-2 text-sm leading-7 text-[var(--text-muted)]">
                        The orchestrator marked the job complete and published the final result
                        payload below.
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-3">
                      <button
                        type="button"
                        onClick={() => downloadResult("json")}
                        className="inline-flex h-10 items-center justify-center gap-2 rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text-muted)] transition hover:border-[var(--primary)] hover:text-[var(--primary)]"
                      >
                        <ArrowDownToLine className="h-4 w-4" />
                        Download JSON
                      </button>
                      <button
                        type="button"
                        onClick={() => downloadResult("txt")}
                        className="inline-flex h-10 items-center justify-center gap-2 rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text-muted)] transition hover:border-[var(--primary)] hover:text-[var(--primary)]"
                      >
                        <ArrowDownToLine className="h-4 w-4" />
                        Download text
                      </button>
                    </div>
                  </div>

                  <pre className="mt-5 overflow-x-auto rounded-[1.4rem] border border-[var(--border)] bg-[var(--surface-2)] p-4 text-xs leading-6 text-[var(--text-muted)]">
                    {safeStringify(resultPayload)}
                  </pre>
                </section>
              ) : null}
            </div>

            <aside className="space-y-4 xl:sticky xl:top-24 xl:self-start">
              <section className="app-panel p-5 sm:p-6">
                <div className="flex items-center gap-3">
                  <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[var(--primary-soft)] text-[var(--primary)]">
                    <Wallet className="h-5 w-5" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold tracking-[-0.03em] text-[var(--text)]">
                      Job details
                    </h2>
                    <p className="mt-1 text-sm text-[var(--text-muted)]">
                      Action, scope summary, and escrow state for this live session.
                    </p>
                  </div>
                </div>

                <div className="mt-5 space-y-3">
                  <div className="app-subtle rounded-2xl p-4">
                    <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                      Agent
                    </p>
                    <p className="mt-2 text-base font-semibold text-[var(--text)]">
                      {session.agentName}
                    </p>
                  </div>
                  <div className="app-subtle rounded-2xl p-4">
                    <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                      Action
                    </p>
                    <p className="mt-2 text-base font-semibold text-[var(--text)]">
                      {session.actionName}
                    </p>
                  </div>
                  <div className="app-subtle rounded-2xl p-4">
                    <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                      Input summary
                    </p>
                    <p className="mt-2 text-sm leading-7 text-[var(--text-muted)]">
                      {session.inputSummary}
                    </p>
                  </div>
                  <div className="app-subtle rounded-2xl p-4">
                    <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                      Amount locked in escrow
                    </p>
                    <p className="mt-2 text-base font-semibold text-[var(--text)]">
                      {amountLockedUsdc > 0 ? formatUsdc(amountLockedUsdc) : "0 USDC"}
                    </p>
                  </div>
                </div>
              </section>

              <section className="app-panel p-5 sm:p-6">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-[var(--primary)]" />
                  <h3 className="text-sm font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                    Session status
                  </h3>
                </div>

                <div className="mt-4 space-y-3">
                  <div className="app-subtle rounded-2xl p-4">
                    <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                      Current state
                    </p>
                    <p className="mt-2 text-base font-semibold text-[var(--text)]">
                      {statusLabel[sessionStatus]}
                    </p>
                  </div>
                  <div className="app-subtle rounded-2xl p-4">
                    <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                      Delivery window
                    </p>
                    <p className="mt-2 text-base font-semibold text-[var(--text)]">
                      {session.estimatedDurationLabel}
                    </p>
                  </div>
                  <div className="app-subtle rounded-2xl p-4">
                    <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                      Created
                    </p>
                    <p className="mt-2 text-base font-semibold text-[var(--text)]">
                      {dateTimeFormatter.format(new Date(session.createdAt))}
                    </p>
                  </div>
                </div>

                <div className="mt-5 rounded-[1.3rem] border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3 text-sm text-[var(--text-muted)]">
                  <div className="flex items-start gap-2">
                    <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-[var(--primary)]" />
                    <p>
                      The feed auto-scrolls, reconnects when the socket drops, and keeps the latest
                      payment and result state in sync.
                    </p>
                  </div>
                </div>
              </section>
            </aside>
          </div>
        ) : null}
      </div>
    </div>
  );
}
