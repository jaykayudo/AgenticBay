import type { AxiosResponse } from "axios";

import { authApiClient } from "@/lib/api/client";

export type WalletTransactionType =
  | "deposit"
  | "withdrawal"
  | "job_payment"
  | "fee"
  | "earning"
  | "refund";

export type WalletTransactionStatus = "pending" | "completed" | "failed" | "locked";

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
};

export type WalletBalance = {
  balance: number;
  currency: string;
  source: string;
};

export type WalletAddress = {
  walletId: string;
  address: string;
  blockchain: string;
  qrData: string;
};

export type DepositInstructions = {
  walletId: string;
  address: string;
  blockchain: string;
  currency: string;
  instructions: string;
};

export type WalletTransaction = {
  id: string;
  transactionType: WalletTransactionType;
  direction: "inbound" | "outbound";
  amount: number;
  signedAmount: number;
  currency: string;
  status: WalletTransactionStatus;
  circleTransferId: string | null;
  onchainTxHash: string | null;
  fromAddress: string | null;
  toAddress: string | null;
  description: string | null;
  txMetadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
};

export type WithdrawResponse = WalletTransaction;

export type EscrowEntry = {
  invoiceId: string;
  jobId: string;
  agentId: string;
  agentName: string | null;
  lockedAmount: number;
  currency: string;
  status: string;
  createdAt: string;
};

export type EarningsSummary = {
  totalEarned: number;
  items: WalletTransaction[];
  meta: {
    total: number;
    page: number;
    pageSize: number;
    hasNext: boolean;
  };
};

type RawPaginatedResponse<T> = {
  items: T[];
  meta: {
    total: number;
    page: number;
    pageSize?: number;
    page_size?: number;
    hasNext?: boolean;
    has_next?: boolean;
  };
};

type RawWalletTransaction = Omit<WalletTransaction, "transactionType" | "status"> & {
  transactionType: string;
  status: string;
};

function normalizeTransactionType(type: string): WalletTransactionType {
  const normalized = type.toLowerCase();
  if (normalized === "job_payment") return "job_payment";
  if (normalized === "fee") return "fee";
  if (normalized === "earning") return "earning";
  if (normalized === "refund") return "refund";
  if (normalized === "withdrawal") return "withdrawal";
  return "deposit";
}

function normalizeStatus(status: string): WalletTransactionStatus {
  const normalized = status.toLowerCase();
  if (normalized === "confirmed") return "completed";
  if (normalized === "initiated") return "pending";
  if (normalized === "refunded") return "completed";
  if (normalized === "failed") return "failed";
  return "pending";
}

function normalizeTransaction(tx: RawWalletTransaction): WalletTransaction {
  return {
    ...tx,
    transactionType: normalizeTransactionType(tx.transactionType),
    status: normalizeStatus(tx.status),
    amount: Number(tx.amount),
    signedAmount: Number(tx.signedAmount),
  };
}

function normalizeEscrow(entry: EscrowEntry): EscrowEntry {
  return {
    ...entry,
    lockedAmount: Number(entry.lockedAmount),
  };
}

function normalizePage<TInput, TOutput>(
  response: RawPaginatedResponse<TInput>,
  normalize: (item: TInput) => TOutput
): PaginatedResponse<TOutput> {
  return {
    items: response.items.map(normalize),
    total: response.meta.total,
    page: response.meta.page,
    page_size: response.meta.pageSize ?? response.meta.page_size ?? response.items.length,
    has_next: response.meta.hasNext ?? response.meta.has_next ?? false,
  };
}

export const walletApi = {
  getBalance(): Promise<AxiosResponse<WalletBalance>> {
    return authApiClient.get("/wallet/balance");
  },

  getAddress(): Promise<AxiosResponse<WalletAddress>> {
    return authApiClient.get("/wallet/address");
  },

  initiateDeposit(): Promise<AxiosResponse<DepositInstructions>> {
    return authApiClient.post("/wallet/deposit");
  },

  withdraw(amount: number, toAddress: string): Promise<AxiosResponse<WithdrawResponse>> {
    return authApiClient.post("/wallet/withdraw", {
      amount,
      toAddress,
    });
  },

  async listTransactions(
    page = 1,
    type?: string
  ): Promise<AxiosResponse<PaginatedResponse<WalletTransaction>>> {
    const response = await authApiClient.get<RawPaginatedResponse<RawWalletTransaction>>(
      "/wallet/transactions",
      { params: { page, type: type?.toUpperCase() } }
    );
    return {
      ...response,
      data: normalizePage(response.data, normalizeTransaction),
    };
  },

  async getTransaction(txId: string): Promise<AxiosResponse<WalletTransaction>> {
    const response = await authApiClient.get<RawWalletTransaction>(`/wallet/transactions/${txId}`);
    return { ...response, data: normalizeTransaction(response.data) };
  },

  async getActiveEscrow(): Promise<AxiosResponse<{ active: EscrowEntry[] }>> {
    const response = await authApiClient.get<EscrowEntry[]>("/wallet/escrow");
    return {
      ...response,
      data: { active: response.data.map(normalizeEscrow) },
    };
  },

  async getEarnings(): Promise<AxiosResponse<EarningsSummary>> {
    const response = await authApiClient.get<
      Omit<EarningsSummary, "items"> & { items: RawWalletTransaction[] }
    >("/wallet/earnings");
    return {
      ...response,
      data: {
        ...response.data,
        totalEarned: Number(response.data.totalEarned),
        items: response.data.items.map(normalizeTransaction),
      },
    };
  },
};
