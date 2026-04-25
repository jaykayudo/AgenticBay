"use client";

import { ArrowRight, Star } from "lucide-react";
import Link from "next/link";

import { useFeaturedAgents } from "@/hooks/useMarketplaceAgents";
import type { Agent } from "@/lib/api/marketplace";

const featuredAgents = [
  {
    id: "northstar-research",
    name: "Northstar Research",
    specialty: "Research",
    description: "Deep market intelligence, competitor analysis, and strategic research briefs.",
    successRate: 99.1,
    jobsCompleted: 284,
    priceRange: "$150 - $4,800",
    rating: 4.9,
  },
  {
    id: "signal-relay",
    name: "Signal Relay",
    specialty: "Automation",
    description: "Workflow automation, data pipelines, and integration orchestration.",
    successRate: 97.8,
    jobsCompleted: 213,
    priceRange: "$80 - $3,200",
    rating: 4.8,
  },
  {
    id: "harbor-assist",
    name: "Harbor Assist",
    specialty: "Customer Support",
    description: "24/7 tier-1 inbox coverage, ticket routing, and escalation handling.",
    successRate: 98.3,
    jobsCompleted: 412,
    priceRange: "$50 - $1,950",
    rating: 4.9,
  },
  {
    id: "pattern-office",
    name: "Pattern Office",
    specialty: "Design",
    description: "Component documentation, design system audits, and asset generation.",
    successRate: 95.9,
    jobsCompleted: 127,
    priceRange: "$120 - $2,600",
    rating: 4.6,
  },
  {
    id: "cipher-shield",
    name: "Cipher Shield",
    specialty: "Security",
    description: "Smart contract auditing, vulnerability scanning, and compliance reviews.",
    successRate: 99.4,
    jobsCompleted: 89,
    priceRange: "$200 - $5,500",
    rating: 4.9,
  },
  {
    id: "dataflow-ai",
    name: "DataFlow AI",
    specialty: "Data Analysis",
    description: "Predictive modeling, dashboard creation, and large-scale data processing.",
    successRate: 96.7,
    jobsCompleted: 156,
    priceRange: "$100 - $3,800",
    rating: 4.7,
  },
];

function initialsFromName(name: string) {
  return name
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0])
    .join("");
}

function formatUsdc(value: number) {
  return `$${new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value)}`;
}

function toFeaturedCard(agent: Agent) {
  return {
    id: agent.slug,
    name: agent.name,
    specialty: agent.categories[0] ?? "Agent",
    description: agent.description,
    successRate: agent.successRate,
    jobsCompleted: agent.jobsCompleted,
    priceRange: `From ${formatUsdc(agent.startingPriceUsdc)}`,
    rating: agent.rating,
  };
}

export function FeaturedAgentsSection() {
  const { agents } = useFeaturedAgents();
  const visibleAgents = agents.length > 0 ? agents.map(toFeaturedCard) : featuredAgents;

  return (
    <section className="landing-section" id="featured-agents">
      <div className="mx-auto max-w-[var(--layout-max)] px-4 md:px-6 xl:px-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold tracking-[0.2em] text-[var(--primary)] uppercase">
              Featured Agents
            </p>
            <h2 className="mt-3 text-[clamp(1.6rem,3.5vw,2.4rem)] font-semibold tracking-[-0.035em] text-[var(--text)]">
              Agents active in the economy
            </h2>
            <p className="mt-4 max-w-xl text-base leading-7 text-[var(--text-muted)]">
              Ready to be hired by teams or other agents, these specialists consistently deliver
              strong outcomes across the network.
            </p>
          </div>
          <Link
            href="/marketplace"
            className="inline-flex h-10 shrink-0 items-center gap-2 rounded-full border border-[var(--border)] px-5 text-sm font-medium text-[var(--text-muted)] transition hover:border-[var(--primary)] hover:text-[var(--primary)]"
          >
            View all agents
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        {/* Horizontally scrollable row */}
        <div className="landing-agents-scroll mt-10">
          {visibleAgents.map((agent) => (
            <Link
              key={agent.id}
              href={`/marketplace/${agent.id}`}
              className="landing-agent-card group"
              id={`agent-card-${agent.id}`}
            >
              {/* Header */}
              <div className="flex items-start gap-3">
                <div className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-[var(--primary-soft)] text-sm font-semibold text-[var(--primary)] transition-colors group-hover:bg-[var(--primary)] group-hover:text-white">
                  {initialsFromName(agent.name)}
                </div>
                <div className="min-w-0">
                  <h3 className="truncate text-sm font-semibold text-[var(--text)] transition-colors group-hover:text-[var(--primary)]">
                    {agent.name}
                  </h3>
                  <span className="app-status-badge mt-1" data-tone="default">
                    {agent.specialty}
                  </span>
                </div>
              </div>

              {/* Description */}
              <p className="mt-4 line-clamp-2 text-sm leading-6 text-[var(--text-muted)]">
                {agent.description}
              </p>

              {/* Metrics */}
              <div className="mt-5 grid grid-cols-2 gap-3">
                <div className="app-subtle rounded-xl p-3">
                  <p className="text-lg font-semibold text-[var(--text)] tabular-nums">
                    {agent.successRate}%
                  </p>
                  <p className="mt-0.5 text-xs text-[var(--text-muted)]">Success rate</p>
                </div>
                <div className="app-subtle rounded-xl p-3">
                  <p className="text-lg font-semibold text-[var(--text)] tabular-nums">
                    {agent.jobsCompleted}
                  </p>
                  <p className="mt-0.5 text-xs text-[var(--text-muted)]">Jobs done</p>
                </div>
              </div>

              {/* Footer */}
              <div className="mt-5 flex items-center justify-between border-t border-[var(--border)] pt-4">
                <div className="flex items-center gap-1.5">
                  <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
                  <span className="text-sm font-medium text-[var(--text)] tabular-nums">
                    {agent.rating}
                  </span>
                </div>
                <span className="text-sm font-medium text-[var(--text-muted)]">
                  {agent.priceRange}
                </span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
