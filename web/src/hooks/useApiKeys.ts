"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiKeysApi, type ApiKeyCreatePayload, type ApiKeyUpdatePayload } from "@/lib/api/apiKeys";

export const apiKeysQueryKey = ["api-keys"] as const;

export function useApiKeys() {
  const queryClient = useQueryClient();

  const keysQuery = useQuery({
    queryKey: apiKeysQueryKey,
    queryFn: async () => {
      const { data } = await apiKeysApi.list();
      return data;
    },
  });

  const refreshKeys = () => queryClient.invalidateQueries({ queryKey: apiKeysQueryKey });

  const createKey = useMutation({
    mutationFn: async (payload: ApiKeyCreatePayload) => {
      const { data } = await apiKeysApi.create(payload);
      return data;
    },
    onSuccess: refreshKeys,
  });

  const updateKey = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: ApiKeyUpdatePayload }) => {
      const response = await apiKeysApi.update(id, data);
      return response.data;
    },
    onSuccess: refreshKeys,
  });

  const revokeKey = useMutation({
    mutationFn: async ({ id, reason }: { id: string; reason?: string }) => {
      await apiKeysApi.revoke(id, reason);
    },
    onSuccess: refreshKeys,
  });

  const rotateKey = useMutation({
    mutationFn: async (id: string) => {
      const { data } = await apiKeysApi.rotate(id);
      return data;
    },
    onSuccess: refreshKeys,
  });

  return {
    keysQuery,
    createKey,
    updateKey,
    revokeKey,
    rotateKey,
  };
}

export function useApiKeyUsage(keyId: string | null) {
  return useQuery({
    queryKey: ["api-key-usage", keyId],
    enabled: Boolean(keyId),
    queryFn: async () => {
      if (!keyId) {
        throw new Error("API key id is required.");
      }
      const { data } = await apiKeysApi.getUsage(keyId);
      return data;
    },
  });
}
