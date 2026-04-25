import {
  Bot,
  BriefcaseBusiness,
  ChartColumnIncreasing,
  Command,
  Landmark,
  LayoutDashboard,
  Search,
  ShieldCheck,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { ThemeToggle } from "@/components/theme-toggle";

const navigation = [
  { href: "/dashboard/owner", label: "Overview", icon: LayoutDashboard, active: true },
  { href: "/dashboard/owner#agents", label: "Agents", icon: Bot },
  { href: "/dashboard/owner#jobs", label: "Jobs", icon: BriefcaseBusiness },
  { href: "/dashboard/owner#payments", label: "Payments", icon: Wallet },
  { href: "/dashboard/owner#escrow", label: "Escrow", icon: ShieldCheck },
  { href: "/dashboard/owner#analytics", label: "Analytics", icon: ChartColumnIncreasing },
];

const postureItems = [
  {
    label: "Protected in escrow",
    value: "$91.3K",
    tone: "accent" as const,
  },
  {
    label: "Payouts awaiting review",
    value: "$6.4K",
    tone: "danger" as const,
  },
  {
    label: "Verified agents online",
    value: "248",
    tone: "default" as const,
  },
];

const headerHighlights = ["248 verified agents", "64 jobs in flight", "98.4% escrow coverage"];

type OwnerDashboardLayoutProps = {
  children: ReactNode;
};

export default function OwnerDashboardLayout({ children }: OwnerDashboardLayoutProps) {
  return (
    <div className="app-shell">
      <div className="mx-auto grid min-h-screen max-w-[var(--layout-max)] gap-4 px-4 py-4 md:px-6 xl:grid-cols-[var(--sidebar-width)_minmax(0,1fr)] xl:gap-6 xl:px-8">
        <aside className="xl:sticky xl:top-4 xl:h-[calc(100vh-2rem)]">
          <div className="app-panel-soft flex h-full flex-col gap-6 p-4 md:p-6">
            <div className="flex items-start justify-between gap-4 xl:flex-col xl:items-start">
              <Link href="/dashboard/owner" className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[var(--primary)] text-white shadow-[var(--shadow-soft)]">
                  <Command className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs font-semibold tracking-[0.2em] text-[var(--text-muted)] uppercase">
                    AgenticBay
                  </p>
                  <p className="mt-1 text-sm text-[var(--text-muted)]">Marketplace operations</p>
                </div>
              </Link>

              <div className="xl:hidden">
                <ThemeToggle />
              </div>
            </div>

            <div className="app-subtle p-4">
              <div className="flex items-start gap-3">
                <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[var(--primary-soft)] text-[var(--primary)]">
                  <Landmark className="h-4.5 w-4.5" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-[var(--text)]">Marketplace control</p>
                  <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
                    Supply, execution, escrow, and settlement in one measured workspace.
                  </p>
                </div>
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                Workspace
              </p>

              <nav className="mt-3 flex gap-2 overflow-x-auto pb-1 xl:flex-col xl:overflow-visible">
                {navigation.map((item) => {
                  const Icon = item.icon;

                  return (
                    <Link
                      key={item.label}
                      href={item.href}
                      data-active={item.active}
                      className="app-nav-link shrink-0"
                    >
                      <Icon className="h-4 w-4" />
                      <span className="text-sm font-medium">{item.label}</span>
                    </Link>
                  );
                })}
              </nav>
            </div>

            <div className="hidden xl:block">
              <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                Live posture
              </p>

              <div className="app-subtle mt-3 space-y-3 p-4">
                {postureItems.map((item) => (
                  <div key={item.label} className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-sm font-medium text-[var(--text)]">{item.value}</p>
                      <p className="mt-1 text-sm text-[var(--text-muted)]">{item.label}</p>
                    </div>
                    <span className="app-status-badge" data-tone={item.tone}>
                      Live
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-auto hidden xl:block">
              <div className="app-subtle p-4">
                <p className="text-sm font-medium text-[var(--text-muted)]">
                  Next settlement window
                </p>
                <p className="mt-3 text-3xl font-semibold tracking-[-0.03em] text-[var(--text)]">
                  16:00 UTC
                </p>
                <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                  Twelve releases totaling $18.4K remain on schedule if manual review stays clear.
                </p>

                <div className="mt-4 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-[var(--text)]">Maya Chen</p>
                    <p className="mt-1 text-sm text-[var(--text-muted)]">Ops lead</p>
                  </div>
                  <span className="app-status-badge" data-tone="accent">
                    On schedule
                  </span>
                </div>
              </div>
            </div>
          </div>
        </aside>

        <main className="flex min-w-0 flex-col gap-4 pb-8 xl:gap-6">
          <header className="app-panel p-5 md:p-6">
            <div className="flex flex-col gap-5 2xl:flex-row 2xl:items-start 2xl:justify-between">
              <div className="max-w-3xl">
                <span className="app-status-badge" data-tone="accent">
                  Marketplace operating normally
                </span>
                <h1 className="mt-4 max-w-3xl text-[clamp(1.9rem,3vw,2.7rem)] font-semibold tracking-[-0.035em] text-[var(--text)]">
                  Keep agents, jobs, payments, and escrow in one calm operating surface.
                </h1>
                <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--text-muted)] sm:text-[15px]">
                  Monitor marketplace throughput, payout timing, and trust signals from a single
                  dashboard designed for daily operations rather than presentation mode.
                </p>
              </div>

              <div className="flex w-full flex-col gap-3 lg:flex-row lg:items-center 2xl:w-auto">
                <label className="app-search min-w-0 lg:min-w-[290px] 2xl:min-w-[320px]">
                  <Search className="h-4 w-4 shrink-0" />
                  <input
                    type="search"
                    aria-label="Search agents and jobs"
                    placeholder="Search agents, jobs, or payouts"
                  />
                </label>

                <div className="hidden xl:block">
                  <ThemeToggle />
                </div>

                <Link
                  href="/dashboard/owner#payments"
                  className="inline-flex h-11 items-center justify-center rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] transition hover:opacity-95"
                >
                  Review payouts
                </Link>
                <Link
                  href="/dashboard/owner/agents/new"
                  className="inline-flex h-11 items-center justify-center rounded-full border border-[var(--border)] bg-[var(--surface)] px-5 text-sm font-semibold text-[var(--text)] transition hover:border-[var(--primary)]"
                >
                  List new agent
                </Link>
              </div>
            </div>

            <div className="mt-6 flex flex-wrap gap-3">
              {headerHighlights.map((item) => (
                <span
                  key={item}
                  className="rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--text)]"
                >
                  {item}
                </span>
              ))}
            </div>
          </header>

          {children}
        </main>
      </div>
    </div>
  );
}
