"use client";

import useSWR from "swr";

import { walletApi, type WalletTransactionType } from "@/lib/api/wallet";

export function useTransactions(page = 1, type?: WalletTransactionType | "all") {
  const normalizedType = type && type !== "all" ? type : undefined;
  const { data, error, isLoading, mutate } = useSWR(
    ["/wallet/transactions", page, normalizedType ?? "all"],
    () => walletApi.listTransactions(page, normalizedType).then((response) => response.data)
  );

  return {
    transactions: data?.items ?? [],
    total: data?.total ?? 0,
    page: data?.page ?? page,
    pageSize: data?.page_size ?? 20,
    hasNext: data?.has_next ?? false,
    isLoading,
    error,
    refresh: mutate,
  };
}

export function useActiveEscrow() {
  const { data, error, isLoading, mutate } = useSWR("/wallet/escrow", () =>
    walletApi.getActiveEscrow().then((response) => response.data.active)
  );

  return {
    active: data ?? [],
    isLoading,
    error,
    refresh: mutate,
  };
}

export function useWalletEarnings() {
  const { data, error, isLoading, mutate } = useSWR("/wallet/earnings", () =>
    walletApi.getEarnings().then((response) => response.data)
  );

  return {
    earnings: data,
    isLoading,
    error,
    refresh: mutate,
  };
}
