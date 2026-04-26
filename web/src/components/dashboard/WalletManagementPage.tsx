"use client";

import {
  ArrowDownLeft,
  ArrowUpRight,
  Check,
  ChevronLeft,
  ChevronRight,
  Copy,
  Download,
  ExternalLink,
  LoaderCircle,
  QrCode,
  Send,
  Wallet,
  X,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useState, type ReactNode } from "react";

import { useTransactions, useActiveEscrow, useWalletEarnings } from "@/hooks/useTransactions";
import { useWalletBalance } from "@/hooks/useWalletBalance";
import { isApiError } from "@/lib/api/errors";
import { walletApi, type WalletTransactionType } from "@/lib/api/wallet";
import { cn } from "@/lib/utils";

type WalletTab = "transactions" | "escrow" | "earnings";

type WalletTransactionRecord = {
  id: string;
  direction: "inbound" | "outbound";
  type: WalletTransactionType;
  label: string;
  amountUsdc: number;
  timestamp: string;
  status: string;
  jobId?: string;
  jobTitle?: string;
  agentName?: string;
  counterparty?: string;
};

type WalletEscrowRecord = {
  id: string;
  jobId: string;
  jobTitle: string;
  agentName: string;
  amountLockedUsdc: number;
  status: string;
  lockedAt: string;
};

type WalletEarningRecord = {
  id: string;
  agentSlug: string;
  agentName: string;
  sourceJobId: string;
  sourceJobTitle: string;
  amountUsdc: number;
  timestamp: string;
  status: "paid" | "pending";
};

type WalletActivityResponse = {
  tab: WalletTab;
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  items: Array<WalletTransactionRecord | WalletEscrowRecord | WalletEarningRecord>;
};

type WalletModal = "deposit" | "withdraw" | null;

const PAGE_SIZE = 8;
const USD_RATE = 1;

const tabOptions: Array<{ value: WalletTab; label: string }> = [
  { value: "transactions", label: "Transactions" },
  { value: "escrow", label: "Escrow" },
  { value: "earnings", label: "Earnings" },
];

const transactionTypeOptions: Array<{ value: WalletTransactionType | "all"; label: string }> = [
  { value: "all", label: "All types" },
  { value: "deposit", label: "Deposits" },
  { value: "withdrawal", label: "Withdrawals" },
  { value: "job_payment", label: "Job payments" },
  { value: "fee", label: "Fees" },
  { value: "earning", label: "Earnings" },
  { value: "refund", label: "Refunds" },
];

const wholeNumberFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 0,
});

const preciseNumberFormatter = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const dateTimeFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

function formatUsdc(value: number, precise = false) {
  const formatter = precise ? preciseNumberFormatter : wholeNumberFormatter;
  return `${formatter.format(value)} USDC`;
}

function formatUsd(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function shortAddress(address: string) {
  if (address.length <= 18) {
    return address;
  }

  return `${address.slice(0, 8)}...${address.slice(-6)}`;
}

function transactionTypeLabel(type: WalletTransactionRecord["type"]) {
  const labels: Record<WalletTransactionRecord["type"], string> = {
    deposit: "Deposit",
    withdrawal: "Withdrawal",
    job_payment: "Job payment",
    fee: "Fee",
    earning: "Earning",
    refund: "Refund",
  };

  return labels[type];
}

function isTransactionRecord(
  item: WalletActivityResponse["items"][number]
): item is WalletTransactionRecord {
  return "direction" in item;
}

function isEscrowRecord(item: WalletActivityResponse["items"][number]): item is WalletEscrowRecord {
  return "amountLockedUsdc" in item;
}

function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/45 px-4 py-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <section className="app-panel w-full max-w-xl p-5 sm:p-6">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-lg font-semibold text-[var(--text)]">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="grid h-10 w-10 place-items-center rounded-full border border-[var(--border)] text-[var(--text-muted)] transition hover:text-[var(--text)]"
            aria-label="Close modal"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}

function AddressQr({ value }: { value: string }) {
  const cells = useMemo(
    () =>
      Array.from({ length: 121 }, (_, index) => {
        const code = value.charCodeAt(index % value.length);
        return (code + index * 7) % 5 !== 0;
      }),
    [value]
  );

  return (
    <div
      className="grid aspect-square w-40 grid-cols-11 gap-1 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-3 shadow-[var(--shadow-soft)]"
      aria-label="Wallet address QR code"
    >
      {cells.map((filled, index) => (
        <span
          key={index}
          className={cn("rounded-[2px]", filled ? "bg-[var(--text)]" : "bg-transparent")}
        />
      ))}
    </div>
  );
}

function EmptyState({ label }: { label: string }) {
  return <div className="app-subtle p-6 text-sm leading-6 text-[var(--text-muted)]">{label}</div>;
}

function TransactionRow({ item }: { item: WalletTransactionRecord }) {
  const inbound = item.direction === "inbound";
  const Icon = inbound ? ArrowDownLeft : ArrowUpRight;

  return (
    <article className="flex flex-col gap-4 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 items-start gap-3">
        <div
          className={cn(
            "grid h-11 w-11 shrink-0 place-items-center rounded-2xl",
            inbound
              ? "bg-[var(--accent-soft)] text-[var(--accent)]"
              : "bg-[var(--danger-soft)] text-[var(--danger)]"
          )}
        >
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <p className="font-medium text-[var(--text)]">{item.label}</p>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-[var(--text-muted)]">
            <span>{transactionTypeLabel(item.type)}</span>
            <span>{dateTimeFormatter.format(new Date(item.timestamp))}</span>
            {item.agentName ? <span>{item.agentName}</span> : null}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between gap-4 sm:block sm:text-right">
        <p
          className={cn(
            "text-lg font-semibold tabular-nums",
            inbound ? "text-[var(--accent)]" : "text-[var(--text)]"
          )}
        >
          {inbound ? "+" : "-"}
          {formatUsdc(item.amountUsdc, true)}
        </p>
        <span
          className="app-status-badge mt-0 sm:mt-2"
          data-tone={item.status === "locked" ? "default" : "accent"}
        >
          {item.status}
        </span>
      </div>
    </article>
  );
}

function EscrowRow({ item }: { item: WalletEscrowRecord }) {
  return (
    <article className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="font-medium text-[var(--text)]">{item.jobTitle}</p>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            {item.agentName} / locked {dateTimeFormatter.format(new Date(item.lockedAt))}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-lg font-semibold text-[var(--text)] tabular-nums">
            {formatUsdc(item.amountLockedUsdc, true)}
          </span>
          <span className="app-status-badge" data-tone="default">
            {item.status.replace("_", " ")}
          </span>
          <Link
            href={`/jobs/${item.jobId}`}
            className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text-muted)] transition hover:text-[var(--text)]"
          >
            Open job
            <ExternalLink className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </article>
  );
}

function EarningRow({ item }: { item: WalletEarningRecord }) {
  return (
    <article className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="font-medium text-[var(--text)]">{item.agentName}</p>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            {item.sourceJobTitle} / {dateTimeFormatter.format(new Date(item.timestamp))}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-lg font-semibold text-[var(--accent)] tabular-nums">
            +{formatUsdc(item.amountUsdc, true)}
          </span>
          <span
            className="app-status-badge"
            data-tone={item.status === "paid" ? "accent" : "default"}
          >
            {item.status}
          </span>
          <Link
            href={`/dashboard/owner/agents/${item.agentSlug}/analytics`}
            className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text-muted)] transition hover:text-[var(--text)]"
          >
            Agent
            <ExternalLink className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </article>
  );
}

export function WalletManagementPage() {
  const [activeTab, setActiveTab] = useState<WalletTab>("transactions");
  const [transactionType, setTransactionType] = useState<WalletTransactionType | "all">("all");
  const [page, setPage] = useState(1);
  const [modal, setModal] = useState<WalletModal>(null);
  const [copied, setCopied] = useState(false);
  const [showQr, setShowQr] = useState(false);
  const [withdrawAddress, setWithdrawAddress] = useState("");
  const [withdrawAmount, setWithdrawAmount] = useState("");
  const [withdrawConfirmed, setWithdrawConfirmed] = useState(false);
  const [withdrawError, setWithdrawError] = useState<string | null>(null);
  const [isWithdrawing, setIsWithdrawing] = useState(false);

  const wallet = useWalletBalance();
  const transactionsQuery = useTransactions(page, transactionType);
  const escrowQuery = useActiveEscrow();
  const earningsQuery = useWalletEarnings();
  const walletAddress = wallet.address;
  const availableBalanceUsdc = wallet.balance;
  const usdEquivalent = availableBalanceUsdc * USD_RATE;
  const lockedInEscrowUsdc = escrowQuery.active.reduce(
    (total, item) => total + item.lockedAmount,
    0
  );

  const activity = useMemo<WalletActivityResponse>(() => {
    if (activeTab === "transactions") {
      return {
        tab: activeTab,
        page: transactionsQuery.page,
        pageSize: transactionsQuery.pageSize,
        totalItems: transactionsQuery.total,
        totalPages: Math.max(1, Math.ceil(transactionsQuery.total / transactionsQuery.pageSize)),
        items: transactionsQuery.transactions.map((item) => ({
          id: item.id,
          direction: item.direction,
          type: item.transactionType,
          label: item.description ?? transactionTypeLabel(item.transactionType),
          amountUsdc: item.amount,
          timestamp: item.createdAt,
          status: item.status,
          jobId:
            typeof item.txMetadata.jobId === "string"
              ? item.txMetadata.jobId
              : typeof item.txMetadata.job_id === "string"
                ? item.txMetadata.job_id
                : undefined,
          jobTitle:
            typeof item.txMetadata.jobTitle === "string"
              ? item.txMetadata.jobTitle
              : typeof item.txMetadata.job_title === "string"
                ? item.txMetadata.job_title
                : undefined,
          agentName:
            typeof item.txMetadata.agentName === "string"
              ? item.txMetadata.agentName
              : typeof item.txMetadata.agent_name === "string"
                ? item.txMetadata.agent_name
                : undefined,
          counterparty:
            item.direction === "inbound"
              ? (item.fromAddress ?? undefined)
              : (item.toAddress ?? undefined),
        })),
      };
    }

    if (activeTab === "escrow") {
      return {
        tab: activeTab,
        page: 1,
        pageSize: escrowQuery.active.length,
        totalItems: escrowQuery.active.length,
        totalPages: 1,
        items: escrowQuery.active.map((item) => ({
          id: item.invoiceId,
          jobId: item.jobId,
          jobTitle: `Job ${item.jobId.slice(0, 8)}`,
          agentName: item.agentName ?? "Agent",
          amountLockedUsdc: item.lockedAmount,
          status: item.status,
          lockedAt: item.createdAt,
        })),
      };
    }

    const earningItems = earningsQuery.earnings?.items ?? [];
    return {
      tab: activeTab,
      page: earningsQuery.earnings?.meta.page ?? 1,
      pageSize: earningsQuery.earnings?.meta.pageSize ?? earningItems.length,
      totalItems: earningsQuery.earnings?.meta.total ?? earningItems.length,
      totalPages: Math.max(
        1,
        Math.ceil(
          (earningsQuery.earnings?.meta.total ?? earningItems.length) /
            Math.max(earningsQuery.earnings?.meta.pageSize ?? PAGE_SIZE, 1)
        )
      ),
      items: earningItems.map((item) => ({
        id: item.id,
        agentSlug:
          typeof item.txMetadata.agentSlug === "string" ? item.txMetadata.agentSlug : "agent",
        agentName:
          typeof item.txMetadata.agentName === "string"
            ? item.txMetadata.agentName
            : "Agent earnings",
        sourceJobId: typeof item.txMetadata.jobId === "string" ? item.txMetadata.jobId : item.id,
        sourceJobTitle:
          typeof item.txMetadata.jobTitle === "string"
            ? item.txMetadata.jobTitle
            : "Marketplace job",
        amountUsdc: item.amount,
        timestamp: item.createdAt,
        status: item.status === "completed" ? "paid" : "pending",
      })),
    };
  }, [activeTab, earningsQuery.earnings, escrowQuery.active, transactionsQuery]);

  const activityLoading =
    activeTab === "transactions"
      ? transactionsQuery.isLoading
      : activeTab === "escrow"
        ? escrowQuery.isLoading
        : earningsQuery.isLoading;

  async function copyWalletAddress() {
    if (!walletAddress) {
      return;
    }

    await navigator.clipboard.writeText(walletAddress);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  async function submitWithdraw() {
    const amount = Number(withdrawAmount);
    setWithdrawError(null);

    if (!Number.isFinite(amount) || amount <= 0) {
      setWithdrawError("Enter a valid withdrawal amount.");
      return;
    }

    if (amount > availableBalanceUsdc) {
      setWithdrawError("Withdrawal amount exceeds your available balance.");
      return;
    }

    if (!withdrawAddress.trim()) {
      setWithdrawError("Enter a destination address.");
      return;
    }

    setIsWithdrawing(true);
    try {
      await walletApi.withdraw(amount, withdrawAddress.trim());
      await Promise.all([wallet.refresh(), transactionsQuery.refresh()]);
      setWithdrawConfirmed(true);
      window.setTimeout(() => {
        setModal(null);
        setWithdrawConfirmed(false);
        setWithdrawAddress("");
        setWithdrawAmount("");
      }, 1300);
    } catch (error) {
      setWithdrawError(isApiError(error) ? error.message : "Withdrawal failed.");
    } finally {
      setIsWithdrawing(false);
    }
  }

  function closeWithdrawModal() {
    setModal(null);
    setWithdrawConfirmed(false);
    setWithdrawAddress("");
    setWithdrawAmount("");
    setWithdrawError(null);
  }

  return (
    <div className="space-y-4 xl:space-y-6">
      <section className="app-panel p-5 sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <span className="app-status-badge" data-tone="accent">
              Circle wallet
            </span>
            <h1 className="mt-4 text-3xl font-semibold text-[var(--text)] sm:text-4xl">
              Wallet management
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--text-muted)]">
              Review balance, move USDC, and audit every deposit, withdrawal, escrow lock, and owner
              payout from one workspace.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => setModal("deposit")}
              className="inline-flex h-11 items-center gap-2 rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] transition hover:opacity-95"
            >
              <Download className="h-4 w-4" />
              Deposit
            </button>
            <button
              type="button"
              onClick={() => setModal("withdraw")}
              className="inline-flex h-11 items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface)] px-5 text-sm font-semibold text-[var(--text)] transition hover:bg-[var(--surface-2)]"
            >
              <Send className="h-4 w-4" />
              Withdraw
            </button>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,420px)] xl:gap-6">
        <div className="app-panel p-5 sm:p-6">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="text-sm font-medium text-[var(--text-muted)]">Available balance</p>
              <div className="mt-4 flex items-end gap-3">
                <p className="text-4xl font-semibold text-[var(--text)] tabular-nums sm:text-5xl">
                  {wallet.isLoading ? "--" : preciseNumberFormatter.format(availableBalanceUsdc)}
                </p>
                <span className="pb-1 text-sm font-semibold text-[var(--text-muted)]">USDC</span>
              </div>
              <p className="mt-3 text-sm text-[var(--text-muted)]">
                {wallet.isLoading
                  ? "Loading USD equivalent"
                  : `${formatUsd(usdEquivalent)} USD equivalent`}
              </p>
            </div>

            <span className="app-status-badge" data-tone={wallet.error ? "danger" : "accent"}>
              Circle {wallet.error ? "sync issue" : "live"}
            </span>
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            <div className="app-subtle p-4">
              <p className="text-sm text-[var(--text-muted)]">Pending</p>
              <p className="mt-2 text-xl font-semibold text-[var(--text)] tabular-nums">
                {wallet.isLoading ? "--" : formatUsdc(0, true)}
              </p>
            </div>
            <div className="app-subtle p-4">
              <p className="text-sm text-[var(--text-muted)]">Locked</p>
              <p className="mt-2 text-xl font-semibold text-[var(--text)] tabular-nums">
                {wallet.isLoading ? "--" : formatUsdc(lockedInEscrowUsdc, true)}
              </p>
            </div>
            <div className="app-subtle p-4">
              <p className="text-sm text-[var(--text-muted)]">Wallet ID</p>
              <p className="mt-2 truncate text-sm font-medium text-[var(--text)]">
                {wallet.walletId || "Loading"}
              </p>
            </div>
          </div>
        </div>

        <div className="app-panel p-5 sm:p-6">
          <div className="flex items-start gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[var(--primary-soft)] text-[var(--primary)]">
              <Wallet className="h-5 w-5" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="font-semibold text-[var(--text)]">Wallet address</p>
              <p className="mt-2 text-sm leading-6 break-all text-[var(--text-muted)]">
                {walletAddress || "Loading wallet address"}
              </p>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            <button
              type="button"
              disabled={!walletAddress}
              onClick={() => void copyWalletAddress()}
              className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text)] transition hover:bg-[var(--surface-2)] disabled:opacity-50"
            >
              {copied ? (
                <Check className="h-4 w-4 text-[var(--accent)]" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
              {copied ? "Copied" : "Copy"}
            </button>
            <button
              type="button"
              disabled={!walletAddress}
              onClick={() => setShowQr((value) => !value)}
              className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text)] transition hover:bg-[var(--surface-2)] disabled:opacity-50"
            >
              <QrCode className="h-4 w-4" />
              {showQr ? "Hide QR" : "Show QR"}
            </button>
          </div>

          {showQr && walletAddress ? (
            <div className="mt-5 flex justify-center rounded-2xl border border-[var(--border)] bg-[var(--surface-2)] p-5">
              <AddressQr value={walletAddress} />
            </div>
          ) : null}
        </div>
      </section>

      <section className="app-panel p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-[var(--text)]">Wallet activity</h2>
            <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
              Showing {activity?.totalItems ?? 0} records for the selected ledger view.
            </p>
          </div>
          <div className="inline-flex overflow-x-auto rounded-full border border-[var(--border)] bg-[var(--surface)] p-1 shadow-[var(--shadow-soft)]">
            {tabOptions.map((tab) => (
              <button
                key={tab.value}
                type="button"
                aria-pressed={activeTab === tab.value}
                onClick={() => {
                  setActiveTab(tab.value);
                  setPage(1);
                }}
                className={cn(
                  "inline-flex h-10 rounded-full px-4 text-sm font-medium whitespace-nowrap transition",
                  activeTab === tab.value
                    ? "bg-[var(--surface-2)] text-[var(--text)]"
                    : "text-[var(--text-muted)] hover:text-[var(--text)]"
                )}
              >
                <span className="self-center">{tab.label}</span>
              </button>
            ))}
          </div>
          {activeTab === "transactions" ? (
            <label className="flex h-11 items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 text-sm text-[var(--text-muted)] shadow-[var(--shadow-soft)]">
              <span>Type</span>
              <select
                value={transactionType}
                onChange={(event) => {
                  setTransactionType(event.target.value as WalletTransactionType | "all");
                  setPage(1);
                }}
                className="bg-transparent font-medium text-[var(--text)] outline-none"
              >
                {transactionTypeOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
        </div>

        <div className="mt-6 space-y-3">
          {activityLoading ? (
            <div className="flex items-center gap-3 rounded-2xl border border-[var(--border)] bg-[var(--surface-2)] p-5 text-sm text-[var(--text-muted)]">
              <LoaderCircle className="h-4 w-4 animate-spin text-[var(--primary)]" />
              Loading wallet activity
            </div>
          ) : null}

          {!activityLoading && activity?.items.length === 0 ? (
            <EmptyState label="No wallet records are available for this view yet." />
          ) : null}

          {!activityLoading && activity
            ? activity.items.map((item) => {
                if (isTransactionRecord(item)) {
                  return <TransactionRow key={item.id} item={item} />;
                }

                if (isEscrowRecord(item)) {
                  return <EscrowRow key={item.id} item={item} />;
                }

                return <EarningRow key={item.id} item={item} />;
              })
            : null}
        </div>

        {activity && activity.totalPages > 1 ? (
          <div className="mt-6 flex flex-col gap-3 border-t border-[var(--border)] pt-5 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-[var(--text-muted)]">
              Page {activity.page} of {activity.totalPages}
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={activity.page <= 1}
                onClick={() => setPage((value) => Math.max(1, value - 1))}
                className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text)] transition hover:bg-[var(--surface-2)] disabled:opacity-45"
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </button>
              <button
                type="button"
                disabled={activity.page >= activity.totalPages}
                onClick={() => setPage((value) => value + 1)}
                className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text)] transition hover:bg-[var(--surface-2)] disabled:opacity-45"
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        ) : null}
      </section>

      {modal === "deposit" ? (
        <Modal title="Deposit USDC" onClose={() => setModal(null)}>
          <div className="mt-5 space-y-4">
            <div className="app-subtle p-4">
              <p className="text-sm font-medium text-[var(--text)]">Circle deposit address</p>
              <p className="mt-2 text-sm leading-6 break-all text-[var(--text-muted)]">
                {walletAddress || "Loading deposit address"}
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-[160px_minmax(0,1fr)]">
              {walletAddress ? <AddressQr value={walletAddress} /> : null}
              <div className="space-y-3 text-sm leading-6 text-[var(--text-muted)]">
                <p>
                  {wallet.depositInstructions?.instructions ??
                    "Send only USDC to this Circle-powered wallet address."}
                </p>
                <p>Deposits appear after network confirmation and refresh automatically.</p>
                <button
                  type="button"
                  onClick={() => void copyWalletAddress()}
                  disabled={!walletAddress}
                  className="inline-flex h-10 items-center gap-2 rounded-full bg-[var(--primary)] px-4 text-sm font-semibold text-[var(--primary-foreground)]"
                >
                  {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                  {copied ? "Copied" : walletAddress ? shortAddress(walletAddress) : "Loading"}
                </button>
              </div>
            </div>
          </div>
        </Modal>
      ) : null}

      {modal === "withdraw" ? (
        <Modal title="Withdraw USDC" onClose={closeWithdrawModal}>
          <div className="mt-5 space-y-4">
            <label className="grid gap-2 text-sm">
              <span className="font-medium text-[var(--text)]">Destination address</span>
              <input
                value={withdrawAddress}
                onChange={(event) => setWithdrawAddress(event.target.value)}
                className="h-11 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-[var(--text)] outline-none focus:border-[var(--primary)]"
                placeholder="0x..."
              />
            </label>
            <label className="grid gap-2 text-sm">
              <span className="font-medium text-[var(--text)]">Amount</span>
              <input
                value={withdrawAmount}
                onChange={(event) => setWithdrawAmount(event.target.value)}
                className="h-11 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-[var(--text)] outline-none focus:border-[var(--primary)]"
                inputMode="decimal"
                placeholder="500.00"
              />
            </label>
            <div className="app-subtle p-4 text-sm leading-6 text-[var(--text-muted)]">
              Withdrawals are submitted through the Circle wallet rail and may require final
              compliance review before funds leave escrow-safe custody.
            </div>
            {withdrawError ? (
              <div className="rounded-2xl border border-[var(--danger-soft)] bg-[var(--danger-soft)] p-3 text-sm text-[var(--danger)]">
                {withdrawError}
              </div>
            ) : null}
            <button
              type="button"
              disabled={!withdrawAddress.trim() || !Number(withdrawAmount) || isWithdrawing}
              onClick={() => void submitWithdraw()}
              className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] transition hover:opacity-95 disabled:opacity-50"
            >
              {withdrawConfirmed ? (
                <Check className="h-4 w-4" />
              ) : isWithdrawing ? (
                <LoaderCircle className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              {withdrawConfirmed
                ? "Withdrawal queued"
                : isWithdrawing
                  ? "Submitting..."
                  : "Confirm withdrawal"}
            </button>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
