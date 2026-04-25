"use client";

import {
  ArrowRight,
  Bot,
  Check,
  ChevronDown,
  CircleAlert,
  Clock3,
  Command,
  LoaderCircle,
  Paperclip,
  RefreshCw,
  Search,
  Send,
  Sparkles,
  Star,
  UserRound,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ThemeToggle } from "@/components/theme-toggle";
import { apiFetch } from "@/lib/api";
import {
  formatUsdc,
  getMarketplaceAgentDetail,
  marketplaceAgentDetails,
  type MarketplaceAgentAction,
  type MarketplaceAgentDetail,
} from "@/lib/marketplace-data";
import { cn } from "@/lib/utils";

type ConnectionState = "connecting" | "connected" | "reconnecting" | "disconnected";
type MessageKind =
  | "user"
  | "message"
  | "recommendation"
  | "clarification"
  | "plan"
  | "cost"
  | "error";

type ConversationMessage = {
  id: string;
  kind: MessageKind;
  title: string;
  body: string;
  timestamp: string;
};

type AgentSuggestion = {
  agent: MarketplaceAgentDetail;
  action: MarketplaceAgentAction;
  matchReason: string;
  estimatedCost: number;
  estimatedTime: string;
};

type ExecutionPlan = {
  selectedAgent: MarketplaceAgentDetail;
  action: MarketplaceAgentAction;
  inputSummary: string;
  estimatedCost: number;
  estimatedTime: string;
  steps: string[];
};

type MarketplaceSessionRead = {
  redirectPath: string;
};

const promptSuggestions = [
  "Scrape data from a website",
  "Analyze a dataset",
  "Write a blog post",
  "Do market research",
];

const timeFormatter = new Intl.DateTimeFormat("en-US", {
  hour: "numeric",
  minute: "2-digit",
  second: "2-digit",
});

function makeId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function tokenize(value: string) {
  return value
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean);
}

function scoreAgent(agent: MarketplaceAgentDetail, query: string) {
  const tokens = tokenize(query);
  const haystack = [
    agent.name,
    agent.description,
    agent.headline,
    ...agent.tags,
    ...agent.categories,
    ...agent.actions.map((action) => `${action.name} ${action.description}`),
  ]
    .join(" ")
    .toLowerCase();

  const keywordScore = tokens.reduce(
    (score, token) => score + (haystack.includes(token) ? 18 : 0),
    0
  );
  const categoryBoost =
    (query.includes("scrape") || query.includes("automate") || query.includes("workflow")) &&
    agent.categories.includes("automation")
      ? 24
      : query.includes("research") && agent.categories.includes("research")
        ? 28
        : query.includes("blog") && agent.categories.includes("content")
          ? 28
          : query.includes("dataset") && agent.categories.includes("data-analysis")
            ? 28
            : 0;

  return (
    keywordScore +
    categoryBoost +
    agent.rating * 8 +
    agent.successRate * 0.4 +
    (6 - agent.speedRank) * 5 -
    agent.startingPriceUsdc * 0.025
  );
}

function selectAction(agent: MarketplaceAgentDetail, query: string) {
  const normalized = query.toLowerCase();

  if (
    normalized.includes("full") ||
    normalized.includes("ongoing") ||
    normalized.includes("end-to-end")
  ) {
    return agent.actions[2] ?? agent.actions[0];
  }

  if (
    normalized.includes("deep") ||
    normalized.includes("report") ||
    normalized.includes("campaign")
  ) {
    return agent.actions[1] ?? agent.actions[0];
  }

  return agent.actions[0];
}

function buildSuggestions(query: string) {
  return marketplaceAgentDetails
    .map((agent) => {
      const action = selectAction(agent, query);

      return {
        agent,
        action,
        matchReason: `${agent.name} matches this request through ${agent.tags.slice(0, 2).join(" and ").toLowerCase()} with ${agent.successRate.toFixed(1)}% historical success.`,
        estimatedCost: action.priceUsdc,
        estimatedTime: action.estimatedDurationLabel,
        score: scoreAgent(agent, query),
      };
    })
    .sort((left, right) => right.score - left.score)
    .slice(0, 4)
    .map(({ score: _score, ...suggestion }) => suggestion);
}

function MessageIcon({ kind }: { kind: MessageKind }) {
  if (kind === "user") {
    return <UserRound className="h-4 w-4" />;
  }

  if (kind === "recommendation") {
    return <Search className="h-4 w-4" />;
  }

  if (kind === "plan") {
    return <Check className="h-4 w-4" />;
  }

  if (kind === "cost") {
    return <Wallet className="h-4 w-4" />;
  }

  if (kind === "error") {
    return <CircleAlert className="h-4 w-4" />;
  }

  return <Bot className="h-4 w-4" />;
}

function messageTone(kind: MessageKind) {
  switch (kind) {
    case "user":
      return "ml-auto border-[var(--primary)]/30 bg-[var(--primary-soft)]";
    case "recommendation":
      return "border-sky-200 bg-sky-50";
    case "plan":
      return "border-emerald-200 bg-emerald-50";
    case "cost":
      return "border-amber-200 bg-amber-50";
    case "error":
      return "border-rose-200 bg-rose-50";
    case "clarification":
      return "border-[var(--primary)] bg-[color-mix(in_srgb,var(--primary-soft)_72%,white)]";
    case "message":
    default:
      return "border-[var(--border)] bg-[var(--surface)]";
  }
}

function RecommendationCard({
  suggestion,
  selected,
  disabled,
  alternativesOpen,
  alternatives,
  onProceed,
  onToggleAlternatives,
  onSelectAlternative,
}: {
  suggestion: AgentSuggestion;
  selected: boolean;
  disabled: boolean;
  alternativesOpen: boolean;
  alternatives: AgentSuggestion[];
  onProceed: () => void;
  onToggleAlternatives: () => void;
  onSelectAlternative: (suggestion: AgentSuggestion) => void;
}) {
  return (
    <section className="app-panel p-5 sm:p-6">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex min-w-0 gap-4">
          <div
            className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl text-sm font-semibold shadow-[var(--shadow-soft)]"
            style={{
              backgroundColor: suggestion.agent.avatar.bg,
              color: suggestion.agent.avatar.fg,
            }}
          >
            {suggestion.agent.avatar.label}
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-semibold text-[var(--text)]">{suggestion.agent.name}</h2>
              <span className="app-status-badge" data-tone="accent">
                Recommended
              </span>
            </div>
            <p className="mt-2 text-sm leading-7 text-[var(--text-muted)]">
              {suggestion.agent.description}
            </p>
            <p className="mt-3 text-sm leading-6 text-[var(--text)]">{suggestion.matchReason}</p>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-3 lg:min-w-[340px]">
          <div className="app-subtle p-3">
            <p className="text-xs text-[var(--text-muted)]">Success</p>
            <p className="mt-1 font-semibold text-[var(--text)]">
              {suggestion.agent.successRate.toFixed(1)}%
            </p>
          </div>
          <div className="app-subtle p-3">
            <p className="text-xs text-[var(--text-muted)]">Cost</p>
            <p className="mt-1 font-semibold text-[var(--text)]">
              {formatUsdc(suggestion.estimatedCost)}
            </p>
          </div>
          <div className="app-subtle p-3">
            <p className="text-xs text-[var(--text-muted)]">Time</p>
            <p className="mt-1 font-semibold text-[var(--text)]">{suggestion.estimatedTime}</p>
          </div>
        </div>
      </div>

      <div className="mt-5 flex flex-col gap-3 sm:flex-row">
        <button
          type="button"
          disabled={disabled}
          onClick={onProceed}
          className="inline-flex h-11 items-center justify-center gap-2 rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] disabled:opacity-50"
        >
          {selected ? <Check className="h-4 w-4" /> : <ArrowRight className="h-4 w-4" />}
          {selected ? "Selected" : "Proceed with this agent"}
        </button>
        <button
          type="button"
          onClick={onToggleAlternatives}
          className="inline-flex h-11 items-center justify-center gap-2 rounded-full border border-[var(--border)] px-5 text-sm font-semibold text-[var(--text)]"
        >
          View alternatives
          <ChevronDown
            className={cn("h-4 w-4 transition-transform", alternativesOpen && "rotate-180")}
          />
        </button>
      </div>

      {alternativesOpen ? (
        <div className="mt-5 space-y-3 border-t border-[var(--border)] pt-5">
          {alternatives.map((alternative) => (
            <article
              key={alternative.agent.slug}
              className="flex flex-col gap-3 rounded-2xl border border-[var(--border)] bg-[var(--surface-2)] p-4 sm:flex-row sm:items-center sm:justify-between"
            >
              <div>
                <p className="font-semibold text-[var(--text)]">{alternative.agent.name}</p>
                <div className="mt-1 flex flex-wrap gap-3 text-sm text-[var(--text-muted)]">
                  <span>{formatUsdc(alternative.estimatedCost)}</span>
                  <span className="inline-flex items-center gap-1">
                    <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                    {alternative.agent.rating.toFixed(1)}
                  </span>
                  <span>{alternative.estimatedTime}</span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => onSelectAlternative(alternative)}
                className="inline-flex h-10 items-center justify-center rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 text-sm font-semibold text-[var(--text)]"
              >
                Select
              </button>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function ExecutionPlanCard({
  plan,
  disabled,
  onConfirm,
  onEdit,
}: {
  plan: ExecutionPlan;
  disabled: boolean;
  onConfirm: () => void;
  onEdit: () => void;
}) {
  return (
    <section className="app-panel p-5 sm:p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <span className="app-status-badge" data-tone="accent">
            Execution plan
          </span>
          <h2 className="mt-3 text-xl font-semibold text-[var(--text)]">
            {plan.action.name} with {plan.selectedAgent.name}
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-7 text-[var(--text-muted)]">
            {plan.inputSummary}
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:min-w-[280px]">
          <div className="app-subtle p-3">
            <p className="text-xs text-[var(--text-muted)]">Estimated cost</p>
            <p className="mt-1 font-semibold text-[var(--text)]">
              {formatUsdc(plan.estimatedCost)}
            </p>
          </div>
          <div className="app-subtle p-3">
            <p className="text-xs text-[var(--text-muted)]">Estimated time</p>
            <p className="mt-1 font-semibold text-[var(--text)]">{plan.estimatedTime}</p>
          </div>
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        {plan.steps.map((step, index) => (
          <div
            key={step}
            className="rounded-2xl border border-[var(--border)] bg-[var(--surface-2)] p-4"
          >
            <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
              Step {index + 1}
            </p>
            <p className="mt-2 text-sm leading-6 text-[var(--text)]">{step}</p>
          </div>
        ))}
      </div>

      <div className="mt-5 flex flex-col gap-3 sm:flex-row">
        <button
          type="button"
          disabled={disabled}
          onClick={onConfirm}
          className="inline-flex h-11 items-center justify-center gap-2 rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] disabled:opacity-50"
        >
          {disabled ? (
            <LoaderCircle className="h-4 w-4 animate-spin" />
          ) : (
            <Check className="h-4 w-4" />
          )}
          Confirm & Start Job
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={onEdit}
          className="inline-flex h-11 items-center justify-center rounded-full border border-[var(--border)] px-5 text-sm font-semibold text-[var(--text)] disabled:opacity-50"
        >
          Edit Task
        </button>
      </div>
    </section>
  );
}

export function OrchestratorInterfacePage() {
  const router = useRouter();
  const [connectionState, setConnectionState] = useState<ConnectionState>("connecting");
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [composerValue, setComposerValue] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [suggestions, setSuggestions] = useState<AgentSuggestion[]>([]);
  const [selectedSuggestion, setSelectedSuggestion] = useState<AgentSuggestion | null>(null);
  const [plan, setPlan] = useState<ExecutionPlan | null>(null);
  const [alternativesOpen, setAlternativesOpen] = useState(false);
  const [startingJob, setStartingJob] = useState(false);
  const [socketNotice, setSocketNotice] = useState("Opening orchestrator channel");

  const bottomRef = useRef<HTMLDivElement | null>(null);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, suggestions.length, plan]);

  useEffect(() => {
    timersRef.current.push(
      setTimeout(() => {
        setConnectionState("connected");
        setSocketNotice("Orchestrator connected");
      }, 350)
    );

    return () => {
      timersRef.current.forEach((timer) => clearTimeout(timer));
      timersRef.current = [];
    };
  }, []);

  const appendMessage = useCallback((message: Omit<ConversationMessage, "id" | "timestamp">) => {
    setMessages((current) => [
      ...current,
      {
        ...message,
        id: makeId("message"),
        timestamp: new Date().toISOString(),
      },
    ]);
  }, []);

  function buildPlan(suggestion: AgentSuggestion, task: string): ExecutionPlan {
    return {
      selectedAgent: suggestion.agent,
      action: suggestion.action,
      inputSummary: task,
      estimatedCost: suggestion.estimatedCost,
      estimatedTime: suggestion.estimatedTime,
      steps: [
        "Clarify scope and transform the natural language request into an executable job brief.",
        `Route execution to ${suggestion.agent.name} using ${suggestion.action.name}.`,
        "Lock estimated USDC in escrow, stream progress, and return a reviewable result package.",
      ],
    };
  }

  function processTask(task: string) {
    setIsThinking(true);
    setSuggestions([]);
    setSelectedSuggestion(null);
    setPlan(null);
    setAlternativesOpen(false);

    appendMessage({
      kind: "user",
      title: "You",
      body: task,
    });

    timersRef.current.push(
      setTimeout(() => {
        appendMessage({
          kind: "message",
          title: "Orchestrator",
          body: "I am interpreting the task, checking marketplace capability fit, and estimating the delivery path.",
        });
      }, 350),
      setTimeout(() => {
        const nextSuggestions = buildSuggestions(task);

        if (task.trim().split(/\s+/).length < 3) {
          appendMessage({
            kind: "clarification",
            title: "Clarification required",
            body: "I can route this, but a little more detail will improve the match. What source, audience, or output format should the agent optimize for?",
          });
        }

        setSuggestions(nextSuggestions);
        const best = nextSuggestions[0];
        if (best) {
          appendMessage({
            kind: "recommendation",
            title: "Agent suggestion",
            body: `${best.agent.name} is the strongest match. Estimated cost is ${formatUsdc(best.estimatedCost)} with an expected turnaround of ${best.estimatedTime}.`,
          });
        }
      }, 950),
      setTimeout(() => {
        const nextSuggestions = buildSuggestions(task);
        const best = nextSuggestions[0];
        if (best) {
          const nextPlan = buildPlan(best, task);
          setSelectedSuggestion(best);
          setPlan(nextPlan);
          appendMessage({
            kind: "plan",
            title: "Execution plan proposed",
            body: `I prepared a plan for ${best.agent.name}. Review it, edit the task if needed, then confirm to create the job.`,
          });
          appendMessage({
            kind: "cost",
            title: "Cost estimate",
            body: `${formatUsdc(nextPlan.estimatedCost)} will be locked in escrow when you confirm the job.`,
          });
        } else {
          appendMessage({
            kind: "error",
            title: "No strong agent match",
            body: "I could not find a reliable marketplace match. Try adding more detail or browse the marketplace manually.",
          });
        }
        setIsThinking(false);
      }, 1550)
    );
  }

  function submitTask() {
    const task = composerValue.trim();
    if (!task || isThinking) {
      return;
    }

    setComposerValue("");
    processTask(task);
  }

  function selectSuggestion(suggestion: AgentSuggestion) {
    setSelectedSuggestion(suggestion);
    const latestUserTask =
      [...messages].reverse().find((message) => message.kind === "user")?.body ?? composerValue;
    const nextPlan = buildPlan(suggestion, latestUserTask || suggestion.action.description);
    setPlan(nextPlan);
    appendMessage({
      kind: "plan",
      title: "Agent selected",
      body: `${suggestion.agent.name} is selected. The execution plan has been updated with its pricing and delivery window.`,
    });
  }

  async function confirmAndStartJob() {
    if (!plan) {
      return;
    }

    setStartingJob(true);
    appendMessage({
      kind: "message",
      title: "Orchestrator",
      body: "Creating the job session and preparing escrow lock. You will be redirected to the live workspace.",
    });

    try {
      const detail = getMarketplaceAgentDetail(plan.selectedAgent.slug);
      const action = detail?.actions.find((item) => item.id === plan.action.id) ?? plan.action;
      const session = await apiFetch<MarketplaceSessionRead>(
        `/marketplace/agents/${encodeURIComponent(plan.selectedAgent.slug)}/sessions`,
        {
          method: "post",
          data: {
            actionId: action.id,
            actionName: action.name,
            priceUsdc: action.priceUsdc,
            estimatedDurationLabel: action.estimatedDurationLabel,
            inputSummary: plan.inputSummary,
            mode: "hire",
          },
        }
      );

      router.push(session.redirectPath);
    } catch {
      setStartingJob(false);
      appendMessage({
        kind: "error",
        title: "Job creation failed",
        body: "The orchestrator could not create the job session. Please try again.",
      });
    }
  }

  const connectionLabel = useMemo(() => {
    switch (connectionState) {
      case "connected":
        return "Live";
      case "reconnecting":
        return "Reconnecting";
      case "disconnected":
        return "Disconnected";
      default:
        return "Connecting";
    }
  }, [connectionState]);

  const bestSuggestion = selectedSuggestion ?? suggestions[0] ?? null;
  const alternatives = suggestions.filter(
    (suggestion) => suggestion.agent.slug !== bestSuggestion?.agent.slug
  );

  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--foreground)]">
      <header className="sticky top-0 z-40 border-b border-[var(--border)] bg-[color-mix(in_srgb,var(--bg-elevated)_92%,transparent)] backdrop-blur">
        <div className="mx-auto flex max-w-[var(--layout-max)] flex-col gap-4 px-4 py-4 md:px-6 xl:flex-row xl:items-center xl:justify-between xl:px-8">
          <Link href="/orchestrator" className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[var(--primary)] text-white shadow-[var(--shadow-soft)]">
              <Command className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-semibold tracking-[0.2em] text-[var(--text-muted)] uppercase">
                AgenticBay
              </p>
              <p className="mt-1 text-sm text-[var(--text-muted)]">Orchestrator</p>
            </div>
          </Link>

          <nav className="flex flex-wrap items-center gap-2 text-sm font-medium text-[var(--text-muted)]">
            <Link
              className="rounded-full px-3 py-2 transition hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
              href="/marketplace"
            >
              Marketplace
            </Link>
            <Link
              className="rounded-full px-3 py-2 transition hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
              href="/dashboard"
            >
              Dashboard
            </Link>
            <Link
              className="rounded-full px-3 py-2 transition hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
              href="/dashboard/wallet"
            >
              Wallet
            </Link>
          </nav>

          <div className="flex items-center justify-between gap-3 xl:justify-end">
            <span
              className="app-status-badge"
              data-tone={connectionState === "connected" ? "accent" : "default"}
            >
              {connectionLabel}
            </span>
            <ThemeToggle />
            <div className="grid h-10 w-10 place-items-center rounded-full border border-[var(--border)] bg-[var(--surface)] text-sm font-semibold text-[var(--text)]">
              MB
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-5xl gap-5 px-4 py-6 md:px-6 xl:px-8">
        <section className="text-center">
          <span className="app-status-badge" data-tone="accent">
            Intelligent routing
          </span>
          <h1 className="mt-4 text-[clamp(2rem,5vw,4.7rem)] font-semibold tracking-[-0.07em] text-[var(--text)]">
            What do you want to get done?
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-7 text-[var(--text-muted)] sm:text-[15px]">
            Describe the outcome. The orchestrator will interpret intent, recommend agents, estimate
            cost, and prepare an executable job before anything is charged.
          </p>
        </section>

        <section className="app-panel min-h-[560px] p-4 sm:p-5">
          <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] pb-4">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[var(--primary-soft)] text-[var(--primary)]">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <p className="font-semibold text-[var(--text)]">Orchestration agent</p>
                <p className="text-sm text-[var(--text-muted)]">{socketNotice}</p>
              </div>
            </div>
            {isThinking ? (
              <span className="inline-flex items-center gap-2 text-sm text-[var(--text-muted)]">
                <LoaderCircle className="h-4 w-4 animate-spin text-[var(--primary)]" />
                Thinking
              </span>
            ) : null}
          </div>

          <div className="mt-5 space-y-4 pb-32">
            {messages.length === 0 ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {promptSuggestions.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => processTask(prompt)}
                    className="rounded-2xl border border-[var(--border)] bg-[var(--surface-2)] p-4 text-left text-sm font-medium text-[var(--text)] transition hover:border-[var(--primary)] hover:bg-[var(--primary-soft)]"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            ) : null}

            {messages.map((message) => (
              <article
                key={message.id}
                className={cn("max-w-[88%] rounded-[1.4rem] border p-4", messageTone(message.kind))}
              >
                <div className="flex items-start gap-3">
                  <div className="grid h-9 w-9 shrink-0 place-items-center rounded-2xl bg-white/75 text-[var(--primary)]">
                    <MessageIcon kind={message.kind} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-semibold text-[var(--text)]">{message.title}</p>
                      <span className="text-xs text-[var(--text-muted)]">
                        {timeFormatter.format(new Date(message.timestamp))}
                      </span>
                    </div>
                    <p className="mt-2 text-sm leading-7 text-[var(--text-muted)]">
                      {message.body}
                    </p>
                  </div>
                </div>
              </article>
            ))}

            {bestSuggestion ? (
              <RecommendationCard
                suggestion={bestSuggestion}
                selected={selectedSuggestion?.agent.slug === bestSuggestion.agent.slug}
                disabled={isThinking || startingJob}
                alternativesOpen={alternativesOpen}
                alternatives={alternatives}
                onProceed={() => selectSuggestion(bestSuggestion)}
                onToggleAlternatives={() => setAlternativesOpen((open) => !open)}
                onSelectAlternative={selectSuggestion}
              />
            ) : null}

            {plan ? (
              <ExecutionPlanCard
                plan={plan}
                disabled={isThinking || startingJob}
                onConfirm={() => void confirmAndStartJob()}
                onEdit={() => {
                  setComposerValue(plan.inputSummary);
                  setPlan(null);
                  setSelectedSuggestion(null);
                  appendMessage({
                    kind: "message",
                    title: "Orchestrator",
                    body: "Edit the task in the composer and send it again. I will recompute the match and plan.",
                  });
                }}
              />
            ) : null}

            <div ref={bottomRef} />
          </div>

          <div className="sticky bottom-4 rounded-[1.6rem] border border-[var(--border)] bg-[var(--surface)] p-3 shadow-[var(--shadow-soft)]">
            <div className="flex items-end gap-2">
              <button
                type="button"
                className="grid h-11 w-11 shrink-0 place-items-center rounded-full border border-[var(--border)] text-[var(--text-muted)]"
                aria-label="Attach file placeholder"
              >
                <Paperclip className="h-4 w-4" />
              </button>
              <textarea
                value={composerValue}
                disabled={isThinking || startingJob}
                onChange={(event) => setComposerValue(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
                    event.preventDefault();
                    submitTask();
                  }
                }}
                rows={1}
                placeholder="What do you want to get done?"
                className="min-h-11 flex-1 resize-none rounded-[1.1rem] border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3 text-sm leading-6 text-[var(--text)] outline-none focus:border-[var(--primary)] disabled:opacity-60"
              />
              <button
                type="button"
                disabled={!composerValue.trim() || isThinking || startingJob}
                onClick={submitTask}
                className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] disabled:opacity-45"
              >
                {isThinking ? (
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                Send
              </button>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-[var(--text-muted)]">
              <span className="inline-flex items-center gap-1">
                <Clock3 className="h-3.5 w-3.5" />
                Ctrl+Enter to send
              </span>
              <span>/</span>
              <span className="inline-flex items-center gap-1">
                <RefreshCw className="h-3.5 w-3.5" />
                Reconnects automatically if the socket drops
              </span>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
