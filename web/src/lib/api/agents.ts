import type { AxiosResponse } from "axios";

import { authApiClient } from "@/lib/api/client";

export type AgentStatus = "PENDING" | "ACTIVE" | "PAUSED" | "REJECTED";
export type AnalyticsRange = "7D" | "30D" | "90D" | "ALL";

export interface AgentActionSubmission {
  name: string;
  description: string;
  inputSchema?: Record<string, unknown>;
  outputSchema?: Record<string, unknown>;
  priceUsdc?: number;
}

export interface AgentSubmission {
  name: string;
  slug?: string;
  description: string;
  base_url: string;
  source_code_url?: string;
  categories: string[];
  tags?: string[];
  pricing_summary: Record<string, number | string>;
  profile_image_url?: string;
  profile_image_data?: string;
  actions?: AgentActionSubmission[];
}

export type Agent = {
  id: string;
  ownerId: string;
  name: string;
  slug: string;
  description: string;
  profileImageUrl: string | null;
  baseUrl: string;
  sourceCodeUrl: string | null;
  status: AgentStatus;
  categories: string[];
  tags: string[];
  walletAddress: string | null;
  circleWalletId: string | null;
  pricingSummary: Record<string, unknown>;
  totalJobs: number;
  successRate: number | string;
  avgRating: number | string;
  totalEarned: number | string;
  createdAt: string;
  updatedAt: string;
};

export type ValidationResult = {
  ok: boolean;
  baseUrl: string;
  testSessionId: string;
  capabilities: Record<string, unknown>;
  invokeResponse: unknown;
};

export type AgentWallet = {
  agentId: string;
  walletAddress: string;
  circleWalletId: string;
};

export type AgentAnalytics = {
  agentId: string;
  agentName: string;
  status: AgentStatus;
  totalJobs: number;
  successRate: number;
  avgRating: number;
  totalEarned: number;
  avgDurationSec: number | null;
};

function toApiPayload(data: Partial<AgentSubmission>) {
  return {
    name: data.name,
    slug: data.slug,
    description: data.description,
    baseUrl: data.base_url,
    sourceCodeUrl: data.source_code_url,
    profileImageUrl: data.profile_image_url,
    profileImageData: data.profile_image_data,
    categories: data.categories,
    tags: data.tags,
    pricingSummary: data.pricing_summary,
    actions: data.actions,
  };
}

export const agentsApi = {
  async myAgents(): Promise<AxiosResponse<{ agents: Agent[] }>> {
    const response = await authApiClient.get<Agent[]>("/agents/mine");
    return { ...response, data: { agents: response.data } };
  },

  submit(data: AgentSubmission): Promise<AxiosResponse<Agent>> {
    return authApiClient.post("/agents", toApiPayload(data));
  },

  validate(baseUrl: string): Promise<AxiosResponse<ValidationResult>> {
    return authApiClient.post("/agents/validate", { baseUrl });
  },

  update(agentId: string, data: Partial<AgentSubmission>): Promise<AxiosResponse<Agent>> {
    return authApiClient.patch(`/agents/${agentId}`, toApiPayload(data));
  },

  delete(agentId: string): Promise<AxiosResponse<void>> {
    return authApiClient.delete(`/agents/${agentId}`);
  },

  setStatus(agentId: string, status: "ACTIVE" | "PAUSED"): Promise<AxiosResponse<Agent>> {
    return authApiClient.patch(`/agents/${agentId}/status`, { status });
  },

  getWallet(agentId: string): Promise<AxiosResponse<AgentWallet>> {
    return authApiClient.get(`/agents/${agentId}/wallet`);
  },

  getAnalytics(agentId: string, range: AnalyticsRange): Promise<AxiosResponse<AgentAnalytics>> {
    return authApiClient.get(`/agents/${agentId}/analytics`, { params: { range } });
  },

  uploadImage(file: File): Promise<AxiosResponse<{ url: string }>> {
    const formData = new FormData();
    formData.append("file", file);
    return authApiClient.post("/agents/upload-image", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};
