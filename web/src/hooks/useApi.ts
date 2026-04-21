"use client";

import { useMutation, useQuery, type UseQueryOptions } from "@tanstack/react-query";
import type { AxiosRequestConfig } from "axios";

import { apiFetch } from "@/lib/api";

export function useApiQuery<T>(
  queryKey: unknown[],
  path: string,
  options?: Omit<UseQueryOptions<T>, "queryKey" | "queryFn">
) {
  return useQuery<T>({
    queryKey,
    queryFn: () => apiFetch<T>(path),
    ...options,
  });
}

export function useApiMutation<TData, TVariables>(
  path: string,
  method: "post" | "put" | "patch" | "delete" = "post",
  config?: AxiosRequestConfig
) {
  return useMutation<TData, Error, TVariables>({
    mutationFn: (variables) => apiFetch<TData>(path, { method, data: variables, ...config }),
  });
}
