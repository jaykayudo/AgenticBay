"use client";

import useSWR from "swr";

import { jobsApi, type JobFilters } from "@/lib/api/jobs";

function stableFilters(filters: JobFilters) {
  return Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== undefined && value !== "")
  ) as JobFilters;
}

export function useJobs(filters: JobFilters) {
  const normalized = stableFilters(filters);
  const { data, error, isLoading, mutate } = useSWR(
    ["/jobs", JSON.stringify(normalized)],
    () => jobsApi.listJobs(normalized).then((response) => response.data),
    {
      refreshInterval: 20_000,
    }
  );

  async function cancelJob(jobId: string) {
    await jobsApi.cancelJob(jobId);
    await mutate();
  }

  return {
    jobs: data?.items ?? [],
    total: data?.total ?? 0,
    page: data?.page ?? normalized.page ?? 1,
    pageSize: data?.page_size ?? 20,
    hasNext: data?.has_next ?? false,
    isLoading,
    error,
    refresh: mutate,
    cancelJob,
  };
}
