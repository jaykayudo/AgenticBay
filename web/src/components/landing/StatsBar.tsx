"use client";

import { Bot, Briefcase, DollarSign } from "lucide-react";

import { useMarketplaceStats } from "@/hooks/useMarketplaceAgents";
import { cn } from "@/lib/utils";

interface MarketplaceStats {
  totalAgents: number;
  totalVolume: number;
  totalJobs: number;
}

const fallbackStats: MarketplaceStats = {
  totalAgents: 248,
  totalVolume: 1_240_000,
  totalJobs: 3842,
};

function formatVolume(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value}`;
}

function formatNumber(value: number): string {
  return value.toLocaleString("en-US");
}

const statItems = [
  {
    key: "totalAgents" as const,
    label: "AI Agents",
    icon: Bot,
    format: formatNumber,
  },
  {
    key: "totalVolume" as const,
    label: "Total Volume",
    icon: DollarSign,
    format: formatVolume,
  },
  {
    key: "totalJobs" as const,
    label: "Jobs Completed",
    icon: Briefcase,
    format: formatNumber,
  },
];

function StatSkeleton() {
  return (
    <div className="flex items-center gap-4">
      <div className="h-12 w-12 animate-pulse rounded-2xl bg-[var(--surface-3)]" />
      <div className="space-y-2">
        <div className="h-7 w-20 animate-pulse rounded-lg bg-[var(--surface-3)]" />
        <div className="h-4 w-24 animate-pulse rounded-md bg-[var(--surface-3)]" />
      </div>
    </div>
  );
}

export function StatsBar() {
  const { stats: data, isLoading } = useMarketplaceStats();

  const stats = data ?? fallbackStats;

  return (
    <section className="landing-section" id="stats-bar">
      <div className="mx-auto max-w-[var(--layout-max)] px-4 md:px-6 xl:px-8">
        <div className="app-panel-soft grid grid-cols-1 divide-y divide-[var(--border)] sm:grid-cols-3 sm:divide-x sm:divide-y-0">
          {statItems.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.key}
                className={cn("flex items-center justify-center gap-4 px-6 py-6 sm:px-8 sm:py-8")}
              >
                {isLoading ? (
                  <StatSkeleton />
                ) : (
                  <>
                    <div className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-[var(--primary-soft)] text-[var(--primary)]">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-2xl font-semibold tracking-[-0.03em] text-[var(--text)] tabular-nums sm:text-3xl">
                        {item.format(stats[item.key])}
                      </p>
                      <p className="mt-1 text-sm text-[var(--text-muted)]">{item.label}</p>
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
