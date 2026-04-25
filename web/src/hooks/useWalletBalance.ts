"use client";

import useSWR from "swr";

import { walletApi } from "@/lib/api/wallet";

export function useWalletBalance() {
  const { data, error, mutate, isLoading } = useSWR(
    "/wallet/balance",
    () => walletApi.getBalance().then((response) => response.data),
    {
      refreshInterval: 30_000,
      revalidateOnFocus: true,
    }
  );

  const addressQuery = useSWR("/wallet/address", () =>
    walletApi.getAddress().then((response) => response.data)
  );

  const depositQuery = useSWR(
    data ? "/wallet/deposit-instructions" : null,
    () => walletApi.initiateDeposit().then((response) => response.data),
    {
      revalidateOnFocus: false,
    }
  );

  return {
    balance: Number(data?.balance ?? 0),
    currency: data?.currency ?? "USDC",
    source: data?.source ?? "circle",
    address: addressQuery.data?.address ?? depositQuery.data?.address ?? "",
    walletId: addressQuery.data?.walletId ?? depositQuery.data?.walletId ?? "",
    blockchain: addressQuery.data?.blockchain ?? depositQuery.data?.blockchain ?? "",
    qrData: addressQuery.data?.qrData ?? "",
    depositInstructions: depositQuery.data,
    isLoading: isLoading || addressQuery.isLoading,
    error: error ?? addressQuery.error,
    refresh: mutate,
  };
}
