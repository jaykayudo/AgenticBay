"use client";

import {
  ArrowLeft,
  ArrowRight,
  CircleAlert,
  LoaderCircle,
  ShieldCheck,
  Sparkles,
  Star,
  TimerReset,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { startTransition, useState } from "react";

import { useApiMutation, useApiQuery } from "@/hooks/useApi";
import {
  formatUsdc,
  getMarketplaceAgentDetail,
  type MarketplaceAgentAction,
} from "@/lib/marketplace-data";
import { cn } from "@/lib/utils";

type DetailTab = "about" | "actions" | "reviews" | "stats";

type MarketplaceAgentInsightsResponse = {
  agentSlug: string;
  agentName: string;
  generatedAt: string;
  stats: {
    successRate: number;
    totalJobs: number;
    totalEarned: number;
    avgJobValue: number;
    avgDeliveryMinutes: number;
    avgDeliveryLabel: string;
    repeatBuyerRate: number;
    onTimeRate: number;
    payoutCompletionRate: number;
    metrics: Array<{
      label: string;
      value: string;
      detail: string;
    }>;
    responseTimeDistribution: Array<{
      label: string;
      count: number;
      percentage: number;
      averageMinutes: number;
    }>;
  };
  reviews: Array<{
    id: string;
    reviewerName: string;
    company: string;
    rating: number;
    comment: string;
    jobTitle: string;
    createdAt: string;
  }>;
};

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

type CreateSessionPayload = {
  actionId: string;
  actionName: string;
  priceUsdc: number;
  estimatedDurationLabel: string;
  inputSummary: string;
  mode: "hire" | "demo";
};

const tabOptions: Array<{ value: DetailTab; label: string }> = [
  { value: "about", label: "About" },
  { value: "actions", label: "Actions" },
  { value: "reviews", label: "Reviews" },
  { value: "stats", label: "Stats" },
];

const REVIEWS_PER_PAGE = 4;

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
});

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

function AgentAvatar({
  label,
  background,
  foreground,
}: {
  label: string;
  background: string;
  foreground: string;
}) {
  return (
    <div
      className="grid h-16 w-16 shrink-0 place-items-center rounded-[1.4rem] text-base font-semibold shadow-[var(--shadow-soft)]"
      style={{ backgroundColor: background, color: foreground }}
    >
      {label}
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
              ? "fill-amber-400 text-amber-400"
              : "fill-transparent text-[var(--border)]"
          )}
        />
      ))}
    </div>
  );
}

function ActionCard({
  action,
  selected,
  onSelect,
}: {
  action: MarketplaceAgentAction;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "app-subtle w-full rounded-[1.35rem] border p-4 text-left transition sm:p-5",
        selected
          ? "border-[var(--primary)] bg-[color-mix(in_srgb,var(--primary-soft)_70%,var(--surface)_30%)]"
          : "border-[var(--border)] hover:border-[var(--primary)]"
      )}
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-semibold tracking-[-0.02em] text-[var(--text)]">
              {action.name}
            </h3>
            {action.demoAvailable ? (
              <span className="app-status-badge" data-tone="accent">
                Demo available
              </span>
            ) : null}
          </div>
          <p className="mt-3 text-sm leading-7 text-[var(--text-muted)]">{action.description}</p>
        </div>

        <div className="grid shrink-0 gap-2 sm:min-w-[150px]">
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3">
            <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
              Price
            </p>
            <p className="mt-2 text-lg font-semibold text-[var(--text)]">
              {formatUsdc(action.priceUsdc)}
            </p>
          </div>
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3">
            <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
              Duration
            </p>
            <p className="mt-2 text-sm font-medium text-[var(--text)]">
              {action.estimatedDurationLabel}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-[var(--primary)]">
        {selected ? "Selected for hire panel" : "Select this action"}
        <ArrowRight className="h-4 w-4" />
      </div>
    </button>
  );
}

export function MarketplaceAgentDetail({ agentSlug }: { agentSlug: string }) {
  const router = useRouter();
  const agent = getMarketplaceAgentDetail(agentSlug);
  const [activeTab, setActiveTab] = useState<DetailTab>("about");
  const [selectedActionId, setSelectedActionId] = useState(() => agent?.actions[0]?.id ?? "");
  const [reviewPage, setReviewPage] = useState(1);

  const insightsQuery = useApiQuery<MarketplaceAgentInsightsResponse>(
    ["marketplace-agent-insights", agentSlug],
    `/marketplace/agents/${encodeURIComponent(agentSlug)}/insights`,
    {
      enabled: Boolean(agent),
    }
  );

  const createSessionMutation = useApiMutation<MarketplaceSessionRead, CreateSessionPayload>(
    `/marketplace/agents/${encodeURIComponent(agentSlug)}/sessions`
  );

  if (!agent) {
    return null;
  }

  const selectedAction = agent.actions.find((action) => action.id === selectedActionId) ?? null;
  const demoAction = agent.actions.find((action) => action.demoAvailable) ?? null;
  const stats = insightsQuery.data?.stats;
  const reviews = insightsQuery.data?.reviews ?? [];
  const totalReviewPages = Math.max(1, Math.ceil(reviews.length / REVIEWS_PER_PAGE));
  const currentReviewPage = Math.min(reviewPage, totalReviewPages);
  const visibleReviews = reviews.slice(
    (currentReviewPage - 1) * REVIEWS_PER_PAGE,
    currentReviewPage * REVIEWS_PER_PAGE
  );

  function createSession(action: MarketplaceAgentAction, mode: "hire" | "demo") {
    if (!agent) {
      return;
    }

    createSessionMutation.mutate(
      {
        actionId: action.id,
        actionName: action.name,
        priceUsdc: mode === "demo" ? 0 : action.priceUsdc,
        estimatedDurationLabel: action.estimatedDurationLabel,
        inputSummary: `${agent.name} will execute ${action.name}. ${action.description}`,
        mode,
      },
      {
        onSuccess: (session) => {
          startTransition(() => {
            router.push(session.redirectPath);
          });
        },
      }
    );
  }

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

        <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="space-y-6">
            <section className="app-panel p-5 sm:p-6">
              <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
                <div className="flex min-w-0 gap-4">
                  <AgentAvatar
                    label={agent.avatar.label}
                    background={agent.avatar.bg}
                    foreground={agent.avatar.fg}
                  />

                  <div className="min-w-0">
                    <span className="app-status-badge" data-tone="accent">
                      {agent.speedLabel}
                    </span>
                    <h1 className="mt-4 text-[clamp(2rem,4vw,3rem)] font-semibold tracking-[-0.05em] text-[var(--text)]">
                      {agent.name}
                    </h1>
                    <p className="mt-3 max-w-3xl text-base leading-7 text-[var(--text-muted)]">
                      {agent.headline}
                    </p>

                    <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-[var(--text-muted)]">
                      <span className="inline-flex items-center gap-1.5">
                        <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
                        {agent.rating.toFixed(1)}
                      </span>
                      <span>{agent.reviewCount} marketplace reviews</span>
                      <span>Starting at {formatUsdc(agent.startingPriceUsdc)}</span>
                    </div>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-3 lg:min-w-[320px] lg:grid-cols-1">
                  <div className="app-subtle rounded-2xl p-4">
                    <p className="text-lg font-semibold text-[var(--text)]">
                      {stats ? `${stats.successRate.toFixed(1)}%` : "--"}
                    </p>
                    <p className="mt-1 text-xs text-[var(--text-muted)]">Success rate</p>
                  </div>
                  <div className="app-subtle rounded-2xl p-4">
                    <p className="text-lg font-semibold text-[var(--text)]">
                      {stats ? stats.avgDeliveryLabel : "--"}
                    </p>
                    <p className="mt-1 text-xs text-[var(--text-muted)]">Average delivery</p>
                  </div>
                  <div className="app-subtle rounded-2xl p-4">
                    <p className="text-lg font-semibold text-[var(--text)]">
                      {stats ? stats.totalJobs : "--"}
                    </p>
                    <p className="mt-1 text-xs text-[var(--text-muted)]">Total jobs</p>
                  </div>
                </div>
              </div>

              <div className="mt-6 flex flex-wrap gap-2">
                {agent.tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1 text-xs font-medium text-[var(--text-muted)]"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </section>

            <section className="app-panel p-2 sm:p-3">
              <div className="flex flex-wrap gap-2">
                {tabOptions.map((tab) => (
                  <button
                    key={tab.value}
                    type="button"
                    onClick={() => setActiveTab(tab.value)}
                    className={cn(
                      "inline-flex h-10 items-center justify-center rounded-full px-4 text-sm font-medium transition",
                      activeTab === tab.value
                        ? "bg-[var(--primary)] text-[var(--primary-foreground)]"
                        : "text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
                    )}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </section>

            <section className="app-panel p-5 sm:p-6">
              {activeTab === "about" ? (
                <div className="space-y-5">
                  <div className="grid gap-4 sm:grid-cols-3">
                    <div className="app-subtle rounded-2xl p-4">
                      <p className="text-sm font-semibold text-[var(--text)]">
                        Economy-ready delivery
                      </p>
                      <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                        Built for teams and agents that need scoped work, escrow-backed execution,
                        and clean handoff quality.
                      </p>
                    </div>
                    <div className="app-subtle rounded-2xl p-4">
                      <p className="text-sm font-semibold text-[var(--text)]">
                        Circle settlement flow
                      </p>
                      <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                        Funding and delivery milestones fit the platform&apos;s Circle-powered USDC
                        payment flow.
                      </p>
                    </div>
                    <div className="app-subtle rounded-2xl p-4">
                      <p className="text-sm font-semibold text-[var(--text)]">
                        Agent handoff friendly
                      </p>
                      <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                        Outputs are framed for downstream automation, review, or immediate reuse by
                        another specialist.
                      </p>
                    </div>
                  </div>

                  {agent.fullDescription.map((paragraph) => (
                    <p
                      key={paragraph}
                      className="text-sm leading-8 text-[var(--text-muted)] sm:text-[15px]"
                    >
                      {paragraph}
                    </p>
                  ))}
                </div>
              ) : null}

              {activeTab === "actions" ? (
                <div className="space-y-4">
                  <div>
                    <h2 className="text-lg font-semibold tracking-[-0.03em] text-[var(--text)]">
                      Available actions
                    </h2>
                    <p className="mt-2 text-sm leading-7 text-[var(--text-muted)]">
                      Pick the delivery shape that matches the scope you want to hire for. Selecting
                      an action here also updates the sticky hire panel.
                    </p>
                  </div>

                  {agent.actions.map((action) => (
                    <ActionCard
                      key={action.id}
                      action={action}
                      selected={selectedActionId === action.id}
                      onSelect={() => setSelectedActionId(action.id)}
                    />
                  ))}
                </div>
              ) : null}

              {activeTab === "reviews" ? (
                <div className="space-y-5">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                    <div>
                      <h2 className="text-lg font-semibold tracking-[-0.03em] text-[var(--text)]">
                        Buyer reviews
                      </h2>
                      <p className="mt-2 text-sm leading-7 text-[var(--text-muted)]">
                        Recent marketplace feedback from buyers and coordinating agents.
                      </p>
                    </div>
                    <p className="text-sm text-[var(--text-muted)]">
                      {reviews.length > 0
                        ? `${(currentReviewPage - 1) * REVIEWS_PER_PAGE + 1}-${Math.min(
                            currentReviewPage * REVIEWS_PER_PAGE,
                            reviews.length
                          )} of ${reviews.length}`
                        : "No reviews available"}
                    </p>
                  </div>

                  {insightsQuery.isLoading ? (
                    <div className="space-y-4">
                      {Array.from({ length: 3 }, (_, index) => (
                        <div key={index} className="app-subtle h-36 animate-pulse rounded-2xl" />
                      ))}
                    </div>
                  ) : null}

                  {insightsQuery.isError ? (
                    <div className="rounded-[1.4rem] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                      <div className="flex items-start gap-2">
                        <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
                        <p>Reviews could not be loaded right now. Please try again shortly.</p>
                      </div>
                    </div>
                  ) : null}

                  {!insightsQuery.isLoading && !insightsQuery.isError && reviews.length === 0 ? (
                    <section className="app-subtle rounded-[1.5rem] p-6 text-sm leading-7 text-[var(--text-muted)]">
                      No buyer reviews are available for this agent yet.
                    </section>
                  ) : null}

                  {!insightsQuery.isLoading &&
                  !insightsQuery.isError &&
                  visibleReviews.length > 0 ? (
                    <div className="space-y-4">
                      {visibleReviews.map((review) => (
                        <article key={review.id} className="app-subtle rounded-[1.4rem] p-4 sm:p-5">
                          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                            <div>
                              <p className="font-semibold text-[var(--text)]">
                                {review.reviewerName}
                              </p>
                              <p className="mt-1 text-sm text-[var(--text-muted)]">
                                {review.company} / {review.jobTitle}
                              </p>
                            </div>
                            <div className="flex items-center gap-3">
                              <StarRating rating={review.rating} />
                              <span className="text-sm text-[var(--text-muted)]">
                                {dateFormatter.format(new Date(review.createdAt))}
                              </span>
                            </div>
                          </div>
                          <p className="mt-4 text-sm leading-7 text-[var(--text-muted)]">
                            {review.comment}
                          </p>
                        </article>
                      ))}

                      {totalReviewPages > 1 ? (
                        <div className="flex items-center justify-between gap-3 border-t border-[var(--border)] pt-4">
                          <button
                            type="button"
                            onClick={() => setReviewPage((page) => Math.max(1, page - 1))}
                            disabled={currentReviewPage === 1}
                            className="inline-flex h-10 items-center justify-center rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text-muted)] transition hover:border-[var(--primary)] hover:text-[var(--primary)] disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Previous
                          </button>
                          <p className="text-sm text-[var(--text-muted)]">
                            Page {currentReviewPage} of {totalReviewPages}
                          </p>
                          <button
                            type="button"
                            onClick={() =>
                              setReviewPage((page) => Math.min(totalReviewPages, page + 1))
                            }
                            disabled={currentReviewPage === totalReviewPages}
                            className="inline-flex h-10 items-center justify-center rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text-muted)] transition hover:border-[var(--primary)] hover:text-[var(--primary)] disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Next
                          </button>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ) : null}

              {activeTab === "stats" ? (
                <div className="space-y-5">
                  <div>
                    <h2 className="text-lg font-semibold tracking-[-0.03em] text-[var(--text)]">
                      Performance metrics
                    </h2>
                    <p className="mt-2 text-sm leading-7 text-[var(--text-muted)]">
                      Live marketplace stats for delivery reliability, response mix, and settled
                      contract performance.
                    </p>
                  </div>

                  {insightsQuery.isLoading ? (
                    <div className="grid gap-4 sm:grid-cols-2">
                      {Array.from({ length: 4 }, (_, index) => (
                        <div key={index} className="app-subtle h-28 animate-pulse rounded-2xl" />
                      ))}
                    </div>
                  ) : null}

                  {insightsQuery.isError ? (
                    <div className="rounded-[1.4rem] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                      <div className="flex items-start gap-2">
                        <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
                        <p>Live stats could not be loaded right now. Please refresh to retry.</p>
                      </div>
                    </div>
                  ) : null}

                  {stats ? (
                    <div className="space-y-5">
                      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                        <div className="app-subtle rounded-2xl p-4">
                          <p className="text-2xl font-semibold tracking-[-0.03em] text-[var(--text)]">
                            {stats.successRate.toFixed(1)}%
                          </p>
                          <p className="mt-1 text-sm text-[var(--text-muted)]">Success rate</p>
                        </div>
                        <div className="app-subtle rounded-2xl p-4">
                          <p className="text-2xl font-semibold tracking-[-0.03em] text-[var(--text)]">
                            {stats.totalJobs}
                          </p>
                          <p className="mt-1 text-sm text-[var(--text-muted)]">Jobs completed</p>
                        </div>
                        <div className="app-subtle rounded-2xl p-4">
                          <p className="text-2xl font-semibold tracking-[-0.03em] text-[var(--text)]">
                            {stats.avgDeliveryLabel}
                          </p>
                          <p className="mt-1 text-sm text-[var(--text-muted)]">Average delivery</p>
                        </div>
                        <div className="app-subtle rounded-2xl p-4">
                          <p className="text-2xl font-semibold tracking-[-0.03em] text-[var(--text)]">
                            {currencyFormatter.format(stats.totalEarned)}
                          </p>
                          <p className="mt-1 text-sm text-[var(--text-muted)]">Settled volume</p>
                        </div>
                      </div>

                      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                        <section className="app-subtle rounded-[1.4rem] p-4 sm:p-5">
                          <h3 className="text-sm font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                            Delivery health
                          </h3>
                          <div className="mt-4 space-y-4">
                            {stats.metrics.map((metric) => (
                              <div key={metric.label}>
                                <div className="flex items-start justify-between gap-4">
                                  <div>
                                    <p className="text-sm font-medium text-[var(--text)]">
                                      {metric.label}
                                    </p>
                                    <p className="mt-1 text-sm text-[var(--text-muted)]">
                                      {metric.detail}
                                    </p>
                                  </div>
                                  <p className="text-sm font-semibold text-[var(--text)]">
                                    {metric.value}
                                  </p>
                                </div>
                              </div>
                            ))}
                          </div>
                        </section>

                        <section className="app-subtle rounded-[1.4rem] p-4 sm:p-5">
                          <h3 className="text-sm font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                            Response distribution
                          </h3>
                          <div className="mt-4 space-y-4">
                            {stats.responseTimeDistribution.map((band) => (
                              <div key={band.label} className="space-y-2">
                                <div className="flex items-start justify-between gap-3 text-sm">
                                  <div>
                                    <p className="font-medium text-[var(--text)]">{band.label}</p>
                                    <p className="mt-1 text-[var(--text-muted)]">
                                      {band.count} jobs / {band.averageMinutes} min average
                                    </p>
                                  </div>
                                  <p className="font-medium text-[var(--text)]">
                                    {band.percentage.toFixed(1)}%
                                  </p>
                                </div>
                                <div className="h-2 overflow-hidden rounded-full bg-[var(--surface-3)]">
                                  <div
                                    className="h-full rounded-full bg-[var(--primary)]"
                                    style={{ width: `${Math.max(band.percentage, 4)}%` }}
                                  />
                                </div>
                              </div>
                            ))}
                          </div>
                        </section>
                      </div>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </section>
          </div>

          <aside className="space-y-4 xl:sticky xl:top-24 xl:self-start">
            <section className="app-panel p-5 sm:p-6">
              <div className="flex items-center gap-3">
                <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[var(--primary-soft)] text-[var(--primary)]">
                  <Wallet className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold tracking-[-0.03em] text-[var(--text)]">
                    Hire {agent.name}
                  </h2>
                  <p className="mt-1 text-sm text-[var(--text-muted)]">
                    Select an action to quote this job session.
                  </p>
                </div>
              </div>

              <div className="mt-5 space-y-3">
                {agent.actions.map((action) => (
                  <label
                    key={action.id}
                    className={cn(
                      "flex cursor-pointer items-start gap-3 rounded-[1.3rem] border p-4 transition",
                      selectedActionId === action.id
                        ? "border-[var(--primary)] bg-[color-mix(in_srgb,var(--primary-soft)_72%,var(--surface)_28%)]"
                        : "border-[var(--border)] hover:border-[var(--primary)]"
                    )}
                  >
                    <input
                      type="radio"
                      name="agent-action"
                      value={action.id}
                      checked={selectedActionId === action.id}
                      onChange={() => setSelectedActionId(action.id)}
                      className="mt-1 h-4 w-4 accent-[var(--primary)]"
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-medium text-[var(--text)]">{action.name}</p>
                        {action.demoAvailable ? (
                          <span className="app-status-badge" data-tone="accent">
                            Demo
                          </span>
                        ) : null}
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[var(--text-muted)]">
                        <span>{formatUsdc(action.priceUsdc)}</span>
                        <span>{action.estimatedDurationLabel}</span>
                      </div>
                    </div>
                  </label>
                ))}
              </div>

              <div className="mt-5 rounded-[1.4rem] border border-[var(--border)] bg-[var(--surface-2)] p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                      Selected quote
                    </p>
                    <p className="mt-2 text-base font-semibold text-[var(--text)]">
                      {selectedAction ? selectedAction.name : "Choose an action"}
                    </p>
                  </div>
                  {selectedAction ? (
                    <span className="app-status-badge" data-tone="default">
                      {selectedAction.estimatedDurationLabel}
                    </span>
                  ) : null}
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                  <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3">
                    <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                      Price
                    </p>
                    <p className="mt-2 text-lg font-semibold text-[var(--text)]">
                      {selectedAction ? formatUsdc(selectedAction.priceUsdc) : "--"}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3">
                    <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                      Estimated duration
                    </p>
                    <p className="mt-2 text-sm font-medium text-[var(--text)]">
                      {selectedAction ? selectedAction.estimatedDurationLabel : "--"}
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-5 space-y-3">
                <button
                  type="button"
                  onClick={() => {
                    if (selectedAction) {
                      createSession(selectedAction, "hire");
                    }
                  }}
                  disabled={!selectedAction || createSessionMutation.isPending}
                  className="inline-flex h-12 w-full items-center justify-center rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-55"
                >
                  {createSessionMutation.isPending ? (
                    <span className="inline-flex items-center gap-2">
                      <LoaderCircle className="h-4 w-4 animate-spin" />
                      Creating session
                    </span>
                  ) : (
                    "Hire Agent"
                  )}
                </button>

                {demoAction ? (
                  <button
                    type="button"
                    onClick={() => createSession(demoAction, "demo")}
                    disabled={createSessionMutation.isPending}
                    className="inline-flex h-12 w-full items-center justify-center rounded-full border border-[var(--border)] px-5 text-sm font-semibold text-[var(--text)] transition hover:border-[var(--primary)] hover:text-[var(--primary)] disabled:cursor-not-allowed disabled:opacity-55"
                  >
                    Try Free Demo
                  </button>
                ) : null}
              </div>

              {createSessionMutation.isError ? (
                <div className="mt-4 rounded-[1.2rem] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  <div className="flex items-start gap-2">
                    <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
                    <p>The job session could not be created right now. Please try again.</p>
                  </div>
                </div>
              ) : null}

              <div className="mt-6 border-t border-[var(--border)] pt-5">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-[var(--primary)]" />
                  <h3 className="text-sm font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                    Agent snapshot
                  </h3>
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
                  <div className="app-subtle rounded-2xl p-4">
                    <p className="text-lg font-semibold text-[var(--text)]">
                      {stats ? `${stats.successRate.toFixed(1)}%` : "--"}
                    </p>
                    <p className="mt-1 text-xs text-[var(--text-muted)]">Success rate</p>
                  </div>
                  <div className="app-subtle rounded-2xl p-4">
                    <p className="text-lg font-semibold text-[var(--text)]">
                      {stats ? stats.avgDeliveryLabel : "--"}
                    </p>
                    <p className="mt-1 text-xs text-[var(--text-muted)]">Avg time</p>
                  </div>
                  <div className="app-subtle rounded-2xl p-4">
                    <p className="text-lg font-semibold text-[var(--text)]">
                      {stats ? stats.totalJobs : "--"}
                    </p>
                    <p className="mt-1 text-xs text-[var(--text-muted)]">Total jobs</p>
                  </div>
                </div>

                <div className="mt-4 space-y-3 text-sm text-[var(--text-muted)]">
                  <div className="flex items-center gap-2">
                    <TimerReset className="h-4 w-4 text-[var(--primary)]" />
                    <span>
                      {stats
                        ? `${stats.onTimeRate.toFixed(1)}% of jobs delivered inside quoted timing.`
                        : "Loading delivery consistency."}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-[var(--primary)]" />
                    <span>
                      {stats
                        ? `${stats.repeatBuyerRate.toFixed(1)}% repeat buyer rate across recent work.`
                        : "Loading repeat buyer signal."}
                    </span>
                  </div>
                </div>
              </div>
            </section>
          </aside>
        </div>
      </div>
    </div>
  );
}
