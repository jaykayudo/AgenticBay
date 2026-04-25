"use client";

import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Command,
  LayoutGrid,
  List,
  Search,
  SlidersHorizontal,
  Star,
  X,
} from "lucide-react";
import Link from "next/link";
import {
  type ReadonlyURLSearchParams,
  usePathname,
  useRouter,
  useSearchParams,
} from "next/navigation";
import { startTransition, useDeferredValue, useEffect, useState } from "react";

import { ThemeToggle } from "@/components/theme-toggle";
import { useMarketplaceAgents } from "@/hooks/useMarketplaceAgents";
import {
  marketplaceCategories,
  marketplaceSortOptions,
  marketplaceSpeedOptions,
  type MarketplaceAgent,
  type MarketplaceCategorySlug,
  type MarketplaceSortKey,
  type MarketplaceSpeedKey,
  type MarketplaceViewMode,
} from "@/lib/marketplace-data";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 9;
const PRICE_MIN = 0;
const PRICE_MAX = 250;
const PRICE_STEP = 25;

const ratingOptions = [
  { value: 0, label: "Any rating" },
  { value: 4, label: "4.0+" },
  { value: 4.5, label: "4.5+" },
  { value: 4.8, label: "4.8+" },
] as const;

const categoryLabelBySlug = Object.fromEntries(
  marketplaceCategories.map((category) => [category.slug, category.label])
) as Record<MarketplaceCategorySlug, string>;

const categorySlugSet = new Set(
  marketplaceCategories.map((category) => category.slug)
) as ReadonlySet<MarketplaceCategorySlug>;

const sortValueSet = new Set(
  marketplaceSortOptions.map((option) => option.value)
) as ReadonlySet<MarketplaceSortKey>;

const speedValueSet = new Set(marketplaceSpeedOptions.map((option) => option.value)) as ReadonlySet<
  MarketplaceSpeedKey | "any"
>;

const ratingValueSet = new Set(ratingOptions.map((option) => option.value)) as ReadonlySet<
  (typeof ratingOptions)[number]["value"]
>;

function formatUsdc(value: number) {
  return `${new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0,
  }).format(value)} USDC`;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function parseNumberParam(value: string | null, fallback: number) {
  if (value === null) return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function parseSelectedCategories(searchParams: ReadonlyURLSearchParams) {
  const rawValues = searchParams
    .getAll("category")
    .flatMap((value) => value.split(","))
    .map((value) => value.trim())
    .filter((value): value is MarketplaceCategorySlug =>
      categorySlugSet.has(value as MarketplaceCategorySlug)
    );

  return Array.from(new Set(rawValues));
}

function getSortValue(value: string | null): MarketplaceSortKey {
  if (value && sortValueSet.has(value as MarketplaceSortKey)) {
    return value as MarketplaceSortKey;
  }
  return "recommended";
}

function getSpeedValue(value: string | null): MarketplaceSpeedKey | "any" {
  if (value && speedValueSet.has(value as MarketplaceSpeedKey | "any")) {
    return value as MarketplaceSpeedKey | "any";
  }
  return "any";
}

function getViewValue(value: string | null): MarketplaceViewMode {
  return value === "list" ? "list" : "grid";
}

function getRatingValue(value: string | null) {
  const parsed = parseNumberParam(value, 0);
  return ratingValueSet.has(parsed as (typeof ratingOptions)[number]["value"]) ? parsed : 0;
}

function toApiSort(sort: MarketplaceSortKey) {
  switch (sort) {
    case "rating":
      return "rating" as const;
    case "reviews":
      return "jobs" as const;
    case "price-low":
      return "price_asc" as const;
    case "price-high":
      return "price_desc" as const;
    case "fastest":
    case "recommended":
    default:
      return "relevance" as const;
  }
}

function buildQueryHref(
  pathname: string,
  searchParams: ReadonlyURLSearchParams,
  updates: Record<string, number | string | string[] | null | undefined>,
  resetPage = false
) {
  const params = new URLSearchParams(searchParams.toString());

  Object.entries(updates).forEach(([key, value]) => {
    if (
      value === null ||
      value === undefined ||
      value === "" ||
      (Array.isArray(value) && value.length === 0)
    ) {
      params.delete(key);
      return;
    }

    params.set(key, Array.isArray(value) ? value.join(",") : String(value));
  });

  if (resetPage) {
    params.delete("page");
  }

  const next = params.toString();
  return next ? `${pathname}?${next}` : pathname;
}

function recommendedScore(agent: MarketplaceAgent, searchTerm: string) {
  const normalizedName = agent.name.toLowerCase();
  const normalizedDescription = agent.description.toLowerCase();
  const searchBonus =
    searchTerm.length > 0
      ? (normalizedName.includes(searchTerm) ? 18 : 0) +
        (normalizedDescription.includes(searchTerm) ? 8 : 0)
      : 0;

  return (
    searchBonus +
    agent.rating * 24 +
    agent.reviewCount * 0.18 +
    agent.successRate * 0.12 +
    (6 - agent.speedRank) * 7 -
    agent.startingPriceUsdc * 0.025
  );
}

function sortAgents(agents: MarketplaceAgent[], sort: MarketplaceSortKey, searchTerm: string) {
  return [...agents].sort((left, right) => {
    switch (sort) {
      case "rating":
        return (
          right.rating - left.rating ||
          right.reviewCount - left.reviewCount ||
          left.startingPriceUsdc - right.startingPriceUsdc
        );
      case "reviews":
        return (
          right.reviewCount - left.reviewCount ||
          right.rating - left.rating ||
          left.startingPriceUsdc - right.startingPriceUsdc
        );
      case "price-low":
        return (
          left.startingPriceUsdc - right.startingPriceUsdc ||
          right.rating - left.rating ||
          left.speedRank - right.speedRank
        );
      case "price-high":
        return (
          right.startingPriceUsdc - left.startingPriceUsdc ||
          right.rating - left.rating ||
          left.speedRank - right.speedRank
        );
      case "fastest":
        return (
          left.speedRank - right.speedRank ||
          right.rating - left.rating ||
          left.startingPriceUsdc - right.startingPriceUsdc
        );
      case "recommended":
      default:
        return (
          recommendedScore(right, searchTerm) - recommendedScore(left, searchTerm) ||
          right.rating - left.rating ||
          right.reviewCount - left.reviewCount
        );
    }
  });
}

function AgentAvatar({ agent }: { agent: MarketplaceAgent }) {
  return (
    <div
      className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl text-sm font-semibold shadow-[var(--shadow-soft)]"
      style={{
        backgroundColor: agent.avatar.bg,
        color: agent.avatar.fg,
      }}
    >
      {agent.avatar.label}
    </div>
  );
}

function AgentCard({ agent, view }: { agent: MarketplaceAgent; view: MarketplaceViewMode }) {
  const categoryLabels = agent.categories.map((slug) => categoryLabelBySlug[slug]);

  if (view === "list") {
    return (
      <article className="app-panel p-5 sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex min-w-0 gap-4">
            <AgentAvatar agent={agent} />

            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-lg font-semibold tracking-[-0.02em] text-[var(--text)]">
                  {agent.name}
                </h2>
                <span className="app-status-badge" data-tone="accent">
                  {agent.speedLabel}
                </span>
              </div>

              <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-[var(--text-muted)]">
                <span className="inline-flex items-center gap-1.5">
                  <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
                  {agent.rating.toFixed(1)}
                </span>
                <span>{agent.reviewCount} reviews</span>
                <span>{agent.successRate.toFixed(1)}% success rate</span>
                <span>{agent.jobsCompleted} jobs completed</span>
              </div>

              <p className="mt-3 line-clamp-2 text-sm leading-7 text-[var(--text-muted)]">
                {agent.description}
              </p>

              <div className="mt-4 flex flex-wrap gap-2">
                {categoryLabels.map((label) => (
                  <span
                    key={`${agent.id}-${label}`}
                    className="rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1 text-xs font-medium text-[var(--text-muted)]"
                  >
                    {label}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div className="flex items-end justify-between gap-4 border-t border-[var(--border)] pt-4 lg:min-w-[220px] lg:flex-col lg:items-end lg:border-t-0 lg:pt-0">
            <div className="text-right">
              <p className="text-xs font-semibold tracking-[0.16em] text-[var(--text-muted)] uppercase">
                Starting at
              </p>
              <p className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[var(--text)]">
                {formatUsdc(agent.startingPriceUsdc)}
              </p>
            </div>

            <Link
              href={`/marketplace/${agent.slug}`}
              className="inline-flex h-11 items-center justify-center rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] transition hover:opacity-90"
            >
              View Agent
            </Link>
          </div>
        </div>
      </article>
    );
  }

  return (
    <article className="app-panel flex h-full flex-col p-5 sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <AgentAvatar agent={agent} />
          <div className="min-w-0">
            <h2 className="truncate text-lg font-semibold tracking-[-0.02em] text-[var(--text)]">
              {agent.name}
            </h2>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-[var(--text-muted)]">
              <span className="inline-flex items-center gap-1.5">
                <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
                {agent.rating.toFixed(1)}
              </span>
              <span>{agent.reviewCount} reviews</span>
            </div>
          </div>
        </div>

        <span className="app-status-badge shrink-0" data-tone="accent">
          {agent.speedLabel}
        </span>
      </div>

      <p className="mt-4 line-clamp-3 text-sm leading-7 text-[var(--text-muted)]">
        {agent.description}
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        {categoryLabels.map((label) => (
          <span
            key={`${agent.id}-${label}`}
            className="rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1 text-xs font-medium text-[var(--text-muted)]"
          >
            {label}
          </span>
        ))}
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3">
        <div className="app-subtle rounded-xl p-3">
          <p className="text-lg font-semibold text-[var(--text)] tabular-nums">
            {agent.successRate.toFixed(1)}%
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

      <div className="mt-auto flex items-end justify-between gap-4 border-t border-[var(--border)] pt-5">
        <div>
          <p className="text-xs font-semibold tracking-[0.16em] text-[var(--text-muted)] uppercase">
            Starting at
          </p>
          <p className="mt-2 text-xl font-semibold tracking-[-0.03em] text-[var(--text)]">
            {formatUsdc(agent.startingPriceUsdc)}
          </p>
        </div>

        <Link
          href={`/marketplace/${agent.slug}`}
          className="inline-flex h-10 items-center justify-center rounded-full bg-[var(--primary)] px-4 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] transition hover:opacity-90"
        >
          View Agent
        </Link>
      </div>
    </article>
  );
}

export function MarketplaceBrowse() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const urlSearch = searchParams.get("q") ?? "";
  const [searchDraft, setSearchDraft] = useState(urlSearch);
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSearchDraft(urlSearch);
  }, [urlSearch]);

  const deferredSearchTerm = useDeferredValue(searchDraft.trim());
  const selectedCategories = parseSelectedCategories(searchParams);
  const minPrice = clamp(
    parseNumberParam(searchParams.get("minPrice"), PRICE_MIN),
    PRICE_MIN,
    PRICE_MAX
  );
  const maxPrice = clamp(
    Math.max(parseNumberParam(searchParams.get("maxPrice"), PRICE_MAX), minPrice),
    PRICE_MIN,
    PRICE_MAX
  );
  const minRating = getRatingValue(searchParams.get("rating"));
  const speedValue = getSpeedValue(searchParams.get("speed"));
  const sortValue = getSortValue(searchParams.get("sort"));
  const viewValue = getViewValue(searchParams.get("view"));
  const pageValue = Math.max(1, parseNumberParam(searchParams.get("page"), 1));
  const speedOption =
    marketplaceSpeedOptions.find((option) => option.value === speedValue) ??
    marketplaceSpeedOptions[0];
  const categoryFilter = selectedCategories[0];
  const marketplaceQuery = useMarketplaceAgents({
    category: categoryFilter,
    min_rating: minRating > 0 ? minRating : undefined,
    max_price: maxPrice < PRICE_MAX ? maxPrice : undefined,
    speed: speedValue !== "any" ? speedValue : undefined,
    sort: toApiSort(sortValue),
    q: deferredSearchTerm || undefined,
    page: pageValue,
    page_size: PAGE_SIZE,
  });

  function updateQuery(
    updates: Record<string, number | string | string[] | null | undefined>,
    resetPage = false
  ) {
    const href = buildQueryHref(pathname, searchParams, updates, resetPage);
    startTransition(() => {
      router.replace(href, { scroll: false });
    });
  }

  const filteredAgents = marketplaceQuery.agents;
  const totalAgents = marketplaceQuery.total;
  const totalPages = Math.max(1, Math.ceil(totalAgents / PAGE_SIZE));
  const currentPage = Math.min(pageValue, totalPages);
  const visibleAgents = filteredAgents;
  const visibleStart = totalAgents === 0 ? 0 : (currentPage - 1) * PAGE_SIZE + 1;
  const visibleEnd = Math.min(currentPage * PAGE_SIZE, totalAgents);

  const activeFilterCount =
    selectedCategories.length +
    Number(searchDraft.trim().length > 0) +
    Number(minPrice > PRICE_MIN || maxPrice < PRICE_MAX) +
    Number(minRating > 0) +
    Number(speedValue !== "any");

  const activeFilterLabels = [
    ...(searchDraft.trim()
      ? [
          {
            key: "search",
            label: `Search: "${searchDraft.trim()}"`,
            onClear: () => {
              setSearchDraft("");
              updateQuery({ q: undefined }, true);
            },
          },
        ]
      : []),
    ...selectedCategories.map((category) => ({
      key: category,
      label: categoryLabelBySlug[category],
      onClear: () =>
        updateQuery(
          {
            category: selectedCategories.filter((value) => value !== category),
          },
          true
        ),
    })),
    ...(minPrice > PRICE_MIN || maxPrice < PRICE_MAX
      ? [
          {
            key: "price",
            label: `${formatUsdc(minPrice)} to ${formatUsdc(maxPrice)}`,
            onClear: () => updateQuery({ minPrice: undefined, maxPrice: undefined }, true),
          },
        ]
      : []),
    ...(minRating > 0
      ? [
          {
            key: "rating",
            label: `${minRating.toFixed(1)}+ rating`,
            onClear: () => updateQuery({ rating: undefined }, true),
          },
        ]
      : []),
    ...(speedValue !== "any"
      ? [
          {
            key: "speed",
            label: speedOption.label,
            onClear: () => updateQuery({ speed: undefined }, true),
          },
        ]
      : []),
  ];

  function clearAllFilters() {
    setSearchDraft("");
    setMobileFiltersOpen(false);
    updateQuery(
      {
        q: undefined,
        category: undefined,
        minPrice: undefined,
        maxPrice: undefined,
        rating: undefined,
        speed: undefined,
      },
      true
    );
  }

  function renderFiltersContent() {
    return (
      <div className="mt-6 space-y-6">
        <section>
          <h3 className="text-sm font-semibold text-[var(--text)]">Categories</h3>
          <div className="mt-3 space-y-2.5">
            {marketplaceCategories.map((category) => {
              const checked = selectedCategories.includes(category.slug);

              return (
                <label
                  key={category.slug}
                  className="flex cursor-pointer items-start gap-3 rounded-2xl border border-transparent px-3 py-2 transition hover:border-[var(--border)] hover:bg-[var(--surface-2)]"
                >
                  <input
                    type="checkbox"
                    className="mt-1 h-4 w-4 rounded accent-[var(--primary)]"
                    checked={checked}
                    onChange={() => {
                      const nextCategories = checked
                        ? selectedCategories.filter((value) => value !== category.slug)
                        : [category.slug];

                      updateQuery({ category: nextCategories }, true);
                    }}
                  />
                  <div>
                    <p className="text-sm font-medium text-[var(--text)]">{category.label}</p>
                    <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
                      {category.description}
                    </p>
                  </div>
                </label>
              );
            })}
          </div>
        </section>

        <section>
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-[var(--text)]">Price range</h3>
            <span className="text-sm text-[var(--text-muted)]">
              {formatUsdc(minPrice)} - {formatUsdc(maxPrice)}
            </span>
          </div>

          <div className="mt-4 space-y-4">
            <div>
              <div className="mb-2 flex items-center justify-between text-xs font-medium tracking-[0.14em] text-[var(--text-muted)] uppercase">
                <span>Minimum</span>
                <span>{formatUsdc(minPrice)}</span>
              </div>
              <input
                type="range"
                min={PRICE_MIN}
                max={PRICE_MAX}
                step={PRICE_STEP}
                value={minPrice}
                onChange={(event) => {
                  const nextMin = Math.min(Number(event.target.value), maxPrice);
                  updateQuery(
                    {
                      minPrice: nextMin > PRICE_MIN ? nextMin : undefined,
                    },
                    true
                  );
                }}
                className="w-full accent-[var(--primary)]"
              />
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between text-xs font-medium tracking-[0.14em] text-[var(--text-muted)] uppercase">
                <span>Maximum</span>
                <span>{formatUsdc(maxPrice)}</span>
              </div>
              <input
                type="range"
                min={PRICE_MIN}
                max={PRICE_MAX}
                step={PRICE_STEP}
                value={maxPrice}
                onChange={(event) => {
                  const nextMax = Math.max(Number(event.target.value), minPrice);
                  updateQuery(
                    {
                      maxPrice: nextMax < PRICE_MAX ? nextMax : undefined,
                    },
                    true
                  );
                }}
                className="w-full accent-[var(--primary)]"
              />
            </div>
          </div>
        </section>

        <section>
          <h3 className="text-sm font-semibold text-[var(--text)]">Minimum rating</h3>
          <div className="mt-3 flex flex-wrap gap-2">
            {ratingOptions.map((option) => (
              <button
                key={option.label}
                type="button"
                onClick={() =>
                  updateQuery(
                    {
                      rating: option.value > 0 ? option.value : undefined,
                    },
                    true
                  )
                }
                className={cn(
                  "rounded-full border px-3 py-2 text-sm font-medium transition",
                  minRating === option.value
                    ? "border-[var(--primary)] bg-[var(--primary-soft)] text-[var(--primary)]"
                    : "border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        </section>

        <section>
          <h3 className="text-sm font-semibold text-[var(--text)]">Estimated speed</h3>
          <div className="mt-3 space-y-2">
            {marketplaceSpeedOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() =>
                  updateQuery(
                    {
                      speed: option.value !== "any" ? option.value : undefined,
                    },
                    true
                  )
                }
                className={cn(
                  "flex w-full items-center justify-between rounded-2xl border px-3 py-3 text-left text-sm transition",
                  speedValue === option.value
                    ? "border-[var(--primary)] bg-[var(--primary-soft)] text-[var(--primary)]"
                    : "border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
                )}
              >
                <span>{option.label}</span>
                {speedValue === option.value ? <span>Selected</span> : null}
              </button>
            ))}
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--foreground)]">
      <header className="sticky top-0 z-40 border-b border-[var(--border)] bg-[color-mix(in_srgb,var(--bg-elevated)_92%,transparent)] backdrop-blur">
        <div className="mx-auto flex max-w-[var(--layout-max)] flex-col gap-4 px-4 py-4 md:px-6 xl:flex-row xl:items-center xl:px-8">
          <div className="flex items-center justify-between gap-3 xl:w-[240px]">
            <Link href="/" className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[var(--primary)] text-white shadow-[var(--shadow-soft)]">
                <Command className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs font-semibold tracking-[0.2em] text-[var(--text-muted)] uppercase">
                  AgenticBay
                </p>
                <p className="mt-1 text-sm text-[var(--text-muted)]">Marketplace browse</p>
              </div>
            </Link>

            <div className="xl:hidden">
              <ThemeToggle />
            </div>
          </div>

          <label className="app-search flex-1">
            <Search className="h-4 w-4 shrink-0" />
            <input
              type="search"
              aria-label="Search agents by name or description"
              placeholder="Search agent name or description"
              value={searchDraft}
              onChange={(event) => {
                const nextValue = event.target.value;
                setSearchDraft(nextValue);
                updateQuery({ q: nextValue.trim() ? nextValue : undefined }, true);
              }}
            />
          </label>

          <div className="flex items-center justify-between gap-3 xl:justify-end">
            <span className="hidden rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--text)] md:inline-flex">
              {totalAgents} agents found
            </span>
            <div className="hidden xl:block">
              <ThemeToggle />
            </div>
            <Link
              href="/login"
              className="inline-flex h-11 items-center justify-center rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 text-sm font-medium text-[var(--text)] shadow-[var(--shadow-soft)] transition hover:bg-[var(--surface-2)]"
            >
              Open workspace
            </Link>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-[var(--layout-max)] px-4 py-6 md:px-6 xl:px-8">
        <section className="app-panel mb-6 p-5 sm:p-6">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <span className="app-status-badge" data-tone="accent">
                Agent marketplace
              </span>
              <h1 className="mt-4 text-[clamp(1.8rem,3vw,2.5rem)] font-semibold tracking-[-0.04em] text-[var(--text)]">
                Discover specialist agents and route work with confidence.
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--text-muted)] sm:text-[15px]">
                Search by name or description, narrow by category, price, rating, and delivery
                speed, then browse the marketplace in the view that fits your workflow.
              </p>
            </div>

            <div className="rounded-[1.4rem] border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3 text-sm text-[var(--text-muted)] shadow-[var(--shadow-soft)]">
              Showing {visibleStart}-{visibleEnd} of {totalAgents} matching agents
            </div>
          </div>
        </section>

        <div className="grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)]">
          <aside className="hidden space-y-4 xl:sticky xl:top-24 xl:block xl:self-start">
            <section className="app-panel p-5">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <SlidersHorizontal className="h-4 w-4 text-[var(--primary)]" />
                  <h2 className="text-lg font-semibold text-[var(--text)]">Filters</h2>
                </div>

                <button
                  type="button"
                  className="text-sm font-medium text-[var(--text-muted)] transition hover:text-[var(--text)]"
                  onClick={clearAllFilters}
                >
                  Clear all
                </button>
              </div>

              {renderFiltersContent()}
            </section>

            <section className="app-panel-soft p-4">
              <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
                Active filters
              </p>
              <p className="mt-3 text-3xl font-semibold tracking-[-0.04em] text-[var(--text)]">
                {activeFilterCount}
              </p>
              <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                Filter state is persisted in the URL, so reloads and shared links keep the same
                marketplace view.
              </p>
            </section>
          </aside>

          <main className="min-w-0 space-y-4">
            <section className="app-panel p-5 xl:hidden">
              <button
                type="button"
                aria-expanded={mobileFiltersOpen}
                aria-controls="marketplace-mobile-filters"
                onClick={() => setMobileFiltersOpen((open) => !open)}
                className="flex w-full items-center justify-between gap-4 text-left"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-[var(--primary-soft)] text-[var(--primary)]">
                    <SlidersHorizontal className="h-5 w-5" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-[var(--text)]">Marketplace filters</p>
                    <p className="mt-1 text-sm text-[var(--text-muted)]">
                      {activeFilterCount > 0
                        ? `${activeFilterCount} active filters applied`
                        : "Category, price, rating, and speed"}
                    </p>
                  </div>
                </div>

                <div className="flex shrink-0 items-center gap-3">
                  {activeFilterCount > 0 ? (
                    <span className="rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1 text-sm text-[var(--text)]">
                      {activeFilterCount}
                    </span>
                  ) : null}
                  <ChevronDown
                    className={cn("h-4 w-4 text-[var(--text-muted)] transition-transform", {
                      "rotate-180": mobileFiltersOpen,
                    })}
                  />
                </div>
              </button>

              {mobileFiltersOpen ? (
                <div
                  id="marketplace-mobile-filters"
                  className="mt-5 border-t border-[var(--border)] pt-5"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <SlidersHorizontal className="h-4 w-4 text-[var(--primary)]" />
                      <h2 className="text-lg font-semibold text-[var(--text)]">Filters</h2>
                    </div>

                    <button
                      type="button"
                      className="text-sm font-medium text-[var(--text-muted)] transition hover:text-[var(--text)]"
                      onClick={clearAllFilters}
                    >
                      Clear all
                    </button>
                  </div>

                  {renderFiltersContent()}
                </div>
              ) : null}
            </section>

            <section className="app-panel p-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <p className="text-sm font-medium text-[var(--text)]">
                    Browse marketplace agents
                  </p>
                  <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
                    Search runs against agent names and descriptions, and filter changes update
                    results instantly without a page reload.
                  </p>
                </div>

                <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                  <label className="flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-sm text-[var(--text-muted)] shadow-[var(--shadow-soft)]">
                    <span>Sort</span>
                    <select
                      value={sortValue}
                      onChange={(event) =>
                        updateQuery({ sort: event.target.value || undefined }, true)
                      }
                      className="bg-transparent font-medium text-[var(--text)] outline-none"
                    >
                      {marketplaceSortOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>

                  <div className="inline-flex items-center rounded-full border border-[var(--border)] bg-[var(--surface)] p-1 shadow-[var(--shadow-soft)]">
                    {[
                      { value: "grid" as const, label: "Grid", icon: LayoutGrid },
                      { value: "list" as const, label: "List", icon: List },
                    ].map((option) => {
                      const Icon = option.icon;

                      return (
                        <button
                          key={option.value}
                          type="button"
                          aria-pressed={viewValue === option.value}
                          onClick={() =>
                            updateQuery(
                              {
                                view: option.value === "grid" ? undefined : option.value,
                              },
                              false
                            )
                          }
                          className={cn(
                            "inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition",
                            viewValue === option.value
                              ? "bg-[var(--surface-2)] text-[var(--text)]"
                              : "text-[var(--text-muted)] hover:text-[var(--text)]"
                          )}
                        >
                          <Icon className="h-4 w-4" />
                          {option.label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                {activeFilterLabels.length > 0 ? (
                  activeFilterLabels.map((filter) => (
                    <button
                      key={filter.key}
                      type="button"
                      onClick={filter.onClear}
                      className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--text)] transition hover:bg-[var(--surface)]"
                    >
                      <span>{filter.label}</span>
                      <X className="h-3.5 w-3.5 text-[var(--text-muted)]" />
                    </button>
                  ))
                ) : (
                  <span className="rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--text-muted)]">
                    No active filters
                  </span>
                )}
              </div>
            </section>

            {marketplaceQuery.isLoading ? (
              <section className="app-panel p-8 text-center sm:p-10">
                <div className="mx-auto h-12 w-12 animate-pulse rounded-2xl bg-[var(--surface-3)]" />
                <h2 className="mt-5 text-2xl font-semibold tracking-[-0.03em] text-[var(--text)]">
                  Loading marketplace agents
                </h2>
                <p className="mx-auto mt-3 max-w-xl text-sm leading-7 text-[var(--text-muted)] sm:text-[15px]">
                  Fetching the latest public marketplace listings for this URL state.
                </p>
              </section>
            ) : totalAgents === 0 ? (
              <section className="app-panel p-8 text-center sm:p-10">
                <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-[var(--primary-soft)] text-[var(--primary)]">
                  <SlidersHorizontal className="h-6 w-6" />
                </div>
                <h2 className="mt-5 text-2xl font-semibold tracking-[-0.03em] text-[var(--text)]">
                  No agents match this search
                </h2>
                <p className="mx-auto mt-3 max-w-xl text-sm leading-7 text-[var(--text-muted)] sm:text-[15px]">
                  Try widening your price range, lowering the rating threshold, or clearing one of
                  the active filters to explore more agents.
                </p>
                <div className="mt-6 flex flex-col items-center justify-center gap-3 sm:flex-row">
                  <button
                    type="button"
                    className="inline-flex h-11 items-center justify-center rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] transition hover:opacity-90"
                    onClick={clearAllFilters}
                  >
                    Clear filters
                  </button>
                  <Link
                    href="/"
                    className="inline-flex h-11 items-center justify-center rounded-full border border-[var(--border)] bg-[var(--surface)] px-5 text-sm font-medium text-[var(--text)] shadow-[var(--shadow-soft)] transition hover:bg-[var(--surface-2)]"
                  >
                    Back to home
                  </Link>
                </div>
              </section>
            ) : (
              <>
                <section
                  className={cn(
                    viewValue === "grid"
                      ? "grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"
                      : "space-y-4"
                  )}
                >
                  {visibleAgents.map((agent) => (
                    <AgentCard key={agent.id} agent={agent} view={viewValue} />
                  ))}
                </section>

                {totalPages > 1 ? (
                  <section className="app-panel flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
                    <p className="text-sm text-[var(--text-muted)]">
                      Page {currentPage} of {totalPages}
                    </p>

                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        disabled={currentPage === 1}
                        onClick={() => updateQuery({ page: currentPage - 1 }, false)}
                        className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 text-sm font-medium text-[var(--text)] shadow-[var(--shadow-soft)] transition hover:bg-[var(--surface-2)] disabled:opacity-40"
                      >
                        <ChevronLeft className="h-4 w-4" />
                        Previous
                      </button>

                      {Array.from({ length: totalPages }, (_, index) => index + 1).map((page) => (
                        <button
                          key={page}
                          type="button"
                          aria-pressed={page === currentPage}
                          onClick={() => updateQuery({ page }, false)}
                          className={cn(
                            "inline-flex h-10 w-10 items-center justify-center rounded-full border text-sm font-medium transition",
                            page === currentPage
                              ? "border-[var(--primary)] bg-[var(--primary)] text-[var(--primary-foreground)]"
                              : "border-[var(--border)] bg-[var(--surface)] text-[var(--text)] hover:bg-[var(--surface-2)]"
                          )}
                        >
                          {page}
                        </button>
                      ))}

                      <button
                        type="button"
                        disabled={currentPage === totalPages}
                        onClick={() => updateQuery({ page: currentPage + 1 }, false)}
                        className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 text-sm font-medium text-[var(--text)] shadow-[var(--shadow-soft)] transition hover:bg-[var(--surface-2)] disabled:opacity-40"
                      >
                        Next
                        <ChevronRight className="h-4 w-4" />
                      </button>
                    </div>
                  </section>
                ) : null}
              </>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
