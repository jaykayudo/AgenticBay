"use client";

import { useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  Check,
  Copy,
  CreditCard,
  KeyRound,
  LoaderCircle,
  LockKeyhole,
  Pencil,
  Plus,
  ShieldCheck,
  Trash2,
  UserRound,
  X,
} from "lucide-react";
import { useState, type ReactNode } from "react";

import { useApiQuery } from "@/hooks/useApi";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

type SettingsTab = "profile" | "security" | "apiKeys" | "notifications" | "billing";

type UserSettingsProfile = {
  username: string;
  email: string;
  role: "buyer" | "agent_owner" | "admin";
  avatarInitials: string;
  avatarColor: string;
};

type UserSettingsApiKey = {
  id: string;
  environment: "Development" | "Production";
  prefix: string;
  createdAt: string;
  lastUsedAt: string | null;
};

type UserSettingsNotification = {
  id: string;
  label: string;
  description: string;
  enabled: boolean;
};

type UserSettingsResponse = {
  profile: UserSettingsProfile;
  apiKeys: UserSettingsApiKey[];
  notifications: UserSettingsNotification[];
};

type GeneratedKeyPayload = {
  key: UserSettingsApiKey;
  fullKey: string;
};

const tabs: Array<{ value: SettingsTab; label: string; icon: typeof UserRound }> = [
  { value: "profile", label: "Profile", icon: UserRound },
  { value: "security", label: "Security", icon: ShieldCheck },
  { value: "apiKeys", label: "API Keys", icon: KeyRound },
  { value: "notifications", label: "Notifications", icon: Bell },
  { value: "billing", label: "Billing", icon: CreditCard },
];

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
});

function roleLabel(role: UserSettingsProfile["role"]) {
  const labels: Record<UserSettingsProfile["role"], string> = {
    buyer: "Buyer",
    agent_owner: "Agent owner",
    admin: "Admin",
  };

  return labels[role];
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

function Toggle({
  enabled,
  disabled,
  onClick,
}: {
  enabled: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={enabled}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "relative h-7 w-12 rounded-full border transition disabled:opacity-60",
        enabled
          ? "border-[var(--primary)] bg-[var(--primary)]"
          : "border-[var(--border)] bg-[var(--surface-2)]"
      )}
    >
      <span
        className={cn(
          "absolute top-1 h-5 w-5 rounded-full bg-white shadow-sm transition",
          enabled ? "left-6" : "left-1"
        )}
      />
      <span className="sr-only">{enabled ? "Enabled" : "Disabled"}</span>
    </button>
  );
}

export function UserSettingsPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<SettingsTab>("profile");
  const [editingProfile, setEditingProfile] = useState(false);
  const [usernameDraft, setUsernameDraft] = useState("");
  const [emailDraft, setEmailDraft] = useState("");
  const [profileError, setProfileError] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const [keyEnvironment, setKeyEnvironment] =
    useState<UserSettingsApiKey["environment"]>("Development");
  const [generatedKey, setGeneratedKey] = useState<GeneratedKeyPayload | null>(null);
  const [generatingKey, setGeneratingKey] = useState(false);
  const [keyToRevoke, setKeyToRevoke] = useState<UserSettingsApiKey | null>(null);
  const [revokingKey, setRevokingKey] = useState(false);
  const [copiedValue, setCopiedValue] = useState("");
  const [updatingNotificationId, setUpdatingNotificationId] = useState("");

  const settingsQuery = useApiQuery<UserSettingsResponse>(["user-settings"], "/user/settings");
  const settings = settingsQuery.data;

  function openProfileEditor(profile: UserSettingsProfile) {
    setUsernameDraft(profile.username);
    setEmailDraft(profile.email);
    setProfileError("");
    setEditingProfile(true);
  }

  async function copyValue(value: string, label: string) {
    await navigator.clipboard.writeText(value);
    setCopiedValue(label);
    window.setTimeout(() => setCopiedValue(""), 1600);
  }

  async function saveProfile() {
    setSavingProfile(true);
    setProfileError("");

    try {
      await apiFetch<UserSettingsProfile>("/user/settings/profile", {
        method: "patch",
        data: {
          username: usernameDraft,
          email: emailDraft,
        },
      });
      await queryClient.invalidateQueries({ queryKey: ["user-settings"] });
      setEditingProfile(false);
    } catch (error) {
      setProfileError(error instanceof Error ? error.message : "Profile update failed.");
    } finally {
      setSavingProfile(false);
    }
  }

  async function generateKey() {
    setGeneratingKey(true);

    try {
      const response = await apiFetch<GeneratedKeyPayload>("/user/settings/api-keys", {
        method: "post",
        data: {
          environment: keyEnvironment,
        },
      });
      setGeneratedKey(response);
      await queryClient.invalidateQueries({ queryKey: ["user-settings"] });
    } finally {
      setGeneratingKey(false);
    }
  }

  async function revokeKey() {
    if (!keyToRevoke) {
      return;
    }

    setRevokingKey(true);

    try {
      await apiFetch(`/user/settings/api-keys/${encodeURIComponent(keyToRevoke.id)}`, {
        method: "delete",
      });
      await queryClient.invalidateQueries({ queryKey: ["user-settings"] });
      setKeyToRevoke(null);
    } finally {
      setRevokingKey(false);
    }
  }

  async function toggleNotification(notification: UserSettingsNotification) {
    setUpdatingNotificationId(notification.id);

    try {
      await apiFetch(`/user/settings/notifications/${encodeURIComponent(notification.id)}`, {
        method: "patch",
        data: {
          enabled: !notification.enabled,
        },
      });
      await queryClient.invalidateQueries({ queryKey: ["user-settings"] });
    } finally {
      setUpdatingNotificationId("");
    }
  }

  return (
    <div className="space-y-4 xl:space-y-6">
      <section className="app-panel overflow-hidden p-5 sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <span className="app-status-badge" data-tone="accent">
              Account control
            </span>
            <h1 className="mt-4 text-3xl font-semibold tracking-[-0.04em] text-[var(--text)] sm:text-4xl">
              User settings
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--text-muted)]">
              Manage your profile, account safety, API access, billing posture, and the notification
              signals that keep the marketplace useful without getting noisy.
            </p>
          </div>
          <div className="app-subtle p-4">
            <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
              Signed in as
            </p>
            <p className="mt-2 text-sm font-semibold text-[var(--text)]">
              {settings?.profile.email ?? "Loading account"}
            </p>
          </div>
        </div>

        <div className="mt-6 flex gap-2 overflow-x-auto rounded-[2rem] border border-[var(--border)] bg-[var(--surface)] p-1 shadow-[var(--shadow-soft)]">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.value;

            return (
              <button
                key={tab.value}
                type="button"
                aria-pressed={isActive}
                onClick={() => setActiveTab(tab.value)}
                className={cn(
                  "inline-flex h-11 items-center gap-2 rounded-full px-4 text-sm font-medium whitespace-nowrap transition",
                  isActive
                    ? "bg-[var(--surface-2)] text-[var(--text)] shadow-sm"
                    : "text-[var(--text-muted)] hover:text-[var(--text)]"
                )}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </section>

      {settingsQuery.isLoading ? (
        <section className="app-panel flex items-center gap-3 p-6 text-sm text-[var(--text-muted)]">
          <LoaderCircle className="h-4 w-4 animate-spin text-[var(--primary)]" />
          Loading settings
        </section>
      ) : null}

      {settings && activeTab === "profile" ? (
        <section className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)] xl:gap-6">
          <div className="app-panel p-5 sm:p-6">
            <div
              className={cn(
                "grid h-28 w-28 place-items-center rounded-[2rem] text-3xl font-semibold text-white shadow-[var(--shadow-soft)]",
                settings.profile.avatarColor
              )}
            >
              {settings.profile.avatarInitials}
            </div>
            <button
              type="button"
              onClick={() => openProfileEditor(settings.profile)}
              className="mt-5 inline-flex h-10 items-center gap-2 rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text)] transition hover:bg-[var(--surface-2)]"
            >
              <Pencil className="h-4 w-4" />
              Edit avatar and profile
            </button>
            <p className="mt-4 text-sm leading-6 text-[var(--text-muted)]">
              Avatar initials update from your username in this mock flow. A future upload rail can
              replace this with image storage.
            </p>
          </div>

          <div className="app-panel p-5 sm:p-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-[var(--text)]">Profile details</h2>
                <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
                  Keep identity fields accurate for invoices, jobs, and owner listings.
                </p>
              </div>
              <span className="app-status-badge" data-tone="default">
                {roleLabel(settings.profile.role)}
              </span>
            </div>

            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <div className="app-subtle p-4">
                <p className="text-sm text-[var(--text-muted)]">Username</p>
                <p className="mt-2 text-lg font-semibold text-[var(--text)]">
                  {settings.profile.username}
                </p>
              </div>
              <div className="app-subtle p-4">
                <p className="text-sm text-[var(--text-muted)]">Email</p>
                <p className="mt-2 text-lg font-semibold break-all text-[var(--text)]">
                  {settings.profile.email}
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => openProfileEditor(settings.profile)}
              className="mt-6 inline-flex h-11 items-center gap-2 rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)]"
            >
              <Pencil className="h-4 w-4" />
              Edit Profile
            </button>
          </div>
        </section>
      ) : null}

      {settings && activeTab === "security" ? (
        <section className="grid gap-4 lg:grid-cols-3 xl:gap-6">
          {[
            {
              title: "Password",
              detail: "Last changed 18 days ago. Require a strong password before withdrawals.",
              icon: LockKeyhole,
            },
            {
              title: "Two-factor auth",
              detail: "Authenticator app enabled for sign-in and API key creation.",
              icon: ShieldCheck,
            },
            {
              title: "Session safety",
              detail: "New device alerts are active and stale sessions are cleared automatically.",
              icon: Check,
            },
          ].map((item) => {
            const Icon = item.icon;

            return (
              <article key={item.title} className="app-panel p-5 sm:p-6">
                <div className="grid h-12 w-12 place-items-center rounded-2xl bg-[var(--primary-soft)] text-[var(--primary)]">
                  <Icon className="h-5 w-5" />
                </div>
                <h2 className="mt-5 text-lg font-semibold text-[var(--text)]">{item.title}</h2>
                <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">{item.detail}</p>
              </article>
            );
          })}
        </section>
      ) : null}

      {settings && activeTab === "apiKeys" ? (
        <section className="app-panel p-5 sm:p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-[var(--text)]">API key management</h2>
              <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
                Existing keys show environment, prefix, and creation metadata. Full secrets are only
                displayed once when generated.
              </p>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <select
                value={keyEnvironment}
                onChange={(event) =>
                  setKeyEnvironment(event.target.value as UserSettingsApiKey["environment"])
                }
                className="h-11 rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 text-sm font-medium text-[var(--text)] outline-none focus:border-[var(--primary)]"
              >
                <option>Development</option>
                <option>Production</option>
              </select>
              <button
                type="button"
                onClick={() => void generateKey()}
                disabled={generatingKey}
                className="inline-flex h-11 items-center justify-center gap-2 rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] disabled:opacity-60"
              >
                {generatingKey ? (
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
                Generate New Key
              </button>
            </div>
          </div>

          <div className="mt-6 space-y-3">
            {settings.apiKeys.length === 0 ? (
              <div className="app-subtle p-6 text-sm text-[var(--text-muted)]">
                No API keys yet. Generate a key when you are ready to connect an integration.
              </div>
            ) : null}

            {settings.apiKeys.map((apiKey) => (
              <article
                key={apiKey.id}
                className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4"
              >
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className="app-status-badge"
                        data-tone={apiKey.environment === "Production" ? "default" : "accent"}
                      >
                        {apiKey.environment}
                      </span>
                      <code className="rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1 text-sm text-[var(--text)]">
                        {apiKey.prefix}...
                      </code>
                    </div>
                    <p className="mt-3 text-sm text-[var(--text-muted)]">
                      Created {dateFormatter.format(new Date(apiKey.createdAt))}
                      {apiKey.lastUsedAt
                        ? ` / Last used ${dateFormatter.format(new Date(apiKey.lastUsedAt))}`
                        : " / Never used"}
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => void copyValue(apiKey.prefix, apiKey.id)}
                      className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text)] transition hover:bg-[var(--surface-2)]"
                    >
                      {copiedValue === apiKey.id ? (
                        <Check className="h-4 w-4 text-[var(--accent)]" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                      {copiedValue === apiKey.id ? "Copied prefix" : "Copy prefix"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setKeyToRevoke(apiKey)}
                      className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--danger)]/25 px-4 text-sm font-medium text-[var(--danger)] transition hover:bg-[var(--danger-soft)]"
                    >
                      <Trash2 className="h-4 w-4" />
                      Revoke
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {settings && activeTab === "notifications" ? (
        <section className="app-panel p-5 sm:p-6">
          <h2 className="text-lg font-semibold text-[var(--text)]">Notification preferences</h2>
          <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
            Toggle changes are saved immediately through the settings API.
          </p>

          <div className="mt-6 space-y-3">
            {settings.notifications.map((notification) => (
              <article
                key={notification.id}
                className="flex flex-col gap-4 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0">
                  <p className="font-semibold text-[var(--text)]">{notification.label}</p>
                  <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
                    {notification.description}
                  </p>
                </div>
                <Toggle
                  enabled={notification.enabled}
                  disabled={updatingNotificationId === notification.id}
                  onClick={() => void toggleNotification(notification)}
                />
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {settings && activeTab === "billing" ? (
        <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px] xl:gap-6">
          <div className="app-panel p-5 sm:p-6">
            <h2 className="text-lg font-semibold text-[var(--text)]">Billing</h2>
            <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
              USDC billing is connected to the wallet rail. Invoices, escrow movement, and owner
              payouts stay reconciled through the transaction ledger.
            </p>
            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              <div className="app-subtle p-4">
                <p className="text-sm text-[var(--text-muted)]">Default currency</p>
                <p className="mt-2 font-semibold text-[var(--text)]">USDC</p>
              </div>
              <div className="app-subtle p-4">
                <p className="text-sm text-[var(--text-muted)]">Payment rail</p>
                <p className="mt-2 font-semibold text-[var(--text)]">Circle</p>
              </div>
              <div className="app-subtle p-4">
                <p className="text-sm text-[var(--text-muted)]">Invoice email</p>
                <p className="mt-2 truncate font-semibold text-[var(--text)]">
                  {settings.profile.email}
                </p>
              </div>
            </div>
          </div>
          <div className="app-panel p-5 sm:p-6">
            <CreditCard className="h-6 w-6 text-[var(--primary)]" />
            <h3 className="mt-4 font-semibold text-[var(--text)]">Billing controls</h3>
            <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
              Wallet deposits and withdrawals are managed from the wallet page while this tab keeps
              account-level billing metadata visible.
            </p>
          </div>
        </section>
      ) : null}

      {editingProfile ? (
        <Modal title="Edit profile" onClose={() => setEditingProfile(false)}>
          <div className="mt-5 space-y-4">
            <label className="grid gap-2 text-sm">
              <span className="font-medium text-[var(--text)]">Username</span>
              <input
                value={usernameDraft}
                onChange={(event) => setUsernameDraft(event.target.value)}
                className="h-11 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-[var(--text)] outline-none focus:border-[var(--primary)]"
                placeholder="maya-buyer"
              />
            </label>
            <label className="grid gap-2 text-sm">
              <span className="font-medium text-[var(--text)]">Email</span>
              <input
                value={emailDraft}
                onChange={(event) => setEmailDraft(event.target.value)}
                className="h-11 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-[var(--text)] outline-none focus:border-[var(--primary)]"
                placeholder="you@example.com"
                type="email"
              />
            </label>
            {profileError ? (
              <div className="rounded-2xl border border-[var(--danger)]/25 bg-[var(--danger-soft)] p-3 text-sm text-[var(--danger)]">
                {profileError}
              </div>
            ) : null}
            <button
              type="button"
              onClick={() => void saveProfile()}
              disabled={savingProfile || !usernameDraft.trim() || !emailDraft.trim()}
              className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)] disabled:opacity-60"
            >
              {savingProfile ? (
                <LoaderCircle className="h-4 w-4 animate-spin" />
              ) : (
                <Check className="h-4 w-4" />
              )}
              Save profile
            </button>
          </div>
        </Modal>
      ) : null}

      {generatedKey ? (
        <Modal title="New API key generated" onClose={() => setGeneratedKey(null)}>
          <div className="mt-5 space-y-4">
            <div className="rounded-2xl border border-[var(--accent)]/25 bg-[var(--accent-soft)] p-4 text-sm leading-6 text-[var(--text)]">
              This is the only time the full key will be shown. Store it somewhere safe before
              closing this modal.
            </div>
            <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface-2)] p-4">
              <p className="text-sm font-medium text-[var(--text-muted)]">
                {generatedKey.key.environment} key
              </p>
              <code className="mt-3 block text-sm break-all text-[var(--text)]">
                {generatedKey.fullKey}
              </code>
            </div>
            <button
              type="button"
              onClick={() => void copyValue(generatedKey.fullKey, "generated-key")}
              className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-soft)]"
            >
              {copiedValue === "generated-key" ? (
                <Check className="h-4 w-4" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
              {copiedValue === "generated-key" ? "Copied full key" : "Copy full key"}
            </button>
          </div>
        </Modal>
      ) : null}

      {keyToRevoke ? (
        <Modal title="Revoke API key?" onClose={() => setKeyToRevoke(null)}>
          <div className="mt-5 space-y-4">
            <p className="text-sm leading-6 text-[var(--text-muted)]">
              This will immediately disable the {keyToRevoke.environment.toLowerCase()} key with
              prefix <span className="font-semibold text-[var(--text)]">{keyToRevoke.prefix}</span>.
              Any connected integration using it will stop working.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                onClick={() => setKeyToRevoke(null)}
                className="inline-flex h-11 flex-1 items-center justify-center rounded-full border border-[var(--border)] px-5 text-sm font-semibold text-[var(--text)]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => void revokeKey()}
                disabled={revokingKey}
                className="inline-flex h-11 flex-1 items-center justify-center gap-2 rounded-full bg-[var(--danger)] px-5 text-sm font-semibold text-white disabled:opacity-60"
              >
                {revokingKey ? (
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4" />
                )}
                Revoke key
              </button>
            </div>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
