"use client";

import {
  ArrowLeft,
  ArrowUpRight,
  CalendarRange,
  CircleAlert,
  LoaderCircle,
  MessageSquareText,
  ShieldCheck,
  Star,
  TimerReset,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { startTransition, useDeferredValue, useState } from "react";
import type { ComponentType } from "react";

import { useApiQuery } from "@/hooks/useApi";
import { cn } from "@/lib/utils";

type AnalyticsRange = "7d" | "30d" | "90d" | "all";

type AgentAnalyticsResponse = {
  agentId: string;
  agentName: string;
  ownerName: string;
  range: AnalyticsRange;
  generatedAt: string;
  summary: {
    totalJobs: number;
    totalEarned: number;
    successRate: number;
    avgJobValue: number;
  };
  revenueSeries: Array<{
    label: string;
    amount: number;
    jobs: number;
  }>;
  actionBreakdown: Array<{
    action: string;
    count: number;
    percentage: number;
    earned: number;
  }>;
  reviews: Array<{
    id: string;
    reviewerName: string;
    company: string;
    rating: number;
    comment: string;
    jobTitle: string;
    createdAt: string;
  }>;
  responseTimeDistribution: Array<{
    label: string;
    count: number;
    percentage: number;
    averageMinutes: number;
  }>;
};

const rangeTabs: Array<{ value: AnalyticsRange; label: string }> = [
  { value: "7d", label: "7D" },
  { value: "30d", label: "30D" },
  { value: "90d", label: "90D" },
  { value: "all", label: "All" },
];

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const currencyPreciseFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
});

function StatCard({
  icon: Icon,
  label,
  value,
  hint,
  delay,
}: {
  icon: ComponentType<{ className?: string }>;
  label: string;
  value: string;
  hint: string;
  delay: number;
}) {
  return (
    <section
      className="app-panel animate-in fade-in slide-in-from-bottom-4 p-5 duration-500 sm:p-6"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm text-[var(--text-muted)]">{label}</p>
          <p className="mt-3 text-[1.9rem] font-semibold tracking-[-0.04em] text-[var(--text)] tabular-nums">
            {value}
          </p>
        </div>
        <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[var(--primary-soft)] text-[var(--primary)]">
          <Icon className="h-5 w-5" />
        </div>
      </div>
      <p className="mt-4 text-sm leading-6 text-[var(--text-muted)]">{hint}</p>
    </section>
  );
}

function RevenueChart({ series }: { series: AgentAnalyticsResponse["revenueSeries"] }) {
  const maxAmount = Math.max(...series.map((item) => item.amount), 1);

  return (
    <div className="mt-6 overflow-x-auto">
      <div className="min-w-[560px] rounded-[1.5rem] border border-[var(--border)] bg-[var(--surface-2)] p-4 sm:p-5">
        <div className="flex h-[280px] items-end gap-3">
          {series.map((item, index) => {
            const height = Math.max((item.amount / maxAmount) * 100, item.amount > 0 ? 12 : 4);

            return (
              <div
                key={`${item.label}-${index}`}
                className="flex min-w-0 flex-1 flex-col justify-end"
              >
                <div className="mb-3 text-center text-xs font-medium text-[var(--text-muted)] tabular-nums">
                  {item.amount > 0 ? currencyFormatter.format(item.amount) : "--"}
                </div>
                <div className="flex h-[210px] items-end justify-center rounded-[1.2rem] bg-[color-mix(in_srgb,var(--surface)_82%,transparent)] px-2 pb-2">
                  <div
                    className="w-full rounded-[0.95rem] bg-[var(--primary)] transition-[height] duration-500 ease-out"
                    style={{ height: `${height}%` }}
                    title={`${item.label}: ${currencyFormatter.format(item.amount)} across ${item.jobs} jobs`}
                  />
                </div>
                <div className="mt-3 text-center text-xs text-[var(--text-muted)]">{item.label}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function HorizontalBreakdown({
  items,
  valueFormatter,
}: {
  items: Array<{ label: string; percentage: number; value: string; hint: string }>;
  valueFormatter?: (value: number) => string;
}) {
  return (
    <div className="mt-6 space-y-4">
      {items.map((item) => (
        <div key={item.label} className="space-y-2.5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-[var(--text)]">{item.label}</p>
              <p className="mt-1 text-sm text-[var(--text-muted)]">{item.hint}</p>
            </div>
            <div className="text-right">
              <p className="text-sm font-medium text-[var(--text)] tabular-nums">
                {valueFormatter ? valueFormatter(item.percentage) : `${item.percentage.toFixed(1)}%`}
              </p>
              <p className="mt-1 text-sm text-[var(--text-muted)]">{item.value}</p>
            </div>
          </div>

          <div className="h-2.5 overflow-hidden rounded-full bg-[var(--surface-3)]">
            <div
              className="h-full rounded-full bg-[var(--primary)] transition-[width] duration-500 ease-out"
              style={{ width: `${Math.max(item.percentage, item.percentage > 0 ? 6 : 0)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function StarRating({ rating }: { rating: number }) {
  return (
    <div className="flex items-center gap-1">
      {Array.from({ length: 5 }, (_, index) => (
        <Star
          key={index}
          className={cn(
            "h-4 w-4",
            index < rating
              ? "fill-[var(--primary)] text-[var(--primary)]"
              : "fill-transparent text-[var(--border)]"
          )}
        />
      ))}
    </div>
  );
}

export default function AgentAnalyticsPage() {
  const params = useParams<{ agentId: string }>();
  const agentId = decodeURIComponent(params.agentId);
  const [selectedRange, setSelectedRange] = useState<AnalyticsRange>("30d");
  const deferredRange = useDeferredValue(selectedRange);

  const analyticsQuery = useApiQuery<AgentAnalyticsResponse>(
    ["agent-analytics", agentId, deferredRange],
    `/agents/${encodeURIComponent(agentId)}/analytics?range=${deferredRange}`,
    {
      enabled: Boolean(agentId),
    }
  );

  const analytics = analyticsQuery.data;

  const actionItems =
    analytics?.actionBreakdown.map((item) => ({
      label: item.action,
      percentage: item.percentage,
      value: currencyFormatter.format(item.earned),
      hint: `${item.count} jobs`,
    })) ?? [];

  const responseItems =
    analytics?.responseTimeDistribution.map((item) => ({
      label: item.label,
      percentage: item.percentage,
      value: `${item.count} jobs`,
      hint: item.averageMinutes > 0 ? `${item.averageMinutes} min average` : "No jobs in this band",
    })) ?? [];

  return (
    <div className="space-y-4 xl:space-y-6">
      <section className="app-panel p-5 sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <Link
              href="/dashboard#agents"
              className="inline-flex items-center gap-2 text-sm font-medium text-[var(--text-muted)] transition hover:text-[var(--text)]"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to agent owner dashboard
            </Link>

            <h1 className="mt-4 text-[clamp(1.8rem,3vw,2.5rem)] font-semibold tracking-[-0.04em] text-[var(--text)]">
              {analytics?.agentName ?? "Agent analytics"}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--text-muted)] sm:text-[15px]">
              Detailed owner-side performance for jobs completed, revenue generated, response-time
              quality, and what clients are saying most recently.
            </p>

            <div className="mt-5 flex flex-wrap gap-3">
              <span className="app-status-badge" data-tone="default">
                Owner: {analytics?.ownerName ?? "Loading"}
              </span>
              <span className="app-status-badge" data-tone="muted">
                Updated{" "}
                {analytics?.generatedAt
                  ? dateFormatter.format(new Date(analytics.generatedAt))
                  : "just now"}
              </span>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 rounded-full border border-[var(--border)] bg-[var(--surface-2)] p-1 shadow-[var(--shadow-soft)]">
            {rangeTabs.map((tab) => (
              <button
                key={tab.value}
                type="button"
                onClick={() =>
                  startTransition(() => {
                    setSelectedRange(tab.value);
                  })
                }
                className={cn(
                  "rounded-full px-4 py-2 text-sm font-medium transition",
                  selectedRange === tab.value
                    ? "bg-[var(--surface)] text-[var(--text)] shadow-[var(--shadow-soft)]"
                    : "text-[var(--text-muted)] hover:text-[var(--text)]"
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {analyticsQuery.isLoading ? (
        <section className="grid gap-4 xl:grid-cols-4 xl:gap-6">
          {Array.from({ length: 4 }, (_, index) => (
            <div key={index} className="app-panel h-[164px] animate-pulse p-5 sm:p-6" />
          ))}
        </section>
      ) : null}

      {analyticsQuery.isError ? (
        <section className="app-panel p-5 sm:p-6">
          <div className="flex items-start gap-3 rounded-[1.2rem] border border-[var(--danger-soft)] bg-[var(--danger-soft)] p-4 text-[var(--danger)]">
            <CircleAlert className="mt-0.5 h-5 w-5 shrink-0" />
            <div>
              <p className="font-medium">Analytics could not be loaded right now.</p>
              <p className="mt-1 text-sm leading-6">
                Try again in a moment or return to the dashboard while the service reconnects.
              </p>
            </div>
          </div>
        </section>
      ) : null}

      {analytics ? (
        <>
          <section key={`${analytics.agentId}-${deferredRange}`} className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4 xl:gap-6">
            <StatCard
              icon={CalendarRange}
              label="Total Jobs"
              value={analytics.summary.totalJobs.toString()}
              hint="Completed inside the selected window."
              delay={0}
            />
            <StatCard
              icon={Wallet}
              label="Total Earned"
              value={currencyFormatter.format(analytics.summary.totalEarned)}
              hint="Recognized revenue for delivered work."
              delay={70}
            />
            <StatCard
              icon={ShieldCheck}
              label="Success Rate"
              value={`${analytics.summary.successRate.toFixed(1)}%`}
              hint="Jobs completed without dispute or failed delivery."
              delay={140}
            />
            <StatCard
              icon={ArrowUpRight}
              label="Avg Job Value"
              value={currencyPreciseFormatter.format(analytics.summary.avgJobValue)}
              hint="Average revenue captured per completed job."
              delay={210}
            />
          </section>

          <section className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,380px)] xl:gap-6">
            <section className="app-panel p-5 sm:p-6">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">
                    Revenue
                  </p>
                  <h2 className="mt-2 text-[1.15rem] font-semibold tracking-[-0.02em] text-[var(--text)]">
                    Revenue trend
                  </h2>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--text-muted)]">
                    Revenue bars are grouped by the active date range and fetched fresh from the
                    analytics API each time you switch tabs.
                  </p>
                </div>
                {analyticsQuery.isFetching ? (
                  <span className="app-status-badge" data-tone="muted">
                    <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
                    Updating
                  </span>
                ) : null}
              </div>

              <RevenueChart series={analytics.revenueSeries} />
            </section>

            <section className="app-panel p-5 sm:p-6">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">
                Actions
              </p>
              <h2 className="mt-2 text-[1.15rem] font-semibold tracking-[-0.02em] text-[var(--text)]">
                Popular actions
              </h2>
              <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                Share of completed work by action type, calculated from the current range.
              </p>

              <HorizontalBreakdown items={actionItems} />
            </section>
          </section>

          <section className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,420px)] xl:gap-6">
            <section className="app-panel p-5 sm:p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">
                    Reviews
                  </p>
                  <h2 className="mt-2 text-[1.15rem] font-semibold tracking-[-0.02em] text-[var(--text)]">
                    Latest client feedback
                  </h2>
                  <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                    The five most recent reviews inside the selected time window.
                  </p>
                </div>
                <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[var(--primary-soft)] text-[var(--primary)]">
                  <MessageSquareText className="h-5 w-5" />
                </div>
              </div>

              <div className="mt-6 space-y-3">
                {analytics.reviews.map((review) => (
                  <article key={review.id} className="app-subtle p-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <p className="font-medium text-[var(--text)]">{review.reviewerName}</p>
                        <p className="mt-1 text-sm text-[var(--text-muted)]">
                          {review.company} / {review.jobTitle}
                        </p>
                      </div>
                      <div className="space-y-2 sm:text-right">
                        <StarRating rating={review.rating} />
                        <p className="text-sm text-[var(--text-muted)]">
                          {dateFormatter.format(new Date(review.createdAt))}
                        </p>
                      </div>
                    </div>
                    <p className="mt-3 text-sm leading-7 text-[var(--text-muted)]">
                      {review.comment}
                    </p>
                  </article>
                ))}
              </div>
            </section>

            <section className="app-panel p-5 sm:p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">
                    Response time
                  </p>
                  <h2 className="mt-2 text-[1.15rem] font-semibold tracking-[-0.02em] text-[var(--text)]">
                    Response time distribution
                  </h2>
                  <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                    Calculated from actual response-time minutes on delivered jobs.
                  </p>
                </div>
                <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[var(--primary-soft)] text-[var(--primary)]">
                  <TimerReset className="h-5 w-5" />
                </div>
              </div>

              <HorizontalBreakdown items={responseItems} />
            </section>
          </section>
        </>
      ) : null}

      <div className="flex justify-start">
        <Link
          href="/dashboard#agents"
          className="inline-flex h-11 items-center rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 text-sm font-medium text-[var(--text)] shadow-[var(--shadow-soft)] transition hover:bg-[var(--surface-2)]"
        >
          Return to dashboard
        </Link>
      </div>
    </div>
  );
}
