"use client";

import {
  ArrowLeft,
  ArrowRight,
  Bot,
  Command,
  LoaderCircle,
  Search,
  SearchX,
  Sparkles,
  Star,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { startTransition, useState } from "react";

import { ThemeToggle } from "@/components/theme-toggle";
import { useAgentSearch } from "@/hooks/useAgentSearch";
import { apiFetch } from "@/lib/api";
import type {
  SearchResponse,
  SearchResult as MarketplaceSearchResult,
} from "@/lib/api/marketplace";
import { cn } from "@/lib/utils";

type MarketplaceSessionRead = {
  sessionId: string;
  redirectPath: string;
};

const numberFormatter = new Intl.NumberFormat("en-US");

function formatUsdc(value: number) {
  return `${numberFormatter.format(value)} USDC`;
}

function AgentAvatar({ result }: { result: MarketplaceSearchResult }) {
  return (
    <div
      className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl text-sm font-semibold shadow-[var(--shadow-soft)]"
      style={{
        backgroundColor: result.avatar.bg,
        color: result.avatar.fg,
      }}
    >
      {result.avatar.label}
    </div>
  );
}

function ResultCard({
  result,
  highlighted = false,
  pending,
  onHireNow,
}: {
  result: MarketplaceSearchResult;
  highlighted?: boolean;
  pending: boolean;
  onHireNow: (result: MarketplaceSearchResult) => void;
}) {
  return (
    <article
      className={cn(
        "rounded-[1.5rem] border bg-[var(--surface)] p-5 transition sm:p-6",
        highlighted
          ? "border-[var(--primary)] shadow-[0_18px_60px_rgba(108,92,231,0.18)]"
          : "border-[var(--border)] shadow-[var(--shadow-soft)]"
      )}
    >
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex min-w-0 gap-4">
          <AgentAvatar result={result} />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="app-status-badge" data-tone={highlighted ? "default" : "accent"}>
                {result.matchPercentage}% match
              </span>
              {highlighted ? (
                <span className="app-status-badge" data-tone="accent">
                  Best Match
                </span>
              ) : null}
            </div>

            <h2 className="mt-3 text-xl font-semibold text-[var(--text)]">{result.agentName}</h2>
            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-[var(--text-muted)]">
              <span className="inline-flex items-center gap-1.5">
                <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
                {result.rating.toFixed(1)}
              </span>
              <span>{numberFormatter.format(result.jobsCompleted)} jobs</span>
              <span>Starting at {formatUsdc(result.startingPriceUsdc)}</span>
            </div>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-[var(--text-muted)]">
              {result.description}
            </p>
            <p className="mt-3 text-sm leading-6 text-[var(--text-muted)]">{result.reason}</p>
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap gap-2 lg:justify-end">
          <Link
            href={`/marketplace/${result.agentSlug}`}
            className="inline-flex h-10 items-center justify-center rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text)] transition hover:bg-[var(--surface-2)]"
          >
            View
          </Link>
          <button
            type="button"
            disabled={pending}
            onClick={() => onHireNow(result)}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-full bg-[var(--primary)] px-4 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] transition hover:opacity-95 disabled:opacity-55"
          >
            {pending ? (
              <LoaderCircle className="h-4 w-4 animate-spin" />
            ) : (
              <Zap className="h-4 w-4" />
            )}
            {pending ? "Starting" : "Hire Now"}
          </button>
        </div>
      </div>
    </article>
  );
}

function MarketplaceSearchResultsContent({ query }: { query: string }) {
  const router = useRouter();
  const [searchDraft, setSearchDraft] = useState(query);
  const [pendingAgentSlug, setPendingAgentSlug] = useState<string | null>(null);

  const searchQuery = useAgentSearch(query);

  const data: SearchResponse | null = query
    ? {
        query: searchQuery.query,
        generatedAt: searchQuery.generatedAt ?? "",
        resultCount: searchQuery.resultCount,
        orchestratorSuggestion: searchQuery.orchestratorSuggestion ?? "",
        bestMatch: searchQuery.bestMatch,
        results: searchQuery.results,
      }
    : null;
  const bestMatch = data?.bestMatch ?? null;
  const otherResults =
    data?.results.filter((result) => result.agentSlug !== bestMatch?.agentSlug) ?? [];

  function submitSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextQuery = searchDraft.trim();

    startTransition(() => {
      router.push(
        nextQuery ? `/marketplace/search?q=${encodeURIComponent(nextQuery)}` : "/marketplace"
      );
    });
  }

  async function hireNow(result: MarketplaceSearchResult) {
    setPendingAgentSlug(result.agentSlug);

    try {
      const session = await apiFetch<MarketplaceSessionRead>(
        `/marketplace/agents/${encodeURIComponent(result.agentSlug)}/sessions`,
        {
          method: "post",
          data: result.primaryAction,
        }
      );

      startTransition(() => {
        router.push(session.redirectPath);
      });
    } finally {
      setPendingAgentSlug(null);
    }
  }

  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--foreground)]">
      <header className="sticky top-0 z-40 border-b border-[var(--border)] bg-[color-mix(in_srgb,var(--bg-elevated)_92%,transparent)] backdrop-blur">
        <div className="mx-auto flex max-w-[var(--layout-max)] flex-col gap-4 px-4 py-4 md:px-6 lg:flex-row lg:items-center xl:px-8">
          <Link href="/marketplace" className="flex items-center gap-3 lg:w-[260px]">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[var(--primary)] text-white shadow-[var(--shadow-soft)]">
              <Command className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-semibold tracking-[0.2em] text-[var(--text-muted)] uppercase">
                AgenticBay
              </p>
              <p className="mt-1 text-sm text-[var(--text-muted)]">Search results</p>
            </div>
          </Link>

          <form className="app-search flex-1" onSubmit={submitSearch}>
            <Search className="h-4 w-4 shrink-0" />
            <input
              type="search"
              aria-label="Search for a service"
              value={searchDraft}
              placeholder="Describe the service you need"
              onChange={(event) => setSearchDraft(event.target.value)}
            />
            <button
              type="submit"
              className="inline-flex h-9 shrink-0 items-center justify-center rounded-full bg-[var(--primary)] px-4 text-sm font-semibold text-[var(--primary-foreground)]"
            >
              Search
            </button>
          </form>

          <div className="hidden lg:block">
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[var(--layout-max)] px-4 py-6 md:px-6 xl:px-8">
        <Link
          href="/marketplace"
          className="inline-flex items-center gap-2 text-sm font-medium text-[var(--text-muted)] transition hover:text-[var(--text)]"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to marketplace
        </Link>

        <section className="mt-6 rounded-[1.5rem] border border-[var(--border)] bg-[var(--surface)] p-5 shadow-[var(--shadow)] sm:p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <span className="app-status-badge" data-tone="accent">
                Natural language search
              </span>
              <h1 className="mt-4 text-3xl font-semibold text-[var(--text)] sm:text-4xl">
                {query ? `${data?.resultCount ?? 0} agents found for ${query}` : "Search agents"}
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--text-muted)]">
                Search results are ranked by task fit, delivery trust, completion history, and agent
                capability overlap.
              </p>
            </div>

            <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3 text-sm text-[var(--text-muted)]">
              Query: {query || "No query"}
            </div>
          </div>
        </section>

        {query ? (
          <section className="mt-4 rounded-[1.5rem] border border-[var(--border)] bg-[var(--surface)] p-5 shadow-[var(--shadow-soft)] sm:p-6">
            <div className="flex items-start gap-4">
              <div className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-[var(--primary-soft)] text-[var(--primary)]">
                <Bot className="h-6 w-6" />
              </div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-semibold text-[var(--text)]">Orchestrator suggestion</p>
                  <Sparkles className="h-4 w-4 text-[var(--primary)]" />
                </div>
                <p className="mt-2 text-sm leading-7 text-[var(--text-muted)]">
                  {searchQuery.isLoading
                    ? "Reading the marketplace and scoring specialist fit."
                    : data?.orchestratorSuggestion}
                </p>
              </div>
            </div>
          </section>
        ) : null}

        <div className="mt-6 space-y-4">
          {searchQuery.isLoading ? (
            <div className="rounded-[1.5rem] border border-[var(--border)] bg-[var(--surface)] p-6 text-sm text-[var(--text-muted)] shadow-[var(--shadow-soft)]">
              <div className="flex items-center gap-3">
                <LoaderCircle className="h-5 w-5 animate-spin text-[var(--primary)]" />
                Searching the agent marketplace
              </div>
            </div>
          ) : null}

          {!query ? (
            <div className="rounded-[1.5rem] border border-[var(--border)] bg-[var(--surface)] p-8 text-center shadow-[var(--shadow-soft)]">
              <Search className="mx-auto h-8 w-8 text-[var(--primary)]" />
              <h2 className="mt-4 text-xl font-semibold text-[var(--text)]">
                Describe the service you need
              </h2>
              <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-[var(--text-muted)]">
                Try a natural language request like “scrape website”, “audit smart contract”, or
                “automate support inbox”.
              </p>
            </div>
          ) : null}

          {!searchQuery.isLoading && query && data?.resultCount === 0 ? (
            <div className="rounded-[1.5rem] border border-[var(--border)] bg-[var(--surface)] p-8 text-center shadow-[var(--shadow-soft)]">
              <SearchX className="mx-auto h-8 w-8 text-[var(--primary)]" />
              <h2 className="mt-4 text-xl font-semibold text-[var(--text)]">No agents found</h2>
              <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-[var(--text-muted)]">
                Try a broader query or name the workflow outcome you want the agent to deliver.
              </p>
            </div>
          ) : null}

          {bestMatch ? (
            <section>
              <ResultCard
                result={bestMatch}
                highlighted
                pending={pendingAgentSlug === bestMatch.agentSlug}
                onHireNow={(result) => void hireNow(result)}
              />
            </section>
          ) : null}

          {otherResults.length > 0 ? (
            <section className="space-y-3">
              <div className="flex items-center justify-between gap-4">
                <h2 className="text-lg font-semibold text-[var(--text)]">Other results</h2>
                <span className="text-sm text-[var(--text-muted)]">
                  {otherResults.length} additional matches
                </span>
              </div>
              {otherResults.map((result) => (
                <ResultCard
                  key={result.agentSlug}
                  result={result}
                  pending={pendingAgentSlug === result.agentSlug}
                  onHireNow={(item) => void hireNow(item)}
                />
              ))}
            </section>
          ) : null}

          {bestMatch ? (
            <Link
              href={`/marketplace?q=${encodeURIComponent(query)}`}
              className="inline-flex h-11 items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 text-sm font-medium text-[var(--text)] shadow-[var(--shadow-soft)] transition hover:bg-[var(--surface-2)]"
            >
              Continue in marketplace browse
              <ArrowRight className="h-4 w-4" />
            </Link>
          ) : null}
        </div>
      </main>
    </div>
  );
}

export function MarketplaceSearchResultsPage() {
  const searchParams = useSearchParams();
  const query = searchParams.get("q")?.trim() ?? "";

  return <MarketplaceSearchResultsContent key={query} query={query} />;
}
