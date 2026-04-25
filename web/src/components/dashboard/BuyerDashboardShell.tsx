"use client";

import {
  Bookmark,
  BriefcaseBusiness,
  Command,
  LayoutDashboard,
  Settings,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/utils";

const navigation = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/jobs", label: "My Jobs", icon: BriefcaseBusiness },
  { href: "/dashboard#saved", label: "Saved Agents", icon: Bookmark },
  { href: "/dashboard/wallet", label: "Wallet", icon: Wallet },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

type BuyerDashboardShellProps = {
  children: ReactNode;
};

function getActiveHref(pathname: string, hash: string) {
  if (pathname === "/dashboard/jobs") {
    return "/dashboard/jobs";
  }

  if (pathname === "/dashboard/wallet") {
    return "/dashboard/wallet";
  }

  if (pathname === "/dashboard/settings") {
    return "/dashboard/settings";
  }

  if (pathname !== "/dashboard") {
    return "/dashboard";
  }

  return hash ? `/dashboard${hash}` : "/dashboard";
}

export function BuyerDashboardShell({ children }: BuyerDashboardShellProps) {
  const pathname = usePathname();
  const [activeHref, setActiveHref] = useState(() =>
    getActiveHref(pathname, typeof window === "undefined" ? "" : window.location.hash)
  );

  useEffect(() => {
    const syncActiveHref = () => {
      setActiveHref(getActiveHref(pathname, window.location.hash));
    };

    syncActiveHref();
    window.addEventListener("hashchange", syncActiveHref);

    return () => {
      window.removeEventListener("hashchange", syncActiveHref);
    };
  }, [pathname]);

  if (pathname.startsWith("/dashboard/owner")) {
    return <>{children}</>;
  }

  return (
    <div className="app-shell">
      <div className="mx-auto grid min-h-screen max-w-[var(--layout-max)] gap-4 px-4 py-4 md:px-6 xl:grid-cols-[280px_minmax(0,1fr)] xl:gap-6 xl:px-8">
        <aside className="hidden xl:sticky xl:top-4 xl:block xl:h-[calc(100vh-2rem)]">
          <div className="app-panel-soft flex h-full flex-col gap-6 p-6">
            <div className="flex items-start justify-between gap-4">
              <Link href="/dashboard" className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[var(--primary)] text-white shadow-[var(--shadow-soft)]">
                  <Command className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs font-semibold tracking-[0.2em] text-[var(--text-muted)] uppercase">
                    AgenticBay
                  </p>
                  <p className="mt-1 text-sm text-[var(--text-muted)]">Buyer workspace</p>
                </div>
              </Link>

              <ThemeToggle />
            </div>

            <div className="app-subtle p-4">
              <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                Wallet rail
              </p>
              <p className="mt-3 text-xl font-semibold tracking-[-0.03em] text-[var(--text)]">
                Circle-powered USDC
              </p>
              <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                Balance, escrow locks, and active buyer jobs in one steady operating surface.
              </p>
            </div>

            <div>
              <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                Navigation
              </p>
              <nav className="mt-3 flex flex-col gap-2">
                {navigation.map((item) => {
                  const Icon = item.icon;
                  const isActive = activeHref === item.href;

                  return (
                    <Link
                      key={item.label}
                      href={item.href}
                      data-active={isActive}
                      className="app-nav-link"
                    >
                      <Icon className="h-4 w-4" />
                      <span className="text-sm font-medium">{item.label}</span>
                    </Link>
                  );
                })}
              </nav>
            </div>

            <div className="app-subtle mt-auto p-4">
              <p className="text-sm font-medium text-[var(--text)]">Buyer mode</p>
              <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                This dashboard is tuned for hiring flow visibility, recent job tracking, and wallet
                readiness rather than owner-side analytics.
              </p>
              <Link
                href="/dashboard/owner"
                className="mt-4 inline-flex h-10 items-center justify-center rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text-muted)] transition hover:text-[var(--text)]"
              >
                Open owner dashboard
              </Link>
            </div>
          </div>
        </aside>

        <main className="min-w-0 pb-28 xl:pb-8">{children}</main>
      </div>

      <div className="fixed inset-x-4 bottom-4 z-40 xl:hidden">
        <div className="app-panel-soft flex items-center justify-between gap-2 px-2 py-2">
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = activeHref === item.href;

            return (
              <Link
                key={item.label}
                href={item.href}
                className={cn(
                  "flex min-w-0 flex-1 flex-col items-center gap-1 rounded-2xl px-2 py-2 text-[11px] font-medium transition",
                  isActive
                    ? "bg-[var(--surface)] text-[var(--text)] shadow-[var(--shadow-soft)]"
                    : "text-[var(--text-muted)]"
                )}
              >
                <Icon className="h-4 w-4" />
                <span className="truncate">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
