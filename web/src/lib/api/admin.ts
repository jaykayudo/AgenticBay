import type { AxiosResponse } from "axios";

import type { Agent } from "@/lib/api/agents";
import { authApiClient } from "@/lib/api/client";
import type { Job } from "@/lib/api/jobs";

export type PendingAgent = Agent;

export type AdminUser = {
  id: string;
  email: string;
  username: string | null;
  displayName: string | null;
  role: "BUYER" | "AGENT_OWNER" | "ADMIN" | string;
  status: "ACTIVE" | "SUSPENDED" | "BANNED" | string;
  emailVerified: boolean;
  kycVerified: boolean;
  createdAt: string;
};

export type AgentReviewDetail = {
  agent: Agent;
  owner: AdminUser;
  sourceCodeUrl: string | null;
  reviewNotes: string | null;
  proxyContractAddress: string | null;
};

export type AdminPlatformStats = {
  users: number;
  agents: number;
  pendingAgents: number;
  jobs: number;
  activeJobs: number;
  volumeUsdc: number;
};

export type AdminJob = {
  id: string;
  sessionId: string;
  buyerId: string;
  agentId: string;
  status: string;
  amountUsdc: number | null;
  createdAt: string;
  startedAt: string | null;
  completedAt: string | null;
};

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
};

function pageFromArray<T>(items: T[], page = 1, pageSize = 50): PaginatedResponse<T> {
  return {
    items,
    total: items.length,
    page,
    page_size: pageSize,
    has_next: false,
  };
}

function normalizeStatus(status: "ACTIVE" | "SUSPENDED" | "BANNED") {
  return status.toUpperCase();
}

export const adminApi = {
  async pendingAgents(): Promise<AxiosResponse<{ agents: PendingAgent[] }>> {
    const response = await authApiClient.get<PendingAgent[]>("/admin/agents/pending");
    return { ...response, data: { agents: response.data } };
  },

  reviewAgent(agentId: string): Promise<AxiosResponse<AgentReviewDetail>> {
    return authApiClient.get(`/admin/agents/${agentId}/review`);
  },

  approveAgent(agentId: string): Promise<AxiosResponse<Agent>> {
    return authApiClient.patch(`/admin/agents/${agentId}/approve`);
  },

  rejectAgent(agentId: string, reason: string): Promise<AxiosResponse<Agent>> {
    return authApiClient.patch(`/admin/agents/${agentId}/reject`, { reason });
  },

  async listUsers(
    filters: { status?: string; page?: number; limit?: number } = {}
  ): Promise<AxiosResponse<PaginatedResponse<AdminUser>>> {
    const limit = filters.limit ?? 50;
    const page = filters.page ?? 1;
    const response = await authApiClient.get<AdminUser[]>("/admin/users", {
      params: {
        status: filters.status,
        limit,
        offset: (page - 1) * limit,
      },
    });
    return { ...response, data: pageFromArray(response.data, page, limit) };
  },

  setUserStatus(
    userId: string,
    status: "ACTIVE" | "SUSPENDED" | "BANNED"
  ): Promise<AxiosResponse<AdminUser>> {
    return authApiClient.patch(`/admin/users/${userId}/status`, {
      status: normalizeStatus(status),
    });
  },

  platformStats(): Promise<AxiosResponse<AdminPlatformStats>> {
    return authApiClient.get("/admin/stats");
  },

  async listAllJobs(
    filters: Record<string, unknown> = {}
  ): Promise<AxiosResponse<PaginatedResponse<AdminJob | Job>>> {
    const limit = typeof filters.limit === "number" ? filters.limit : 50;
    const page = typeof filters.page === "number" ? filters.page : 1;
    const response = await authApiClient.get<AdminJob[]>("/admin/jobs", {
      params: {
        ...filters,
        limit,
        offset: (page - 1) * limit,
      },
    });
    return { ...response, data: pageFromArray(response.data, page, limit) };
  },
};
