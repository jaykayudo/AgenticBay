"use client";

import {
  ArrowRight,
  ArrowUpRight,
  Bookmark,
  Clock3,
  ExternalLink,
  Star,
  Wallet,
} from "lucide-react";
import Link from "next/link";

import { useApiQuery } from "@/hooks/useApi";

type CircleWalletBalanceResponse = {
  provider: "Circle";
  walletId: string;
  walletAddress: string;
  availableBalanceUsdc: number;
  pendingBalanceUsdc: number;
  lockedInEscrowUsdc: number;
  lastUpdatedAt: string;
  syncStatus: "live";
};

type BuyerDashboardSummaryResponse = {
  generatedAt: string;
  stats: {
    totalJobs: number;
    totalSpentUsdc: number;
    savedAgentsCount: number;
  };
  recentJobs: Array<{
    sessionId: string;
    agentSlug: string;
    agentName: string;
    actionName: string;
    status: "done" | "running" | "failed";
    statusLabel: "Done" | "Running" | "Failed";
    amountChargedUsdc: number;
    createdAt: string;
    mode: "hire" | "demo";
  }>;
};

type BuyerRecommendedAgent = {
  id: string;
  slug: string;
  name: string;
  description: string;
  rating: number;
  reviewCount: number;
  startingPriceUsdc: number;
  speedLabel: string;
  tags: string[];
  avatar: {
    label: string;
    bg: string;
    fg: string;
  };
  reason: string;
};

const wholeNumberFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 0,
});

const preciseNumberFormatter = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatUsdc(value: number, precise = false) {
  const formatter = precise ? preciseNumberFormatter : wholeNumberFormatter;
  return `${formatter.format(value)} USDC`;
}

function formatTimeAgo(isoDate: string) {
  const deltaMs = Date.now() - new Date(isoDate).getTime();
  const minutes = Math.max(1, Math.round(deltaMs / (1000 * 60)));

  if (minutes < 60) {
    return `${minutes}m ago`;
  }

  const hours = Math.round(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }

  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

function statusTone(status: BuyerDashboardSummaryResponse["recentJobs"][number]["status"]) {
  if (status === "done") {
    return "accent";
  }

  if (status === "failed") {
    return "danger";
  }

  return "default";
}

function StatCard({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <section className="app-panel p-5 sm:p-6">
      <p className="text-sm text-[var(--text-muted)]">{label}</p>
      <p className="mt-4 text-[1.85rem] font-semibold tracking-[-0.04em] text-[var(--text)] tabular-nums">
        {value}
      </p>
      <p className="mt-3 text-sm leading-6 text-[var(--text-muted)]">{hint}</p>
    </section>
  );
}

export function BuyerDashboardPage() {
  const walletQuery = useApiQuery<CircleWalletBalanceResponse>(
    ["buyer-wallet-balance"],
    "/circle/wallets/primary/balance",
    {
      refetchInterval: 15000,
    }
  );

  const summaryQuery = useApiQuery<BuyerDashboardSummaryResponse>(
    ["buyer-dashboard-summary"],
    "/buyer/dashboard/summary?limit=10"
  );

  const recommendedQuery = useApiQuery<BuyerRecommendedAgent[]>(
    ["buyer-recommended-agents"],
    "/buyer/recommended-agents?limit=6"
  );

  const wallet = walletQuery.data;
  const summary = summaryQuery.data;
  const recommendedAgents = recommendedQuery.data ?? [];
  const recentJobs = summary?.recentJobs ?? [];

  return (
    <div className="space-y-4 xl:space-y-6">
      <section id="overview" className="app-panel p-5 sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <span className="app-status-badge" data-tone="accent">
              Buyer dashboard
            </span>
            <h1 className="mt-4 text-[clamp(1.85rem,3vw,2.6rem)] font-semibold tracking-[-0.04em] text-[var(--text)]">
              Track balance, active jobs, and next-best agents without leaving the hiring flow.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--text-muted)] sm:text-[15px]">
              This view keeps your Circle wallet balance, the latest buyer-side job activity, and
              recommended agents in one place so you can move from discovery to execution quickly.
            </p>
          </div>

          <Link
            href="/dashboard/owner"
            className="inline-flex h-11 items-center justify-center gap-2 rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] transition hover:opacity-95"
          >
            Go to the Agent Owner Dashboard
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      <section
        id="wallet"
        className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(280px,340px)] xl:gap-6"
      >
        <div className="app-panel p-5 sm:p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-sm font-medium text-[var(--text-muted)]">Wallet balance</p>
              <p className="mt-4 text-[2.35rem] font-semibold tracking-[-0.05em] text-[var(--text)] tabular-nums">
                {wallet ? formatUsdc(wallet.availableBalanceUsdc, true) : "--"}
              </p>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--text-muted)]">
                Real-time buyer wallet balance, mocked through a Circle-shaped API response so the
                dashboard stays usable before live wallet sync is turned back on.
              </p>
            </div>

            <span className="app-status-badge" data-tone="accent">
              {wallet?.provider ?? "Circle"} sync {wallet?.syncStatus ?? "pending"}
            </span>
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            <div className="app-subtle p-4">
              <p className="text-sm text-[var(--text-muted)]">Pending</p>
              <p className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[var(--text)] tabular-nums">
                {wallet ? formatUsdc(wallet.pendingBalanceUsdc) : "--"}
              </p>
            </div>

            <div className="app-subtle p-4">
              <p className="text-sm text-[var(--text-muted)]">Locked in escrow</p>
              <p className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[var(--text)] tabular-nums">
                {wallet ? formatUsdc(wallet.lockedInEscrowUsdc) : "--"}
              </p>
            </div>

            <div className="app-subtle p-4">
              <p className="text-sm text-[var(--text-muted)]">Wallet ID</p>
              <p className="mt-2 truncate text-sm font-medium text-[var(--text)]">
                {wallet?.walletId ?? "Loading..."}
              </p>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <button
              type="button"
              className="inline-flex h-11 items-center justify-center rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)]"
            >
              Deposit
            </button>
            <button
              type="button"
              className="inline-flex h-11 items-center justify-center rounded-full border border-[var(--border)] px-5 text-sm font-semibold text-[var(--text)]"
            >
              Withdraw
            </button>
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-3 text-sm text-[var(--text-muted)]">
            <span className="inline-flex items-center gap-2">
              <Wallet className="h-4 w-4" />
              {wallet?.walletAddress ?? "Loading wallet address"}
            </span>
            <span className="inline-flex items-center gap-2">
              <Clock3 className="h-4 w-4" />
              Updated {wallet ? formatTimeAgo(wallet.lastUpdatedAt) : "just now"}
            </span>
          </div>
        </div>

        <div className="app-panel p-5 sm:p-6">
          <p className="text-sm font-medium text-[var(--text-muted)]">Buyer notes</p>
          <div className="mt-5 grid gap-3">
            <div className="app-subtle p-4">
              <p className="font-medium text-[var(--text)]">Mock wallet actions</p>
              <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                Deposit and withdraw buttons are present for the UI flow while the live Circle
                action handlers are still mocked.
              </p>
            </div>

            <div className="app-subtle p-4">
              <p className="font-medium text-[var(--text)]">Escrow visibility</p>
              <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                Running jobs keep their locked amount visible here so buyers can watch spend and
                delivery progress together.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3 xl:gap-6">
        <StatCard
          label="Total Jobs"
          value={summary ? wholeNumberFormatter.format(summary.stats.totalJobs) : "--"}
          hint="All recent buyer-side sessions available through the mocked session API."
        />
        <StatCard
          label="Total Spent"
          value={summary ? formatUsdc(summary.stats.totalSpentUsdc) : "--"}
          hint="Aggregate USDC committed across your current mocked buyer history."
        />
        <StatCard
          label="Saved Agents"
          value={summary ? wholeNumberFormatter.format(summary.stats.savedAgentsCount) : "--"}
          hint="Pinned specialists and likely next hires surfaced for quick re-engagement."
        />
      </section>

      <section id="jobs" className="app-panel p-5 sm:p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
              My Jobs
            </p>
            <h2 className="mt-2 text-[1.15rem] font-semibold tracking-[-0.02em] text-[var(--text)]">
              Recent activity
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--text-muted)]">
              The latest ten jobs, each linked back into the live session page for testing.
            </p>
          </div>

          <Link
            href="/marketplace"
            className="inline-flex h-10 items-center justify-center rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text-muted)] transition hover:text-[var(--text)]"
          >
            Hire another agent
          </Link>
        </div>

        <div className="mt-6 space-y-3">
          {recentJobs.length > 0 ? (
            recentJobs.map((job) => (
              <Link
                key={job.sessionId}
                href={`/jobs/${job.sessionId}`}
                className="block rounded-[1.35rem] border border-[var(--border)] bg-[var(--surface)] p-4 transition hover:bg-[var(--surface-2)]"
              >
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <div className="min-w-0">
                    <p className="font-medium text-[var(--text)]">{job.actionName}</p>
                    <p className="mt-1 text-sm text-[var(--text-muted)]">
                      {job.agentName}
                      {job.mode === "demo" ? " . Demo session" : ""}
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-3 text-sm">
                    <span className="app-status-badge" data-tone={statusTone(job.status)}>
                      {job.statusLabel}
                    </span>
                    <span className="font-medium text-[var(--text)] tabular-nums">
                      {formatUsdc(job.amountChargedUsdc)}
                    </span>
                    <span className="text-[var(--text-muted)]">{formatTimeAgo(job.createdAt)}</span>
                    <span className="inline-flex items-center gap-1.5 text-[var(--text-muted)]">
                      Open session
                      <ExternalLink className="h-4 w-4" />
                    </span>
                  </div>
                </div>
              </Link>
            ))
          ) : (
            <div className="app-subtle p-6 text-sm text-[var(--text-muted)]">
              No recent jobs yet. Hire an agent from the marketplace to start your first session.
            </div>
          )}
        </div>
      </section>

      <section id="saved" className="app-panel p-5 sm:p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
              Saved Agents
            </p>
            <h2 className="mt-2 text-[1.15rem] font-semibold tracking-[-0.02em] text-[var(--text)]">
              Recommended specialists
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--text-muted)]">
              Suggested hires pulled from the API layer and tuned toward buyers with active job
              volume.
            </p>
          </div>

          <Link
            href="/marketplace"
            className="inline-flex h-10 items-center justify-center rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text-muted)] transition hover:text-[var(--text)]"
          >
            Browse marketplace
          </Link>
        </div>

        <div className="mt-6 flex gap-4 overflow-x-auto pb-2">
          {recommendedAgents.map((agent) => (
            <article
              key={agent.id}
              className="max-w-[320px] min-w-[280px] shrink-0 rounded-[1.5rem] border border-[var(--border)] bg-[var(--surface)] p-5"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div
                    className="grid h-12 w-12 place-items-center rounded-2xl text-sm font-semibold shadow-[var(--shadow-soft)]"
                    style={{
                      backgroundColor: agent.avatar.bg,
                      color: agent.avatar.fg,
                    }}
                  >
                    {agent.avatar.label}
                  </div>
                  <div>
                    <p className="font-medium text-[var(--text)]">{agent.name}</p>
                    <p className="mt-1 text-sm text-[var(--text-muted)]">{agent.speedLabel}</p>
                  </div>
                </div>

                <span className="inline-flex items-center gap-1 text-sm font-medium text-[var(--text-muted)]">
                  <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
                  {agent.rating.toFixed(1)}
                </span>
              </div>

              <p className="mt-4 text-sm leading-6 text-[var(--text-muted)]">{agent.reason}</p>
              <p className="mt-3 line-clamp-2 text-sm leading-6 text-[var(--text-muted)]">
                {agent.description}
              </p>

              <div className="mt-4 flex flex-wrap gap-2">
                {agent.tags.slice(0, 3).map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1 text-xs text-[var(--text-muted)]"
                  >
                    {tag}
                  </span>
                ))}
              </div>

              <div className="mt-5 flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm text-[var(--text-muted)]">Starting at</p>
                  <p className="mt-1 text-lg font-semibold text-[var(--text)]">
                    {formatUsdc(agent.startingPriceUsdc)}
                  </p>
                  <p className="mt-1 text-sm text-[var(--text-muted)]">
                    {wholeNumberFormatter.format(agent.reviewCount)} reviews
                  </p>
                </div>

                <Link
                  href={`/marketplace/${agent.slug}`}
                  className="inline-flex h-10 items-center justify-center gap-2 rounded-full bg-[var(--primary)] px-4 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)]"
                >
                  View agent
                  <ArrowUpRight className="h-4 w-4" />
                </Link>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section id="settings" className="app-panel p-5 sm:p-6">
        <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
          Settings
        </p>
        <h2 className="mt-2 text-[1.15rem] font-semibold tracking-[-0.02em] text-[var(--text)]">
          Buyer preferences
        </h2>
        <div className="mt-6 grid gap-3 md:grid-cols-2">
          <div className="app-subtle p-4">
            <div className="flex items-start gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[var(--primary-soft)] text-[var(--primary)]">
                <Bookmark className="h-4.5 w-4.5" />
              </div>
              <div>
                <p className="font-medium text-[var(--text)]">Saved agent alerts</p>
                <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                  Keep notifications focused on availability changes, faster delivery windows, and
                  stronger matches in your saved categories.
                </p>
              </div>
            </div>
          </div>

          <div className="app-subtle p-4">
            <div className="flex items-start gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[var(--primary-soft)] text-[var(--primary)]">
                <Wallet className="h-4.5 w-4.5" />
              </div>
              <div>
                <p className="font-medium text-[var(--text)]">Escrow preferences</p>
                <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                  Payment and release behavior can be surfaced here once the live Circle controls
                  are connected.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
