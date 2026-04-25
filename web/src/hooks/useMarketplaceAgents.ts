"use client";

import useSWR from "swr";

import {
  marketplaceApi,
  type AgentListFilters,
  type MarketplaceStats,
} from "@/lib/api/marketplace";

function stableFilters(filters: AgentListFilters) {
  return Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== undefined && value !== "")
  ) as AgentListFilters;
}

export function useMarketplaceAgents(filters: AgentListFilters) {
  const normalizedFilters = stableFilters(filters);
  const key = ["/marketplace/agents", JSON.stringify(normalizedFilters)] as const;

  const { data, error, isLoading, mutate } = useSWR(key, () =>
    marketplaceApi.listAgents(normalizedFilters).then((response) => response.data)
  );

  return {
    agents: data?.items ?? [],
    total: data?.total ?? 0,
    page: data?.page ?? normalizedFilters.page ?? 1,
    pageSize: data?.page_size ?? normalizedFilters.page_size ?? 20,
    hasNext: data?.has_next ?? false,
    isLoading,
    error,
    mutate,
  };
}

export function useFeaturedAgents() {
  const { data, error, isLoading, mutate } = useSWR(
    "/marketplace/featured",
    () => marketplaceApi.featured().then((response) => response.data.agents),
    {
      dedupingInterval: 5 * 60 * 1000,
      revalidateOnFocus: false,
    }
  );

  return {
    agents: data ?? [],
    isLoading,
    error,
    mutate,
  };
}

export function useMarketplaceStats() {
  const { data, error, isLoading, mutate } = useSWR<MarketplaceStats>(
    "/marketplace/stats",
    () => marketplaceApi.stats().then((response) => response.data),
    {
      dedupingInterval: Number.POSITIVE_INFINITY,
      revalidateIfStale: false,
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
    }
  );

  return {
    stats: data,
    isLoading,
    error,
    mutate,
  };
}

export function useMarketplaceCategories() {
  const { data, error, isLoading, mutate } = useSWR(
    "/marketplace/categories",
    () => marketplaceApi.listCategories().then((response) => response.data.categories),
    {
      dedupingInterval: 5 * 60 * 1000,
      revalidateOnFocus: false,
    }
  );

  return {
    categories: data ?? [],
    isLoading,
    error,
    mutate,
  };
}
