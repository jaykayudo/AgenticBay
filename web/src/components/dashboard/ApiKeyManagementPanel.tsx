"use client";

import {
  AlertTriangle,
  BarChart3,
  Check,
  Copy,
  Filter,
  KeyRound,
  LoaderCircle,
  MoreVertical,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  X,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useState, type ReactNode } from "react";
import { toast } from "sonner";

import { useApiKeyUsage, useApiKeys } from "@/hooks/useApiKeys";
import type {
  ApiKeyCreatedResponse,
  ApiKeyEnvironment,
  ApiKeyPermission,
  ApiKeyRecord,
} from "@/lib/api/apiKeys";
import { cn } from "@/lib/utils";

const MAX_ACTIVE_KEYS = 5;

const permissionOptions: Array<{ value: ApiKeyPermission; label: string }> = [
  { value: "search", label: "Search agents" },
  { value: "hire", label: "Hire and execute" },
  { value: "pay", label: "Make payments" },
  { value: "check_balance", label: "Check balance" },
  { value: "read_history", label: "Read history" },
];

const allPermissions = permissionOptions.map((permission) => permission.value);

const environmentLabels: Record<ApiKeyEnvironment, string> = {
  SANDBOX: "Sandbox",
  PRODUCTION: "Production",
};

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
});

const dateTimeFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

type SortMode = "created_desc" | "last_used_desc" | "name_asc";
type FilterMode = "ALL" | ApiKeyEnvironment;

function formatDate(value: string | null) {
  if (!value) {
    return "Never";
  }
  return dateFormatter.format(new Date(value));
}

function formatDateTime(value: string | null) {
  if (!value) {
    return "Never";
  }
  return dateTimeFormatter.format(new Date(value));
}

function permissionsLabel(permissions: ApiKeyPermission[]) {
  if (permissions.length === allPermissions.length) {
    return "All permissions";
  }
  return permissions
    .map((permission) => permissionOptions.find((item) => item.value === permission)?.label)
    .filter(Boolean)
    .join(", ");
}

function Modal({
  title,
  children,
  onClose,
  closeDisabled = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  closeDisabled?: boolean;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/45 px-4 py-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <section className="app-panel max-h-[calc(100vh-2rem)] w-full max-w-xl overflow-y-auto p-5 sm:p-6">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-lg font-semibold text-[var(--text)]">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            disabled={closeDisabled}
            className="grid h-10 w-10 place-items-center rounded-full border border-[var(--border)] text-[var(--text-muted)] transition hover:text-[var(--text)] disabled:opacity-40"
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

function GenerateKeyModal({
  busy,
  onClose,
  onGenerate,
}: {
  busy: boolean;
  onClose: () => void;
  onGenerate: (payload: {
    name: string;
    environment: ApiKeyEnvironment;
    permissions: ApiKeyPermission[];
    expiresInDays: number | null;
  }) => void;
}) {
  const [name, setName] = useState("");
  const [environment, setEnvironment] = useState<ApiKeyEnvironment>("SANDBOX");
  const [expiresInDays, setExpiresInDays] = useState("none");
  const [permissions, setPermissions] = useState<ApiKeyPermission[]>(allPermissions);

  function togglePermission(permission: ApiKeyPermission) {
    setPermissions((current) =>
      current.includes(permission)
        ? current.filter((item) => item !== permission)
        : [...current, permission]
    );
  }

  const resolvedExpiry = expiresInDays === "none" ? null : Number(expiresInDays);
  const canGenerate = name.trim().length > 0 && permissions.length > 0 && !busy;

  return (
    <Modal title="Generate API key" onClose={onClose}>
      <div className="mt-5 space-y-5">
        <label className="grid gap-2 text-sm">
          <span className="font-medium text-[var(--text)]">Key name</span>
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="h-11 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-[var(--text)] outline-none focus:border-[var(--primary)]"
            placeholder="Production Backend"
          />
        </label>

        <div className="grid gap-3 sm:grid-cols-2">
          {(["SANDBOX", "PRODUCTION"] as const).map((value) => (
            <button
              key={value}
              type="button"
              aria-pressed={environment === value}
              onClick={() => setEnvironment(value)}
              className={cn(
                "rounded-2xl border p-4 text-left transition",
                environment === value
                  ? "border-[var(--primary)] bg-[var(--primary-soft)]"
                  : "border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-2)]"
              )}
            >
              <span className="text-sm font-semibold text-[var(--text)]">
                {environmentLabels[value]}
              </span>
              <span className="mt-1 block text-xs leading-5 text-[var(--text-muted)]">
                {value === "PRODUCTION" ? "Live integrations" : "Testing and development"}
              </span>
            </button>
          ))}
        </div>

        <label className="grid gap-2 text-sm">
          <span className="font-medium text-[var(--text)]">Expiration</span>
          <select
            value={expiresInDays}
            onChange={(event) => setExpiresInDays(event.target.value)}
            className="h-11 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-[var(--text)] outline-none focus:border-[var(--primary)]"
          >
            <option value="none">Never expires</option>
            <option value="30">30 days</option>
            <option value="90">90 days</option>
            <option value="365">1 year</option>
          </select>
        </label>

        <fieldset className="space-y-3">
          <legend className="text-sm font-medium text-[var(--text)]">Permissions</legend>
          <div className="grid gap-2 sm:grid-cols-2">
            {permissionOptions.map((permission) => (
              <label
                key={permission.value}
                className="flex items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3 text-sm text-[var(--text)]"
              >
                <input
                  type="checkbox"
                  checked={permissions.includes(permission.value)}
                  onChange={() => togglePermission(permission.value)}
                  className="h-4 w-4 accent-[var(--primary)]"
                />
                {permission.label}
              </label>
            ))}
          </div>
        </fieldset>

        <div className="rounded-2xl border border-[var(--accent)]/30 bg-[var(--accent-soft)] p-4 text-sm leading-6 text-[var(--text)]">
          Full keys are shown once. Store the key before closing the success modal.
        </div>

        <div className="flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-11 flex-1 items-center justify-center rounded-full border border-[var(--border)] px-5 text-sm font-semibold text-[var(--text)]"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!canGenerate}
            onClick={() =>
              onGenerate({
                name: name.trim(),
                environment,
                permissions,
                expiresInDays: resolvedExpiry,
              })
            }
            className="inline-flex h-11 flex-1 items-center justify-center gap-2 rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] disabled:opacity-60"
          >
            {busy ? (
              <LoaderCircle className="h-4 w-4 animate-spin" />
            ) : (
              <Plus className="h-4 w-4" />
            )}
            Generate key
          </button>
        </div>
      </div>
    </Modal>
  );
}

function KeyCreatedModal({
  createdKey,
  onClose,
}: {
  createdKey: ApiKeyCreatedResponse;
  onClose: () => void;
}) {
  const [acknowledged, setAcknowledged] = useState(false);
  const [copied, setCopied] = useState(false);

  async function copyKey() {
    await navigator.clipboard.writeText(createdKey.key);
    setCopied(true);
    toast.success("Key copied to clipboard");
    window.setTimeout(() => setCopied(false), 1500);
  }

  return (
    <Modal title="Key generated" onClose={onClose} closeDisabled={!acknowledged}>
      <div className="mt-5 space-y-5">
        <div className="rounded-2xl border border-[var(--accent)]/30 bg-[var(--accent-soft)] p-4 text-sm leading-6 text-[var(--text)]">
          Save this key now. You will not be able to view it again.
        </div>

        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface-2)] p-4">
          <p className="text-sm font-medium text-[var(--text-muted)]">{createdKey.name}</p>
          <code className="mt-3 block text-sm break-all text-[var(--text)]">{createdKey.key}</code>
          <button
            type="button"
            onClick={() => void copyKey()}
            className={cn(
              "mt-4 inline-flex h-10 items-center gap-2 rounded-full px-4 text-sm font-semibold transition",
              copied
                ? "bg-[var(--accent)] text-white"
                : "bg-[var(--primary)] text-[var(--primary-foreground)]"
            )}
          >
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            {copied ? "Copied" : "Copy key"}
          </button>
        </div>

        <label className="flex items-start gap-3 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 text-sm text-[var(--text)]">
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(event) => setAcknowledged(event.target.checked)}
            className="mt-1 h-4 w-4 accent-[var(--primary)]"
          />
          <span>I have saved this key securely.</span>
        </label>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <Link
            href="/docs/api-reference/authentication"
            className="text-sm font-semibold text-[var(--primary)] hover:underline"
          >
            View setup guide
          </Link>
          <button
            type="button"
            disabled={!acknowledged}
            onClick={onClose}
            className="inline-flex h-11 items-center justify-center rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] disabled:opacity-60"
          >
            Done
          </button>
        </div>
      </div>
    </Modal>
  );
}

function RevokeKeyModal({
  apiKey,
  busy,
  onClose,
  onRevoke,
}: {
  apiKey: ApiKeyRecord;
  busy: boolean;
  onClose: () => void;
  onRevoke: (reason: string) => void;
}) {
  const [reason, setReason] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const canRevoke = confirmation === apiKey.name && !busy;

  return (
    <Modal title="Revoke API key" onClose={onClose}>
      <div className="mt-5 space-y-5">
        <div className="rounded-2xl border border-[var(--danger)]/25 bg-[var(--danger-soft)] p-4 text-sm leading-6 text-[var(--danger)]">
          This action cannot be undone. Integrations using this key will stop working immediately.
        </div>
        <div className="app-subtle p-4">
          <p className="text-sm font-semibold text-[var(--text)]">{apiKey.name}</p>
          <code className="mt-2 block text-sm break-all text-[var(--text-muted)]">
            {apiKey.key_prefix}...
          </code>
        </div>
        <label className="grid gap-2 text-sm">
          <span className="font-medium text-[var(--text)]">Reason</span>
          <textarea
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            className="min-h-24 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-[var(--text)] outline-none focus:border-[var(--primary)]"
            placeholder="Optional"
          />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="font-medium text-[var(--text)]">Type the key name to confirm</span>
          <input
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
            className="h-11 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-[var(--text)] outline-none focus:border-[var(--primary)]"
            placeholder={apiKey.name}
          />
        </label>
        <div className="flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-11 flex-1 items-center justify-center rounded-full border border-[var(--border)] px-5 text-sm font-semibold text-[var(--text)]"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!canRevoke}
            onClick={() => onRevoke(reason)}
            className="inline-flex h-11 flex-1 items-center justify-center gap-2 rounded-full bg-[var(--danger)] px-5 text-sm font-semibold text-white disabled:opacity-60"
          >
            {busy ? (
              <LoaderCircle className="h-4 w-4 animate-spin" />
            ) : (
              <Trash2 className="h-4 w-4" />
            )}
            Revoke key
          </button>
        </div>
      </div>
    </Modal>
  );
}

function RotateKeyModal({
  apiKey,
  busy,
  onClose,
  onRotate,
}: {
  apiKey: ApiKeyRecord;
  busy: boolean;
  onClose: () => void;
  onRotate: () => void;
}) {
  const [confirmation, setConfirmation] = useState("");
  const canRotate = confirmation === apiKey.name && !busy;

  return (
    <Modal title="Rotate API key" onClose={onClose}>
      <div className="mt-5 space-y-5">
        <div className="rounded-2xl border border-[var(--accent)]/30 bg-[var(--accent-soft)] p-4 text-sm leading-6 text-[var(--text)]">
          Rotating creates a new key and immediately invalidates the old one.
        </div>
        <div className="app-subtle p-4">
          <p className="text-sm font-semibold text-[var(--text)]">{apiKey.name}</p>
          <code className="mt-2 block text-sm break-all text-[var(--text-muted)]">
            {apiKey.key_prefix}...
          </code>
        </div>
        <label className="grid gap-2 text-sm">
          <span className="font-medium text-[var(--text)]">Type the key name to confirm</span>
          <input
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
            className="h-11 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-[var(--text)] outline-none focus:border-[var(--primary)]"
            placeholder={apiKey.name}
          />
        </label>
        <div className="flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-11 flex-1 items-center justify-center rounded-full border border-[var(--border)] px-5 text-sm font-semibold text-[var(--text)]"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!canRotate}
            onClick={onRotate}
            className="inline-flex h-11 flex-1 items-center justify-center gap-2 rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] disabled:opacity-60"
          >
            {busy ? (
              <LoaderCircle className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            Rotate key
          </button>
        </div>
      </div>
    </Modal>
  );
}

function UsageStatsModal({ apiKey, onClose }: { apiKey: ApiKeyRecord; onClose: () => void }) {
  const usageQuery = useApiKeyUsage(apiKey.id);
  const usage = usageQuery.data;
  const peak = Math.max(1, ...(usage?.daily_usage.map((day) => day.count) ?? [0]));

  return (
    <Modal title={`${apiKey.name} usage`} onClose={onClose}>
      <div className="mt-5 space-y-5">
        {usageQuery.isLoading ? (
          <div className="flex items-center gap-3 text-sm text-[var(--text-muted)]">
            <LoaderCircle className="h-4 w-4 animate-spin text-[var(--primary)]" />
            Loading usage
          </div>
        ) : null}

        {usage ? (
          <>
            <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4">
              <p className="text-sm font-semibold text-[var(--text)]">Last 30 days</p>
              <div className="mt-4 flex h-24 items-end gap-1">
                {usage.daily_usage.map((day) => (
                  <div
                    key={day.date}
                    title={`${day.date}: ${day.count}`}
                    className="min-w-0 flex-1 rounded-t bg-[var(--primary)]/80"
                    style={{ height: `${Math.max(4, (day.count / peak) * 100)}%` }}
                  />
                ))}
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="app-subtle p-4">
                <p className="text-sm text-[var(--text-muted)]">Total requests</p>
                <p className="mt-2 text-lg font-semibold text-[var(--text)]">
                  {usage.usage_count.toLocaleString()}
                </p>
              </div>
              <div className="app-subtle p-4">
                <p className="text-sm text-[var(--text-muted)]">Last used</p>
                <p className="mt-2 text-sm font-semibold text-[var(--text)]">
                  {formatDateTime(usage.last_used_at)}
                </p>
              </div>
              <div className="app-subtle p-4">
                <p className="text-sm text-[var(--text-muted)]">Last IP</p>
                <p className="mt-2 text-sm font-semibold text-[var(--text)]">
                  {usage.last_used_ip ?? "Unknown"}
                </p>
              </div>
              <div className="app-subtle p-4">
                <p className="text-sm text-[var(--text-muted)]">Last user agent</p>
                <p className="mt-2 text-sm font-semibold break-all text-[var(--text)]">
                  {usage.last_used_user_agent ?? "Unknown"}
                </p>
              </div>
            </div>
          </>
        ) : null}
      </div>
    </Modal>
  );
}

function ApiKeyCard({
  apiKey,
  copied,
  onCopyPrefix,
  onUsage,
  onRotate,
  onRevoke,
}: {
  apiKey: ApiKeyRecord;
  copied: boolean;
  onCopyPrefix: () => void;
  onUsage: () => void;
  onRotate: () => void;
  onRevoke: () => void;
}) {
  return (
    <article className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="grid h-10 w-10 place-items-center rounded-2xl bg-[var(--primary-soft)] text-[var(--primary)]">
              <KeyRound className="h-4 w-4" />
            </span>
            <div className="min-w-0">
              <p className="font-semibold break-words text-[var(--text)]">{apiKey.name}</p>
              <code className="mt-1 block text-sm break-all text-[var(--text-muted)]">
                {apiKey.key_prefix}...
              </code>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-[var(--text-muted)]">
            <span
              className="app-status-badge"
              data-tone={apiKey.environment === "PRODUCTION" ? "default" : "accent"}
            >
              {environmentLabels[apiKey.environment]}
            </span>
            <span>{permissionsLabel(apiKey.permissions)}</span>
            <span>Created {formatDate(apiKey.created_at)}</span>
            <span>Last used {formatDate(apiKey.last_used_at)}</span>
            <span>{apiKey.usage_count.toLocaleString()} requests</span>
            {apiKey.expires_at ? <span>Expires {formatDate(apiKey.expires_at)}</span> : null}
            {!apiKey.is_active && apiKey.revoked_at ? (
              <span>Revoked {formatDate(apiKey.revoked_at)}</span>
            ) : null}
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onUsage}
            className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text)] transition hover:bg-[var(--surface-2)]"
          >
            <BarChart3 className="h-4 w-4" />
            Usage
          </button>
          <button
            type="button"
            onClick={onCopyPrefix}
            className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text)] transition hover:bg-[var(--surface-2)]"
          >
            {copied ? (
              <Check className="h-4 w-4 text-[var(--accent)]" />
            ) : (
              <Copy className="h-4 w-4" />
            )}
            {copied ? "Copied" : "Copy prefix"}
          </button>
          {apiKey.is_active ? (
            <>
              <button
                type="button"
                onClick={onRotate}
                className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text)] transition hover:bg-[var(--surface-2)]"
              >
                <RefreshCw className="h-4 w-4" />
                Rotate
              </button>
              <button
                type="button"
                onClick={onRevoke}
                className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--danger)]/25 px-4 text-sm font-medium text-[var(--danger)] transition hover:bg-[var(--danger-soft)]"
              >
                <Trash2 className="h-4 w-4" />
                Revoke
              </button>
            </>
          ) : null}
        </div>
      </div>
    </article>
  );
}

export function ApiKeyManagementPanel() {
  const { keysQuery, createKey, revokeKey, rotateKey } = useApiKeys();
  const [showGenerate, setShowGenerate] = useState(false);
  const [createdKey, setCreatedKey] = useState<ApiKeyCreatedResponse | null>(null);
  const [revokeTarget, setRevokeTarget] = useState<ApiKeyRecord | null>(null);
  const [rotateTarget, setRotateTarget] = useState<ApiKeyRecord | null>(null);
  const [usageTarget, setUsageTarget] = useState<ApiKeyRecord | null>(null);
  const [copiedId, setCopiedId] = useState("");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<FilterMode>("ALL");
  const [sort, setSort] = useState<SortMode>("created_desc");

  const keys = useMemo(() => keysQuery.data ?? [], [keysQuery.data]);
  const activeKeys = keys.filter((key) => key.is_active);
  const revokedKeys = keys.filter((key) => !key.is_active);
  const activeLimitReached = activeKeys.length >= MAX_ACTIVE_KEYS;

  const visibleKeys = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return [...keys]
      .filter((key) => {
        const matchesSearch =
          !needle ||
          key.name.toLowerCase().includes(needle) ||
          key.key_prefix.toLowerCase().includes(needle);
        const matchesFilter = filter === "ALL" || key.environment === filter;
        return matchesSearch && matchesFilter;
      })
      .sort((a, b) => {
        if (sort === "name_asc") {
          return a.name.localeCompare(b.name);
        }
        if (sort === "last_used_desc") {
          return new Date(b.last_used_at ?? 0).getTime() - new Date(a.last_used_at ?? 0).getTime();
        }
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });
  }, [filter, keys, search, sort]);

  const visibleActive = visibleKeys.filter((key) => key.is_active);
  const visibleRevoked = visibleKeys.filter((key) => !key.is_active);

  async function copyPrefix(apiKey: ApiKeyRecord) {
    await navigator.clipboard.writeText(`${apiKey.key_prefix}...`);
    setCopiedId(apiKey.id);
    toast.success("Key prefix copied");
    window.setTimeout(() => setCopiedId(""), 1400);
  }

  async function handleGenerate(payload: {
    name: string;
    environment: ApiKeyEnvironment;
    permissions: ApiKeyPermission[];
    expiresInDays: number | null;
  }) {
    try {
      const result = await createKey.mutateAsync({
        name: payload.name,
        environment: payload.environment,
        permissions: payload.permissions,
        expires_in_days: payload.expiresInDays,
      });
      setShowGenerate(false);
      setCreatedKey(result);
      toast.success("API key generated");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not generate API key.");
    }
  }

  async function handleRevoke(reason: string) {
    if (!revokeTarget) {
      return;
    }
    try {
      await revokeKey.mutateAsync({ id: revokeTarget.id, reason });
      setRevokeTarget(null);
      toast.success("API key revoked");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not revoke API key.");
    }
  }

  async function handleRotate() {
    if (!rotateTarget) {
      return;
    }
    try {
      const result = await rotateKey.mutateAsync(rotateTarget.id);
      setRotateTarget(null);
      setCreatedKey(result);
      toast.success("API key rotated");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not rotate API key.");
    }
  }

  function clearCreatedKey() {
    setCreatedKey(null);
  }

  return (
    <section className="app-panel p-5 sm:p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-[var(--text)]">API key management</h2>
          <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
            Create keys for external user agents and integrations. Full secrets are shown once.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowGenerate(true)}
          disabled={activeLimitReached || createKey.isPending}
          className="inline-flex h-11 items-center justify-center gap-2 rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] disabled:opacity-60"
        >
          <Plus className="h-4 w-4" />
          Generate New Key
        </button>
      </div>

      <div className="mt-5 rounded-2xl border border-[var(--accent)]/30 bg-[var(--accent-soft)] p-4">
        <div className="flex gap-3">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--accent)]" />
          <p className="text-sm leading-6 text-[var(--text)]">
            Treat API keys like passwords. Anyone with a key can access permitted account actions.
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-3 lg:grid-cols-[minmax(0,1fr)_180px_180px]">
        <label className="relative">
          <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="h-11 w-full rounded-full border border-[var(--border)] bg-[var(--surface)] pr-4 pl-10 text-sm text-[var(--text)] outline-none focus:border-[var(--primary)]"
            placeholder="Search keys"
          />
        </label>
        <label className="relative">
          <Filter className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
          <select
            value={filter}
            onChange={(event) => setFilter(event.target.value as FilterMode)}
            className="h-11 w-full rounded-full border border-[var(--border)] bg-[var(--surface)] pr-4 pl-10 text-sm text-[var(--text)] outline-none focus:border-[var(--primary)]"
          >
            <option value="ALL">All environments</option>
            <option value="SANDBOX">Sandbox</option>
            <option value="PRODUCTION">Production</option>
          </select>
        </label>
        <label className="relative">
          <MoreVertical className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
          <select
            value={sort}
            onChange={(event) => setSort(event.target.value as SortMode)}
            className="h-11 w-full rounded-full border border-[var(--border)] bg-[var(--surface)] pr-4 pl-10 text-sm text-[var(--text)] outline-none focus:border-[var(--primary)]"
          >
            <option value="created_desc">Newest</option>
            <option value="last_used_desc">Last used</option>
            <option value="name_asc">Name</option>
          </select>
        </label>
      </div>

      {activeLimitReached ? (
        <div className="mt-4 rounded-2xl border border-[var(--danger)]/25 bg-[var(--danger-soft)] p-4 text-sm leading-6 text-[var(--danger)]">
          Maximum {MAX_ACTIVE_KEYS} active keys. Revoke an existing key to create a new one.
        </div>
      ) : null}

      {keysQuery.isLoading ? (
        <div className="mt-6 flex items-center gap-3 text-sm text-[var(--text-muted)]">
          <LoaderCircle className="h-4 w-4 animate-spin text-[var(--primary)]" />
          Loading API keys
        </div>
      ) : null}

      {keysQuery.isError ? (
        <div className="mt-6 rounded-2xl border border-[var(--danger)]/25 bg-[var(--danger-soft)] p-4 text-sm text-[var(--danger)]">
          {keysQuery.error instanceof Error ? keysQuery.error.message : "Could not load API keys."}
        </div>
      ) : null}

      {!keysQuery.isLoading && keys.length === 0 ? (
        <div className="app-subtle mt-6 p-6 text-sm text-[var(--text-muted)]">
          No API keys yet. Generate a key when you are ready to connect an integration.
        </div>
      ) : null}

      {visibleKeys.length === 0 && keys.length > 0 ? (
        <div className="app-subtle mt-6 p-6 text-sm text-[var(--text-muted)]">
          No keys match the current filters.
        </div>
      ) : null}

      {visibleActive.length > 0 ? (
        <div className="mt-6 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-[var(--text)]">
              Active keys ({activeKeys.length} of {MAX_ACTIVE_KEYS})
            </h3>
          </div>
          {visibleActive.map((apiKey) => (
            <ApiKeyCard
              key={apiKey.id}
              apiKey={apiKey}
              copied={copiedId === apiKey.id}
              onCopyPrefix={() => void copyPrefix(apiKey)}
              onUsage={() => setUsageTarget(apiKey)}
              onRotate={() => setRotateTarget(apiKey)}
              onRevoke={() => setRevokeTarget(apiKey)}
            />
          ))}
        </div>
      ) : null}

      {visibleRevoked.length > 0 ? (
        <details className="group mt-6" open={visibleActive.length === 0}>
          <summary className="cursor-pointer text-sm font-semibold text-[var(--text)]">
            Revoked keys ({revokedKeys.length})
          </summary>
          <div className="mt-3 space-y-3 opacity-80">
            {visibleRevoked.map((apiKey) => (
              <ApiKeyCard
                key={apiKey.id}
                apiKey={apiKey}
                copied={copiedId === apiKey.id}
                onCopyPrefix={() => void copyPrefix(apiKey)}
                onUsage={() => setUsageTarget(apiKey)}
                onRotate={() => setRotateTarget(apiKey)}
                onRevoke={() => setRevokeTarget(apiKey)}
              />
            ))}
          </div>
        </details>
      ) : null}

      {showGenerate ? (
        <GenerateKeyModal
          busy={createKey.isPending}
          onClose={() => setShowGenerate(false)}
          onGenerate={(payload) => void handleGenerate(payload)}
        />
      ) : null}

      {createdKey ? <KeyCreatedModal createdKey={createdKey} onClose={clearCreatedKey} /> : null}

      {revokeTarget ? (
        <RevokeKeyModal
          apiKey={revokeTarget}
          busy={revokeKey.isPending}
          onClose={() => setRevokeTarget(null)}
          onRevoke={(reason) => void handleRevoke(reason)}
        />
      ) : null}

      {rotateTarget ? (
        <RotateKeyModal
          apiKey={rotateTarget}
          busy={rotateKey.isPending}
          onClose={() => setRotateTarget(null)}
          onRotate={() => void handleRotate()}
        />
      ) : null}

      {usageTarget ? (
        <UsageStatsModal apiKey={usageTarget} onClose={() => setUsageTarget(null)} />
      ) : null}
    </section>
  );
}
