import type { Metadata } from "next";
import Link from "next/link";
import { BookOpen } from "lucide-react";

import { DocsSidebar } from "@/components/docs/DocsSidebar";
import { DocsTOC } from "@/components/docs/DocsTOC";
import { DocsSearch } from "@/components/docs/DocsSearch";
import { DocsMobileNav } from "@/components/docs/DocsMobileNav";

export const metadata: Metadata = {
  title: {
    template: "%s — Agentic Bay Docs",
    default: "Agentic Bay Documentation",
  },
  description:
    "Complete developer documentation for Agentic Bay — the AI agent marketplace platform.",
};

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      {/* Top nav */}
      <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-[1400px] items-center gap-4 px-4 sm:px-6">
          <DocsMobileNav />
          <Link href="/docs" className="flex items-center gap-2 font-semibold">
            <BookOpen className="size-4 text-primary" />
            <span className="hidden sm:inline">Docs</span>
          </Link>
          <div className="hidden w-64 lg:block">
            <DocsSearch />
          </div>
          <nav className="ml-auto flex items-center gap-4 text-sm">
            <Link
              href="/"
              className="text-muted-foreground transition-colors hover:text-foreground"
            >
              Marketplace
            </Link>
            <Link
              href="/dashboard"
              className="text-muted-foreground transition-colors hover:text-foreground"
            >
              Dashboard
            </Link>
          </nav>
        </div>
      </header>

      <div className="mx-auto flex w-full max-w-[1400px] flex-1 px-4 sm:px-6">
        {/* Sidebar */}
        <aside className="sticky top-14 hidden h-[calc(100vh-3.5rem)] w-56 shrink-0 overflow-y-auto lg:block xl:w-64">
          <DocsSidebar />
        </aside>

        {/* Main content */}
        <main className="min-w-0 flex-1 py-8 lg:px-8">{children}</main>

        {/* TOC */}
        <aside className="sticky top-14 hidden h-[calc(100vh-3.5rem)] w-48 shrink-0 overflow-y-auto xl:block">
          <DocsTOC />
        </aside>
      </div>
    </div>
  );
}
