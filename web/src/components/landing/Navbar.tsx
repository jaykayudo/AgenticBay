"use client";

import { BookOpen, Command, LayoutDashboard, Menu, MessageSquare, Store, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { ThemeToggle } from "@/components/theme-toggle";
import { useAuthStore } from "@/store/auth-store";
import { cn } from "@/lib/utils";

const navLinks = [
  { href: "#categories", label: "Categories" },
  { href: "#how-it-works", label: "How it Works" },
  { href: "#featured-agents", label: "Agents" },
  { href: "/marketplace", label: "Explore Agents", isRoute: true, icon: Store },
  { href: "/docs", label: "Docs", isRoute: true, icon: BookOpen },
];

export function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { accessToken, hydrated, hydrate } = useAuthStore();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  const isLoggedIn = hydrated && !!accessToken;

  return (
    <nav className="landing-navbar" id="navbar">
      <div className="mx-auto flex h-16 max-w-[var(--layout-max)] items-center justify-between px-4 md:px-6 xl:px-8">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[var(--primary)] text-white shadow-[var(--shadow-soft)]">
            <Command className="h-5 w-5" />
          </div>
          <span className="text-sm font-semibold tracking-[0.2em] text-[var(--text)] uppercase">
            AgenticBay
          </span>
        </Link>

        {/* Desktop nav links */}
        <div className="hidden items-center gap-1 md:flex">
          {navLinks.map((link) =>
            link.isRoute ? (
              <Link
                key={link.href}
                href={link.href}
                className="flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
              >
                {link.icon && <link.icon className="h-3.5 w-3.5" />}
                {link.label}
              </Link>
            ) : (
              <a
                key={link.href}
                href={link.href}
                className="rounded-full px-4 py-2 text-sm font-medium text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
              >
                {link.label}
              </a>
            )
          )}
        </div>

        {/* Right side */}
        <div className="flex items-center gap-3">
          <div className="hidden sm:block">
            <ThemeToggle />
          </div>

          {/* Dashboard link — only when logged in */}
          {isLoggedIn && (
            <Link
              href="/dashboard"
              className="hidden items-center gap-2 rounded-full border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text)] sm:inline-flex"
            >
              <LayoutDashboard className="h-4 w-4" />
              Dashboard
            </Link>
          )}

          {/* Primary CTA — always visible */}
          <Link
            href={isLoggedIn ? "/orchestrator" : "/login"}
            className="hidden items-center gap-2 rounded-full bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] transition hover:opacity-90 sm:inline-flex"
          >
            <MessageSquare className="h-4 w-4" />
            Interact with Agent
          </Link>

          {/* Mobile hamburger */}
          <button
            type="button"
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl text-[var(--text-muted)] transition hover:bg-[var(--surface-2)] hover:text-[var(--text)] md:hidden"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      <div
        className={cn(
          "overflow-hidden border-t border-[var(--border)] transition-all duration-300 ease-in-out md:hidden",
          mobileOpen ? "max-h-96 opacity-100" : "max-h-0 opacity-0"
        )}
      >
        <div className="mx-auto flex max-w-[var(--layout-max)] flex-col gap-1 px-4 py-4">
          {navLinks.map((link) =>
            link.isRoute ? (
              <Link
                key={link.href}
                href={link.href}
                className="flex items-center gap-2 rounded-xl px-4 py-3 text-sm font-medium text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
                onClick={() => setMobileOpen(false)}
              >
                {link.icon && <link.icon className="h-4 w-4" />}
                {link.label}
              </Link>
            ) : (
              <a
                key={link.href}
                href={link.href}
                className="rounded-xl px-4 py-3 text-sm font-medium text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
                onClick={() => setMobileOpen(false)}
              >
                {link.label}
              </a>
            )
          )}
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <ThemeToggle />
            {isLoggedIn && (
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-2)]"
                onClick={() => setMobileOpen(false)}
              >
                <LayoutDashboard className="h-4 w-4" />
                Dashboard
              </Link>
            )}
            <Link
              href={isLoggedIn ? "/orchestrator" : "/login"}
              className="inline-flex items-center gap-2 rounded-full bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] transition hover:opacity-90"
              onClick={() => setMobileOpen(false)}
            >
              <MessageSquare className="h-4 w-4" />
              Interact with Agent
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}
