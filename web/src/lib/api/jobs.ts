import type { AxiosResponse } from "axios";

import { apiFetch } from "@/lib/api";
import { authApiClient } from "@/lib/api/client";

export interface JobFilters {
  status?: "ACTIVE" | "COMPLETED" | "FAILED" | "ALL";
  agent_id?: string;
  date_from?: string;
  date_to?: string;
  min_amount?: number;
  max_amount?: number;
  page?: number;
}

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
};

export type JobStatus = "ACTIVE" | "COMPLETED" | "FAILED" | "CANCELLED";

export type Job = {
  id: string;
  sessionId: string;
  agentId: string;
  agentSlug: string;
  agentName: string;
  actionId: string;
  actionName: string;
  inputSummary: string;
  status: JobStatus;
  amountUsdc: number;
  amountLockedUsdc: number;
  durationLabel: string;
  createdAt: string;
  redirectPath: string;
  mode: "hire" | "demo";
  rehirePayload: {
    actionId: string;
    actionName: string;
    priceUsdc: number;
    estimatedDurationLabel: string;
    inputSummary: string;
    mode: "hire" | "demo";
  };
};

export type JobDetail = Job & {
  messages?: Message[];
};

export type Message = {
  id: string;
  sender: string;
  body: string;
  createdAt: string;
};

export type StartSessionResponse = {
  session_id: string;
  token: string;
  ws_url: string;
};

type BuyerJobHistoryRecord = {
  sessionId: string;
  agentSlug: string;
  agentName: string;
  actionId: string;
  actionName: string;
  inputSummary: string;
  status: "active" | "completed" | "failed";
  amountChargedUsdc: number;
  amountLockedUsdc: number;
  durationLabel: string;
  createdAt: string;
  redirectPath: string;
  mode: "hire" | "demo";
  rehirePayload: Job["rehirePayload"];
};

type BuyerJobHistoryResponse = {
  jobs: BuyerJobHistoryRecord[];
};

function normalizeStatus(status: BuyerJobHistoryRecord["status"]): JobStatus {
  if (status === "completed") return "COMPLETED";
  if (status === "failed") return "FAILED";
  return "ACTIVE";
}

function normalizeJob(job: BuyerJobHistoryRecord): Job {
  return {
    id: job.sessionId,
    sessionId: job.sessionId,
    agentId: job.agentSlug,
    agentSlug: job.agentSlug,
    agentName: job.agentName,
    actionId: job.actionId,
    actionName: job.actionName,
    inputSummary: job.inputSummary,
    status: normalizeStatus(job.status),
    amountUsdc: job.amountChargedUsdc,
    amountLockedUsdc: job.amountLockedUsdc,
    durationLabel: job.durationLabel,
    createdAt: job.createdAt,
    redirectPath: job.redirectPath,
    mode: job.mode,
    rehirePayload: job.rehirePayload,
  };
}

function applyFilters(jobs: Job[], filters: JobFilters) {
  return jobs.filter((job) => {
    const createdAt = new Date(job.createdAt);
    const matchesStatus =
      !filters.status || filters.status === "ALL" || job.status === filters.status;
    const matchesAgent = !filters.agent_id || job.agentId === filters.agent_id;
    const matchesFrom = !filters.date_from || createdAt >= new Date(filters.date_from);
    const matchesTo = !filters.date_to || createdAt <= new Date(filters.date_to);
    const matchesMin = filters.min_amount === undefined || job.amountUsdc >= filters.min_amount;
    const matchesMax = filters.max_amount === undefined || job.amountUsdc <= filters.max_amount;

    return matchesStatus && matchesAgent && matchesFrom && matchesTo && matchesMin && matchesMax;
  });
}

async function fallbackListJobs(filters: JobFilters): Promise<PaginatedResponse<Job>> {
  const response = await apiFetch<BuyerJobHistoryResponse>("/buyer/jobs/history");
  const filtered = applyFilters(response.jobs.map(normalizeJob), filters);
  const page = filters.page ?? 1;
  const pageSize = 20;
  const offset = (page - 1) * pageSize;

  return {
    items: filtered.slice(offset, offset + pageSize),
    total: filtered.length,
    page,
    page_size: pageSize,
    has_next: offset + pageSize < filtered.length,
  };
}

export const jobsApi = {
  async listJobs(filters: JobFilters = {}): Promise<AxiosResponse<PaginatedResponse<Job>>> {
    try {
      const response = await authApiClient.get<PaginatedResponse<Job>>("/jobs", {
        params: filters,
      });
      return response;
    } catch {
      return {
        data: await fallbackListJobs(filters),
        status: 200,
        statusText: "OK",
        headers: {},
        config: {} as AxiosResponse["config"],
      };
    }
  },

  async getJob(jobId: string): Promise<AxiosResponse<JobDetail>> {
    const jobs = await fallbackListJobs({ status: "ALL" });
    const job = jobs.items.find((item) => item.id === jobId || item.sessionId === jobId);
    if (!job) {
      throw new Error("Job not found.");
    }
    return {
      data: { ...job, messages: [] },
      status: 200,
      statusText: "OK",
      headers: {},
      config: {} as AxiosResponse["config"],
    };
  },

  cancelJob(jobId: string): Promise<AxiosResponse<void>> {
    return authApiClient.post(`/jobs/${jobId}/cancel`);
  },

  async getMessages(jobId: string): Promise<AxiosResponse<{ messages: Message[] }>> {
    try {
      return await authApiClient.get(`/jobs/${jobId}/messages`);
    } catch {
      return {
        data: { messages: [] },
        status: 200,
        statusText: "OK",
        headers: {},
        config: {} as AxiosResponse["config"],
      };
    }
  },

  startExternalSession(apiKey: string): Promise<AxiosResponse<StartSessionResponse>> {
    return authApiClient.post(
      "/sessions",
      {},
      {
        headers: { "x-api-key": apiKey },
      }
    );
  },
};
