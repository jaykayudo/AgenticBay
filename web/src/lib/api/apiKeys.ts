import type { AxiosResponse } from "axios";

import { authApiClient } from "@/lib/api/client";

export type ApiKeyEnvironment = "SANDBOX" | "PRODUCTION";
export type ApiKeyPermission = "search" | "hire" | "pay" | "check_balance" | "read_history";

export type ApiKeyRecord = {
  id: string;
  name: string;
  key_prefix: string;
  environment: ApiKeyEnvironment;
  permissions: ApiKeyPermission[];
  is_active: boolean;
  expires_at: string | null;
  last_used_at: string | null;
  usage_count: number;
  revoked_at: string | null;
  revoked_reason: string | null;
  created_at: string;
  updated_at: string;
};

export type ApiKeyCreatePayload = {
  name: string;
  environment: ApiKeyEnvironment;
  permissions?: ApiKeyPermission[];
  expires_in_days?: number | null;
};

export type ApiKeyUpdatePayload = {
  name?: string;
  permissions?: ApiKeyPermission[];
};

export type ApiKeyCreatedResponse = ApiKeyRecord & {
  key: string;
  warning: string;
};

export type ApiKeyUsageDay = {
  date: string;
  count: number;
};

export type ApiKeyUsage = {
  key_id: string;
  name: string;
  usage_count: number;
  last_used_at: string | null;
  last_used_ip: string | null;
  last_used_user_agent: string | null;
  daily_usage: ApiKeyUsageDay[];
  recent_events: Array<{
    action: string;
    ip_address: string | null;
    created_at: string;
  }>;
};

export const apiKeysApi = {
  list(): Promise<AxiosResponse<ApiKeyRecord[]>> {
    return authApiClient.get("/keys");
  },

  get(id: string): Promise<AxiosResponse<ApiKeyRecord>> {
    return authApiClient.get(`/keys/${encodeURIComponent(id)}`);
  },

  create(data: ApiKeyCreatePayload): Promise<AxiosResponse<ApiKeyCreatedResponse>> {
    return authApiClient.post("/keys", data);
  },

  update(id: string, data: ApiKeyUpdatePayload): Promise<AxiosResponse<ApiKeyRecord>> {
    return authApiClient.patch(`/keys/${encodeURIComponent(id)}`, data);
  },

  revoke(id: string, reason?: string): Promise<AxiosResponse<void>> {
    return authApiClient.delete(`/keys/${encodeURIComponent(id)}`, {
      data: { reason: reason || null },
    });
  },

  rotate(id: string): Promise<AxiosResponse<ApiKeyCreatedResponse>> {
    return authApiClient.post(`/keys/${encodeURIComponent(id)}/rotate`);
  },

  getUsage(id: string): Promise<AxiosResponse<ApiKeyUsage>> {
    return authApiClient.get(`/keys/${encodeURIComponent(id)}/usage`);
  },
};
