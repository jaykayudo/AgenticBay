"use client";

import {
  ArrowRight,
  CheckCircle2,
  ExternalLink,
  LoaderCircle,
  RefreshCcw,
  RotateCcw,
  SearchX,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { startTransition, useDeferredValue, useMemo, useState } from "react";

import { useApiQuery } from "@/hooks/useApi";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

type JobStatusTab = "all" | "active" | "completed" | "failed";
type BuyerJobHistoryStatus = "active" | "completed" | "failed";

type MarketplaceSessionRead = {
  sessionId: string;
  redirectPath: string;
};

type RehirePayload = {
  actionId: string;
  actionName: string;
  priceUsdc: number;
  estimatedDurationLabel: string;
  inputSummary: string;
  mode: "hire" | "demo";
};

type BuyerJobHistoryRecord = {
  sessionId: string;
  agentSlug: string;
  agentName: string;
  actionId: string;
  actionName: string;
  inputSummary: string;
  status: BuyerJobHistoryStatus;
  statusLabel: "Active" | "Completed" | "Failed";
  refundStatus: "not_applicable" | "refunded" | "pending_refund";
  amountChargedUsdc: number;
  amountLockedUsdc: number;
  durationLabel: string;
  createdAt: string;
  redirectPath: string;
  mode: "hire" | "demo";
  rehirePayload: RehirePayload;
};

type BuyerJobHistoryResponse = {
  generatedAt: string;
  jobs: BuyerJobHistoryRecord[];
};

const statusTabs: Array<{ value: JobStatusTab; label: string }> = [
  { value: "all", label: "All" },
  { value: "active", label: "Active" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
];

const EMPTY_JOBS: BuyerJobHistoryRecord[] = [];

const numberFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 0,
});

const preciseNumberFormatter = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const dateTimeFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

function formatUsdc(value: number) {
  return `${preciseNumberFormatter.format(value)} USDC`;
}

function statusTone(status: BuyerJobHistoryStatus) {
  if (status === "completed") {
    return "accent";
  }

  if (status === "failed") {
    return "danger";
  }

  return "default";
}

function StatusIcon({ status }: { status: BuyerJobHistoryStatus }) {
  if (status === "completed") {
    return <CheckCircle2 className="h-5 w-5 text-[var(--accent)]" />;
  }

  if (status === "failed") {
    return <XCircle className="h-5 w-5 text-[var(--danger)]" />;
  }

  return <LoaderCircle className="h-5 w-5 animate-spin text-[var(--primary)]" />;
}

function normalizeDateInput(value: string, endOfDay = false) {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  if (endOfDay) {
    date.setHours(23, 59, 59, 999);
  }

  return date;
}

export function JobHistoryPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<JobStatusTab>("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [agentFilter, setAgentFilter] = useState("all");
  const [minAmount, setMinAmount] = useState("");
  const [maxAmount, setMaxAmount] = useState("");
  const [pendingSessionId, setPendingSessionId] = useState<string | null>(null);
  const deferredMinAmount = useDeferredValue(minAmount);
  const deferredMaxAmount = useDeferredValue(maxAmount);

  const jobsQuery = useApiQuery<BuyerJobHistoryResponse>(
    ["buyer-job-history"],
    "/buyer/jobs/history",
    {
      refetchInterval: 20000,
    }
  );

  const jobs = jobsQuery.data?.jobs ?? EMPTY_JOBS;

  const agentOptions = useMemo(
    () =>
      Array.from(new Map(jobs.map((job) => [job.agentSlug, job.agentName])).entries()).sort(
        (left, right) => left[1].localeCompare(right[1])
      ),
    [jobs]
  );

  const filteredJobs = useMemo(() => {
    const from = normalizeDateInput(dateFrom);
    const to = normalizeDateInput(dateTo, true);
    const min = Number(deferredMinAmount);
    const max = Number(deferredMaxAmount);
    const hasMin = deferredMinAmount.trim() !== "" && Number.isFinite(min);
    const hasMax = deferredMaxAmount.trim() !== "" && Number.isFinite(max);

    return jobs.filter((job) => {
      const createdAt = new Date(job.createdAt);
      const matchesStatus = activeTab === "all" || job.status === activeTab;
      const matchesAgent = agentFilter === "all" || job.agentSlug === agentFilter;
      const matchesFrom = !from || createdAt >= from;
      const matchesTo = !to || createdAt <= to;
      const matchesMin = !hasMin || job.amountChargedUsdc >= min;
      const matchesMax = !hasMax || job.amountChargedUsdc <= max;

      return matchesStatus && matchesAgent && matchesFrom && matchesTo && matchesMin && matchesMax;
    });
  }, [activeTab, agentFilter, dateFrom, dateTo, deferredMaxAmount, deferredMinAmount, jobs]);

  const statusCounts = useMemo(
    () => ({
      all: jobs.length,
      active: jobs.filter((job) => job.status === "active").length,
      completed: jobs.filter((job) => job.status === "completed").length,
      failed: jobs.filter((job) => job.status === "failed").length,
    }),
    [jobs]
  );

  async function startMatchingJob(job: BuyerJobHistoryRecord) {
    setPendingSessionId(job.sessionId);

    try {
      const nextSession = await apiFetch<MarketplaceSessionRead>(
        `/marketplace/agents/${encodeURIComponent(job.agentSlug)}/sessions`,
        {
          method: "post",
          data: {
            ...job.rehirePayload,
            inputSummary: `${job.agentName} will execute ${job.actionName}. Recreated from job ${job.sessionId}.`,
            mode: "hire",
          },
        }
      );

      startTransition(() => {
        router.push(nextSession.redirectPath);
      });
    } finally {
      setPendingSessionId(null);
    }
  }

  function clearFilters() {
    setDateFrom("");
    setDateTo("");
    setAgentFilter("all");
    setMinAmount("");
    setMaxAmount("");
  }

  return (
    <div className="space-y-4 xl:space-y-6">
      <section className="app-panel p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <span className="app-status-badge" data-tone="accent">
              Job history
            </span>
            <h1 className="mt-4 text-3xl font-semibold text-[var(--text)] sm:text-4xl">
              Review every agent job
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--text-muted)]">
              Browse active and past work, stack filters, open live sessions, and quickly recreate
              successful or failed jobs with the same agent.
            </p>
          </div>

          <div className="app-subtle p-4">
            <p className="text-sm text-[var(--text-muted)]">Matching jobs</p>
            <p className="mt-2 text-3xl font-semibold text-[var(--text)] tabular-nums">
              {numberFormatter.format(filteredJobs.length)}
            </p>
          </div>
        </div>
      </section>

      <section className="app-panel p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="inline-flex overflow-x-auto rounded-full border border-[var(--border)] bg-[var(--surface)] p-1 shadow-[var(--shadow-soft)]">
            {statusTabs.map((tab) => (
              <button
                key={tab.value}
                type="button"
                aria-pressed={activeTab === tab.value}
                onClick={() => setActiveTab(tab.value)}
                className={cn(
                  "inline-flex h-10 rounded-full px-4 text-sm font-medium whitespace-nowrap transition",
                  activeTab === tab.value
                    ? "bg-[var(--surface-2)] text-[var(--text)]"
                    : "text-[var(--text-muted)] hover:text-[var(--text)]"
                )}
              >
                <span className="self-center">
                  {tab.label} ({statusCounts[tab.value]})
                </span>
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={clearFilters}
            className="inline-flex h-10 items-center justify-center rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text-muted)] transition hover:text-[var(--text)]"
          >
            Clear filters
          </button>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <label className="grid gap-2 text-sm">
            <span className="font-medium text-[var(--text)]">From</span>
            <input
              type="date"
              value={dateFrom}
              onChange={(event) => setDateFrom(event.target.value)}
              className="h-11 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-[var(--text)] outline-none focus:border-[var(--primary)]"
            />
          </label>

          <label className="grid gap-2 text-sm">
            <span className="font-medium text-[var(--text)]">To</span>
            <input
              type="date"
              value={dateTo}
              onChange={(event) => setDateTo(event.target.value)}
              className="h-11 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-[var(--text)] outline-none focus:border-[var(--primary)]"
            />
          </label>

          <label className="grid gap-2 text-sm">
            <span className="font-medium text-[var(--text)]">Agent</span>
            <select
              value={agentFilter}
              onChange={(event) => setAgentFilter(event.target.value)}
              className="h-11 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-[var(--text)] outline-none focus:border-[var(--primary)]"
            >
              <option value="all">All agents</option>
              {agentOptions.map(([slug, name]) => (
                <option key={slug} value={slug}>
                  {name}
                </option>
              ))}
            </select>
          </label>

          <label className="grid gap-2 text-sm">
            <span className="font-medium text-[var(--text)]">Min amount</span>
            <input
              value={minAmount}
              onChange={(event) => setMinAmount(event.target.value)}
              inputMode="decimal"
              className="h-11 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-[var(--text)] outline-none focus:border-[var(--primary)]"
              placeholder="0"
            />
          </label>

          <label className="grid gap-2 text-sm">
            <span className="font-medium text-[var(--text)]">Max amount</span>
            <input
              value={maxAmount}
              onChange={(event) => setMaxAmount(event.target.value)}
              inputMode="decimal"
              className="h-11 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-[var(--text)] outline-none focus:border-[var(--primary)]"
              placeholder="5000"
            />
          </label>
        </div>
      </section>

      <section className="app-panel p-5 sm:p-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-[var(--text)]">Jobs</h2>
            <p className="mt-1 text-sm text-[var(--text-muted)]">
              {filteredJobs.length} of {jobs.length} jobs shown
            </p>
          </div>
        </div>

        <div className="mt-5 space-y-3">
          {jobsQuery.isLoading ? (
            <div className="flex items-center gap-3 rounded-2xl border border-[var(--border)] bg-[var(--surface-2)] p-5 text-sm text-[var(--text-muted)]">
              <LoaderCircle className="h-4 w-4 animate-spin text-[var(--primary)]" />
              Loading job history
            </div>
          ) : null}

          {!jobsQuery.isLoading && filteredJobs.length === 0 ? (
            <div className="app-subtle p-8 text-center">
              <div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-[var(--primary-soft)] text-[var(--primary)]">
                <SearchX className="h-5 w-5" />
              </div>
              <h3 className="mt-4 text-lg font-semibold text-[var(--text)]">No jobs found</h3>
              <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-[var(--text-muted)]">
                No {activeTab === "all" ? "" : activeTab} jobs match the current filter stack.
              </p>
            </div>
          ) : null}

          {filteredJobs.map((job) => {
            const actionLabel =
              job.status === "failed" ? "Try Again" : job.status === "completed" ? "Rehire" : null;
            const pending = pendingSessionId === job.sessionId;

            return (
              <article
                key={job.sessionId}
                className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 transition hover:bg-[var(--surface-2)]"
              >
                <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-center">
                  <div className="flex min-w-0 gap-3">
                    <div className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-[var(--surface-2)]">
                      <StatusIcon status={job.status} />
                    </div>

                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="app-status-badge" data-tone={statusTone(job.status)}>
                          {job.statusLabel}
                        </span>
                        {job.refundStatus !== "not_applicable" ? (
                          <span className="app-status-badge" data-tone="muted">
                            {job.refundStatus.replace("_", " ")}
                          </span>
                        ) : null}
                        <span className="text-xs font-medium tracking-[0.14em] text-[var(--text-muted)] uppercase">
                          {job.sessionId.slice(0, 18)}
                        </span>
                      </div>

                      <h3 className="mt-3 font-semibold text-[var(--text)]">
                        {job.agentName} / {job.actionName}
                      </h3>
                      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-[var(--text-muted)]">
                        <span>{formatUsdc(job.amountChargedUsdc)}</span>
                        <span>{job.durationLabel}</span>
                        <span>{dateTimeFormatter.format(new Date(job.createdAt))}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2 xl:justify-end">
                    <Link
                      href={job.redirectPath}
                      className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text)] transition hover:bg-[var(--surface)]"
                    >
                      View
                      <ExternalLink className="h-4 w-4" />
                    </Link>

                    {actionLabel ? (
                      <button
                        type="button"
                        disabled={pending}
                        onClick={() => void startMatchingJob(job)}
                        className="inline-flex h-10 items-center gap-2 rounded-full bg-[var(--primary)] px-4 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] transition hover:opacity-95 disabled:opacity-55"
                      >
                        {pending ? (
                          <LoaderCircle className="h-4 w-4 animate-spin" />
                        ) : job.status === "failed" ? (
                          <RotateCcw className="h-4 w-4" />
                        ) : (
                          <RefreshCcw className="h-4 w-4" />
                        )}
                        {pending ? "Creating" : actionLabel}
                      </button>
                    ) : (
                      <Link
                        href={job.redirectPath}
                        className="inline-flex h-10 items-center gap-2 rounded-full bg-[var(--primary)] px-4 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] transition hover:opacity-95"
                      >
                        Continue
                        <ArrowRight className="h-4 w-4" />
                      </Link>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}
