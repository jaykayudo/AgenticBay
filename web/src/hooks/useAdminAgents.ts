"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import useSWR from "swr";

import { adminApi } from "@/lib/api/admin";
import { useAuthStore } from "@/store/auth-store";

function isAdminRole(role: string | undefined | null) {
  return role?.toLowerCase() === "admin";
}

export function useAdminGuard() {
  const router = useRouter();
  const hydrate = useAuthStore((state) => state.hydrate);
  const hydrated = useAuthStore((state) => state.hydrated);
  const user = useAuthStore((state) => state.user);
  const isAdmin = isAdminRole(user?.role);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (hydrated && !isAdmin) {
      router.replace("/dashboard");
    }
  }, [hydrated, isAdmin, router]);

  return { hydrated, isAdmin, user };
}

export function usePendingAgents() {
  const guard = useAdminGuard();
  const { data, error, isLoading, mutate } = useSWR(
    guard.isAdmin ? "/admin/agents/pending" : null,
    () => adminApi.pendingAgents().then((response) => response.data)
  );

  const approve = async (agentId: string) => {
    await adminApi.approveAgent(agentId);
    await mutate();
  };

  const reject = async (agentId: string, reason: string) => {
    await adminApi.rejectAgent(agentId, reason);
    await mutate();
  };

  return {
    agents: data?.agents ?? [],
    isLoading,
    error,
    refresh: mutate,
    approve,
    reject,
  };
}

export function useAdminUsers(filters: { status?: string; page?: number } = {}) {
  const guard = useAdminGuard();
  const { data, error, isLoading, mutate } = useSWR(
    guard.isAdmin ? ["/admin/users", JSON.stringify(filters)] : null,
    () => adminApi.listUsers(filters).then((response) => response.data)
  );

  const setStatus = async (userId: string, status: "ACTIVE" | "SUSPENDED" | "BANNED") => {
    await mutate(
      async (current) => {
        const { data: updated } = await adminApi.setUserStatus(userId, status);
        if (!current) {
          return current;
        }
        return {
          ...current,
          items: current.items.map((user) => (user.id === userId ? updated : user)),
        };
      },
      {
        optimisticData: (current) => ({
          ...(current ?? { items: [], total: 0, page: 1, page_size: 50, has_next: false }),
          items: (current?.items ?? []).map((user) =>
            user.id === userId ? { ...user, status } : user
          ),
        }),
        rollbackOnError: true,
        revalidate: true,
      }
    );
  };

  return {
    users: data?.items ?? [],
    total: data?.total ?? 0,
    isLoading,
    error,
    refresh: mutate,
    setStatus,
  };
}

export function useAdminStats() {
  const guard = useAdminGuard();
  const { data, error, isLoading, mutate } = useSWR(guard.isAdmin ? "/admin/stats" : null, () =>
    adminApi.platformStats().then((response) => response.data)
  );

  return { stats: data, isLoading, error, refresh: mutate };
}

export function useAdminJobs(filters: Record<string, unknown> = {}) {
  const guard = useAdminGuard();
  const { data, error, isLoading, mutate } = useSWR(
    guard.isAdmin ? ["/admin/jobs", JSON.stringify(filters)] : null,
    () => adminApi.listAllJobs(filters).then((response) => response.data)
  );

  return {
    jobs: data?.items ?? [],
    total: data?.total ?? 0,
    isLoading,
    error,
    refresh: mutate,
  };
}
