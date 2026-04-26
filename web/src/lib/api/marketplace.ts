import type { AxiosResponse } from "axios";

import { apiClient } from "@/lib/api/client";
import {
  marketplaceCategories,
  marketplaceSpeedOptions,
  type MarketplaceAgent,
  type MarketplaceAgentDetail,
  type MarketplaceCategory,
  type MarketplaceCategorySlug,
  type MarketplaceSpeedKey,
} from "@/lib/marketplace-data";

export interface AgentListFilters {
  category?: string;
  min_rating?: number;
  max_price?: number;
  speed?: string;
  sort?: "relevance" | "rating" | "price_asc" | "price_desc" | "jobs";
  q?: string;
  page?: number;
  page_size?: number;
}

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
};

export type MarketplaceStats = {
  totalAgents: number;
  totalVolume: number;
  totalJobs: number;
};

export type SearchResult = {
  agentSlug: string;
  agentName: string;
  description: string;
  rating: number;
  jobsCompleted: number;
  startingPriceUsdc: number;
  matchPercentage: number;
  reason: string;
  primaryAction: {
    actionId: string;
    actionName: string;
    priceUsdc: number;
    estimatedDurationLabel: string;
    inputSummary: string;
    mode: "hire" | "demo";
  };
  avatar: MarketplaceAgent["avatar"];
};

export type SearchResponse = {
  query: string;
  generatedAt: string;
  resultCount: number;
  orchestratorSuggestion: string;
  bestMatch: SearchResult | null;
  results: SearchResult[];
};

type RawPaginationMeta = {
  total: number;
  page: number;
  pageSize?: number;
  page_size?: number;
  hasNext?: boolean;
  has_next?: boolean;
};

type RawAgent = {
  id: string;
  slug: string;
  name: string;
  description: string;
  categories: string[];
  tags: string[];
  avgRating?: number | string;
  totalJobs?: number;
  successRate?: number | string;
  startingPriceUsdc?: number | string | null;
  avgDurationSec?: number | string | null;
  actions?: Array<{
    id: string;
    name: string;
    description: string;
    priceUsdc?: number | string | null;
  }>;
};

type RawAgentListResponse = {
  items: RawAgent[];
  meta: RawPaginationMeta;
};

type RawSearchResponse = {
  query: string;
  enrichedQuery: string;
  orchestratorSuggestion: string;
  results: Array<{
    agent: RawAgent;
    relevanceScore: number;
    matchReason: string;
  }>;
};

const categoryLabelBySlug = Object.fromEntries(
  marketplaceCategories.map((category) => [category.slug, category.label])
) as Record<string, string>;

function withData<T>(response: AxiosResponse<unknown>, data: T): AxiosResponse<T> {
  return {
    ...response,
    data,
  };
}

function toNumber(value: number | string | null | undefined, fallback = 0) {
  if (value === null || value === undefined) {
    return fallback;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function buildAvatar(name: string): MarketplaceAgent["avatar"] {
  return {
    label: name
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part[0])
      .join("")
      .toUpperCase(),
    bg: "var(--primary-soft)",
    fg: "var(--primary)",
  };
}

function speedFromDuration(seconds: number | string | null | undefined): {
  speedKey: MarketplaceSpeedKey;
  speedLabel: string;
  speedRank: number;
} {
  const duration = toNumber(seconds, 86_400);

  if (duration <= 300) {
    return { speedKey: "instant", speedLabel: "Instant or API", speedRank: 1 };
  }
  if (duration <= 3_600) {
    return { speedKey: "under-1-hour", speedLabel: "Under 1 hour", speedRank: 2 };
  }
  if (duration <= 86_400) {
    return { speedKey: "same-day", speedLabel: "Same day", speedRank: 3 };
  }
  if (duration <= 259_200) {
    return { speedKey: "1-3-days", speedLabel: "1-3 days", speedRank: 4 };
  }
  return { speedKey: "3-7-days", speedLabel: "3-7 days", speedRank: 5 };
}

function normalizeAgent(agent: RawAgent): MarketplaceAgent {
  const speed = speedFromDuration(agent.avgDurationSec);

  return {
    id: agent.id,
    slug: agent.slug,
    name: agent.name,
    description: agent.description,
    categories: agent.categories.filter((category): category is MarketplaceCategorySlug =>
      Boolean(categoryLabelBySlug[category])
    ),
    tags: agent.tags ?? [],
    rating: toNumber(agent.avgRating, 0),
    reviewCount: 0,
    startingPriceUsdc: toNumber(agent.startingPriceUsdc, 0),
    ...speed,
    successRate: toNumber(agent.successRate, 0),
    jobsCompleted: agent.totalJobs ?? 0,
    avatar: buildAvatar(agent.name),
  };
}

function normalizeAgentDetail(agent: RawAgent): MarketplaceAgentDetail {
  const normalized = normalizeAgent(agent);

  return {
    ...normalized,
    headline: `${normalized.name} marketplace specialist`,
    fullDescription: [normalized.description],
    actions:
      agent.actions?.map((action) => ({
        id: action.id,
        name: action.name,
        description: action.description,
        priceUsdc: toNumber(action.priceUsdc, normalized.startingPriceUsdc),
        estimatedDurationHours: Math.max(1, Math.round(normalized.speedRank * 6)),
        estimatedDurationLabel: normalized.speedLabel,
        demoAvailable: false,
      })) ?? [],
    demoActionId: null,
  };
}

function normalizePagination(response: RawAgentListResponse): PaginatedResponse<MarketplaceAgent> {
  return {
    items: response.items.map(normalizeAgent),
    total: response.meta.total,
    page: response.meta.page,
    page_size: response.meta.pageSize ?? response.meta.page_size ?? response.items.length,
    has_next: response.meta.hasNext ?? response.meta.has_next ?? false,
  };
}

function normalizeSearch(response: RawSearchResponse): SearchResponse {
  const results = response.results.map((hit) => {
    const agent = normalizeAgent(hit.agent);
    const firstAction = hit.agent.actions?.[0];

    return {
      agentSlug: agent.slug,
      agentName: agent.name,
      description: agent.description,
      rating: agent.rating,
      jobsCompleted: agent.jobsCompleted,
      startingPriceUsdc: agent.startingPriceUsdc,
      matchPercentage: Math.round(Math.min(Math.max(hit.relevanceScore, 0), 1) * 100),
      reason: hit.matchReason,
      primaryAction: {
        actionId: firstAction?.id ?? "default",
        actionName: firstAction?.name ?? "Start job",
        priceUsdc: toNumber(firstAction?.priceUsdc, agent.startingPriceUsdc),
        estimatedDurationLabel: agent.speedLabel,
        inputSummary: response.query,
        mode: "hire" as const,
      },
      avatar: agent.avatar,
    };
  });

  return {
    query: response.query,
    generatedAt: new Date().toISOString(),
    resultCount: results.length,
    orchestratorSuggestion: response.orchestratorSuggestion,
    bestMatch: results[0] ?? null,
    results,
  };
}

export const marketplaceApi = {
  async listAgents(
    filters: AgentListFilters = {}
  ): Promise<AxiosResponse<PaginatedResponse<MarketplaceAgent>>> {
    const response = await apiClient.get<RawAgentListResponse>("/marketplace/agents", {
      params: filters,
    });
    return withData(response, normalizePagination(response.data));
  },

  async getAgent(agentId: string): Promise<AxiosResponse<MarketplaceAgentDetail>> {
    const response = await apiClient.get<RawAgent>(`/marketplace/agents/${agentId}`);
    return withData(response, normalizeAgentDetail(response.data));
  },

  async search(query: string): Promise<AxiosResponse<SearchResponse>> {
    const response = await apiClient.get<RawSearchResponse>("/marketplace/search", {
      params: { q: query },
    });
    return withData(response, normalizeSearch(response.data));
  },

  async listCategories(): Promise<AxiosResponse<{ categories: MarketplaceCategory[] }>> {
    const response =
      await apiClient.get<Array<{ category: string; agentCount: number }>>(
        "/marketplace/categories"
      );
    const categories = response.data.map((item) => {
      const fallback = marketplaceCategories.find((category) => category.slug === item.category);
      return {
        slug: item.category as MarketplaceCategorySlug,
        label: fallback?.label ?? item.category,
        description: fallback?.description ?? `${item.agentCount} active agents`,
      };
    });
    return withData(response, { categories });
  },

  async featured(): Promise<AxiosResponse<{ agents: MarketplaceAgent[] }>> {
    const response = await apiClient.get<RawAgent[]>("/marketplace/featured");
    return withData(response, { agents: response.data.map(normalizeAgent) });
  },

  stats(): Promise<AxiosResponse<MarketplaceStats>> {
    return apiClient.get<MarketplaceStats>("/marketplace/stats");
  },
};

export { marketplaceSpeedOptions };
export type {
  MarketplaceAgent as Agent,
  MarketplaceAgentDetail as AgentDetail,
  MarketplaceCategory as Category,
};
