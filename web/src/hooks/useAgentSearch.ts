"use client";

import useSWR from "swr";

import { marketplaceApi, type SearchResponse } from "@/lib/api/marketplace";

export function useAgentSearch(query: string) {
  const normalizedQuery = query.trim();
  const key = normalizedQuery ? ["/marketplace/search", normalizedQuery] : null;

  const { data, error, isLoading, mutate } = useSWR<SearchResponse>(key, () =>
    marketplaceApi.search(normalizedQuery).then((response) => response.data)
  );

  return {
    query: data?.query ?? normalizedQuery,
    results: data?.results ?? [],
    bestMatch: data?.bestMatch ?? null,
    orchestratorSuggestion: data?.orchestratorSuggestion,
    resultCount: data?.resultCount ?? 0,
    generatedAt: data?.generatedAt,
    isLoading,
    error,
    mutate,
  };
}
