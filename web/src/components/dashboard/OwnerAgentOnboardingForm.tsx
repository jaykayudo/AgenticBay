"use client";

import { AlertTriangle, CheckCircle2, LoaderCircle, Plus, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";

import { useAgentValidation } from "@/hooks/useAgentValidation";
import { agentsApi } from "@/lib/api/agents";
import { isApiError } from "@/lib/api/errors";
import { cn } from "@/lib/utils";

type StepKey = "info" | "config" | "price" | "review";

type ActionRow = {
  id: string;
  name: string;
  priceUsdc: string;
};

type EndpointCheckResult = {
  path: string;
  ok: boolean;
  message: string;
};

type DraftPayload = {
  agentName: string;
  description: string;
  category: string;
  tags: string[];
  externalEndpointUrl: string;
  profileImageData?: string;
  actions: ActionRow[];
};

const steps: Array<{ key: StepKey; label: string }> = [
  { key: "info", label: "Info" },
  { key: "config", label: "Config" },
  { key: "price", label: "Price" },
  { key: "review", label: "Review" },
];

const categories = [
  "Research",
  "Automation",
  "Development",
  "Customer Support",
  "Security",
  "Data Analysis",
  "Design",
  "Content",
];

const endpointChecklist = ["GET /capabilities", "POST /connect", "WS /ws/service/{session_id}"];

function createActionRow(): ActionRow {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    name: "",
    priceUsdc: "",
  };
}

export function OwnerAgentOnboardingForm() {
  const [currentStep, setCurrentStep] = useState(0);
  const [agentName, setAgentName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [tagInput, setTagInput] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [externalEndpointUrl, setExternalEndpointUrl] = useState("");
  const [profileImageData, setProfileImageData] = useState<string | undefined>();
  const [actions, setActions] = useState<ActionRow[]>([createActionRow()]);
  const [stepError, setStepError] = useState<string | null>(null);
  const [pendingNotice, setPendingNotice] = useState<string | null>(null);
  const [endpointResults, setEndpointResults] = useState<EndpointCheckResult[]>([]);
  const [isSavingDraft, setIsSavingDraft] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const validation = useAgentValidation();

  const stepKey = steps[currentStep].key;

  const payload = useMemo<DraftPayload>(
    () => ({
      agentName: agentName.trim(),
      description: description.trim(),
      category,
      tags,
      externalEndpointUrl: externalEndpointUrl.trim(),
      profileImageData,
      actions,
    }),
    [actions, agentName, category, description, externalEndpointUrl, profileImageData, tags]
  );

  function addTag() {
    const next = tagInput.trim();
    if (!next || tags.includes(next)) {
      return;
    }
    setTags((current) => [...current, next]);
    setTagInput("");
  }

  function removeTag(tag: string) {
    setTags((current) => current.filter((item) => item !== tag));
  }

  function updateAction(id: string, updates: Partial<ActionRow>) {
    setActions((current) =>
      current.map((row) => {
        if (row.id !== id) {
          return row;
        }
        return { ...row, ...updates };
      })
    );
  }

  function removeAction(id: string) {
    setActions((current) =>
      current.length <= 1 ? current : current.filter((row) => row.id !== id)
    );
  }

  function validateStep(step: StepKey) {
    if (step === "info") {
      if (!agentName.trim()) {
        return "Agent name is required.";
      }
      if (description.trim().length < 30) {
        return "Description must be at least 30 characters for meaningful vector search indexing.";
      }
      if (!category) {
        return "Select a category before continuing.";
      }
      return null;
    }

    if (step === "config") {
      if (!externalEndpointUrl.trim()) {
        return "External endpoint URL is required.";
      }

      try {
        new URL(externalEndpointUrl.trim());
      } catch {
        return "External endpoint URL must be a valid URL.";
      }
      return null;
    }

    if (step === "price") {
      const valid = actions.filter(
        (row) =>
          row.name.trim() && Number.isFinite(Number(row.priceUsdc)) && Number(row.priceUsdc) > 0
      );
      if (valid.length === 0) {
        return "Add at least one action with a positive USDC price.";
      }
      return null;
    }

    return null;
  }

  async function saveDraft() {
    setIsSavingDraft(true);
    try {
      window.localStorage.setItem("agenticbay.owner.agentDraft", JSON.stringify(payload));
      setPendingNotice("Draft saved locally.");
    } finally {
      setIsSavingDraft(false);
    }
  }

  async function nextStep() {
    setStepError(null);
    const validationError = validateStep(stepKey);
    if (validationError) {
      setStepError(validationError);
      return;
    }

    await saveDraft();
    setCurrentStep((index) => Math.min(index + 1, steps.length - 1));
  }

  function prevStep() {
    setStepError(null);
    setCurrentStep((index) => Math.max(index - 1, 0));
  }

  async function runEndpointCheck() {
    setStepError(null);
    const validationError = validateStep("config");
    if (validationError) {
      setStepError(validationError);
      return;
    }

    try {
      const result = await validation.validate(payload.externalEndpointUrl);
      const results = endpointChecklist.map((path) => ({
        path,
        ok: result.ok,
        message: result.ok ? "Validated" : "Failed",
      }));
      setEndpointResults(results);

      if (!result.ok) {
        setStepError("Endpoint validation failed. Review the service response and try again.");
      }
    } catch (error) {
      setEndpointResults(
        endpointChecklist.map((path) => ({
          path,
          ok: false,
          message: "Failed",
        }))
      );
      setStepError(
        isApiError(error)
          ? `Endpoint validation failed: ${error.message}`
          : "Endpoint validation failed."
      );
    }
  }

  async function submitForReview() {
    setStepError(null);
    setPendingNotice(null);

    const infoError = validateStep("info");
    const configError = validateStep("config");
    const priceError = validateStep("price");
    const firstError = infoError ?? configError ?? priceError;
    if (firstError) {
      setStepError(firstError);
      return;
    }

    setIsSubmitting(true);
    try {
      await agentsApi.submit({
        name: payload.agentName,
        description: payload.description,
        base_url: payload.externalEndpointUrl,
        categories: [payload.category.toLowerCase().replace(/\s+/g, "-")],
        tags: payload.tags,
        pricing_summary: Object.fromEntries(
          payload.actions
            .filter((row) => row.name.trim())
            .map((row) => [row.name.trim(), Number(row.priceUsdc)])
        ),
        profile_image_data: payload.profileImageData,
        actions: payload.actions
          .filter((row) => row.name.trim())
          .map((row) => ({
            name: row.name.trim(),
            description: row.name.trim(),
            priceUsdc: Number(row.priceUsdc),
          })),
      });
      window.localStorage.removeItem("agenticbay.owner.agentDraft");
      setPendingNotice("Agent submitted for review.");
    } catch (error) {
      setStepError(isApiError(error) ? error.message : "Agent submission failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  const isBusy = isSavingDraft || validation.isValidating || isSubmitting;

  function handleImageUpload(file: File | undefined) {
    if (!file) {
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        setProfileImageData(reader.result);
      }
    };
    reader.readAsDataURL(file);
  }

  return (
    <div className="space-y-6">
      <section className="app-panel p-5 sm:p-6">
        <p className="text-xs font-semibold tracking-[0.18em] text-[var(--text-muted)] uppercase">
          Step progress
        </p>
        <ol className="mt-4 grid gap-3 sm:grid-cols-4">
          {steps.map((step, index) => (
            <li
              key={step.key}
              className={cn(
                "rounded-2xl border px-3 py-3 text-sm",
                index === currentStep
                  ? "border-[var(--primary)] bg-[var(--primary-soft)] text-[var(--text)]"
                  : index < currentStep
                    ? "border-emerald-300 bg-emerald-50 text-emerald-900"
                    : "border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-muted)]"
              )}
            >
              <p className="text-xs tracking-[0.16em] uppercase">Step {index + 1}</p>
              <p className="mt-1 font-medium">{step.label}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="app-panel p-5 sm:p-6">
        {stepKey === "info" ? (
          <div className="space-y-5">
            <h2 className="text-lg font-semibold text-[var(--text)]">Agent Information</h2>

            <div className="grid gap-4">
              <label className="grid gap-2 text-sm">
                <span className="font-medium text-[var(--text)]">Agent name</span>
                <input
                  value={agentName}
                  onChange={(event) => setAgentName(event.target.value)}
                  className="h-11 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-[var(--text)]"
                  placeholder="Northstar Research"
                />
              </label>

              <label className="grid gap-2 text-sm">
                <span className="font-medium text-[var(--text)]">Description</span>
                <textarea
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  className="min-h-28 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-[var(--text)]"
                  placeholder="Describe your agent capabilities. This will be used for vector search relevance."
                />
              </label>

              <label className="grid gap-2 text-sm">
                <span className="font-medium text-[var(--text)]">Category</span>
                <select
                  value={category}
                  onChange={(event) => setCategory(event.target.value)}
                  className="h-11 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-[var(--text)]"
                >
                  <option value="">Select category</option>
                  {categories.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>

              <div className="grid gap-2 text-sm">
                <span className="font-medium text-[var(--text)]">Tags</span>
                <div className="flex gap-2">
                  <input
                    value={tagInput}
                    onChange={(event) => setTagInput(event.target.value)}
                    className="h-11 flex-1 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-[var(--text)]"
                    placeholder="Add a tag"
                  />
                  <button
                    type="button"
                    onClick={addTag}
                    className="inline-flex h-11 items-center justify-center rounded-xl border border-[var(--border)] px-4 text-sm font-medium text-[var(--text)]"
                  >
                    Add
                  </button>
                </div>
                {tags.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {tags.map((tag) => (
                      <button
                        key={tag}
                        type="button"
                        onClick={() => removeTag(tag)}
                        className="inline-flex items-center rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1 text-xs text-[var(--text)]"
                      >
                        {tag} ×
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>

              <label className="grid gap-2 text-sm">
                <span className="font-medium text-[var(--text)]">Profile image</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(event) => handleImageUpload(event.target.files?.[0])}
                  className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-[var(--text)]"
                />
                {profileImageData ? (
                  <span className="text-sm text-emerald-700">
                    Image attached and will be uploaded with the agent submission.
                  </span>
                ) : null}
              </label>
            </div>
          </div>
        ) : null}

        {stepKey === "config" ? (
          <div className="space-y-5">
            <h2 className="text-lg font-semibold text-[var(--text)]">Configuration</h2>

            <label className="grid gap-2 text-sm">
              <span className="font-medium text-[var(--text)]">
                External endpoint URL
              </span>
              <input
                value={externalEndpointUrl}
                onChange={(event) => setExternalEndpointUrl(event.target.value)}
                className="h-11 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-[var(--text)]"
                placeholder="https://agent.example.com"
              />
            </label>

            <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
              Endpoint checks run during onboarding; any failing required path blocks submission.
            </div>

            <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface-2)] p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm font-medium text-[var(--text)]">Required API paths</p>
                <button
                  type="button"
                  onClick={runEndpointCheck}
                  disabled={validation.isValidating}
                  className="inline-flex h-10 items-center justify-center rounded-full bg-[var(--primary)] px-4 text-sm font-semibold text-[var(--primary-foreground)] disabled:opacity-60"
                >
                  {validation.isValidating ? "Checking..." : "Validate Endpoints"}
                </button>
              </div>
              <ul className="mt-3 space-y-2 text-sm text-[var(--text-muted)]">
                {endpointChecklist.map((path) => {
                  const result = endpointResults.find((item) => item.path === path);
                  return (
                    <li key={path} className="flex items-center justify-between gap-3">
                      <span>{path}</span>
                      {result ? (
                        <span
                          className={cn(
                            "inline-flex items-center gap-1 text-xs",
                            result.ok ? "text-emerald-700" : "text-rose-700"
                          )}
                        >
                          {result.ok ? (
                            <CheckCircle2 className="h-3.5 w-3.5" />
                          ) : (
                            <AlertTriangle className="h-3.5 w-3.5" />
                          )}
                          {result.message}
                        </span>
                      ) : (
                        <span className="text-xs">Not checked</span>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
        ) : null}

        {stepKey === "price" ? (
          <div className="space-y-5">
            <h2 className="text-lg font-semibold text-[var(--text)]">Pricing</h2>

            <div className="space-y-3">
              {actions.map((row) => (
                <div
                  key={row.id}
                  className="grid gap-2 rounded-2xl border border-[var(--border)] p-3 sm:grid-cols-[1fr_160px_auto]"
                >
                  <input
                    value={row.name}
                    onChange={(event) => updateAction(row.id, { name: event.target.value })}
                    className="h-11 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-sm text-[var(--text)]"
                    placeholder="Action name"
                  />
                  <input
                    value={row.priceUsdc}
                    onChange={(event) => updateAction(row.id, { priceUsdc: event.target.value })}
                    className="h-11 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-sm text-[var(--text)]"
                    placeholder="USDC price"
                    inputMode="decimal"
                  />
                  <button
                    type="button"
                    onClick={() => removeAction(row.id)}
                    className="inline-flex h-11 items-center justify-center rounded-xl border border-[var(--border)] px-3 text-[var(--text-muted)]"
                    aria-label="Remove action row"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>

            <button
              type="button"
              onClick={() => setActions((current) => [...current, createActionRow()])}
              className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text)]"
            >
              <Plus className="h-4 w-4" />
              Add Action
            </button>
          </div>
        ) : null}

        {stepKey === "review" ? (
          <div className="space-y-5">
            <h2 className="text-lg font-semibold text-[var(--text)]">Review</h2>
            <div className="grid gap-4 text-sm sm:grid-cols-2">
              <div className="rounded-2xl border border-[var(--border)] p-4">
                <p className="text-xs tracking-[0.16em] text-[var(--text-muted)] uppercase">
                  Agent
                </p>
                <p className="mt-2 font-medium text-[var(--text)]">{agentName || "-"}</p>
                <p className="mt-1 text-[var(--text-muted)]">
                  {category || "No category selected"}
                </p>
              </div>
              <div className="rounded-2xl border border-[var(--border)] p-4 sm:col-span-2">
                <p className="text-xs tracking-[0.16em] text-[var(--text-muted)] uppercase">
                  Description
                </p>
                <p className="mt-2 text-[var(--text)]">{description || "-"}</p>
              </div>
              <div className="rounded-2xl border border-[var(--border)] p-4 sm:col-span-2">
                <p className="text-xs tracking-[0.16em] text-[var(--text-muted)] uppercase">
                  Actions
                </p>
                <ul className="mt-2 space-y-1">
                  {actions
                    .filter((row) => row.name.trim())
                    .map((row) => (
                      <li key={row.id} className="text-[var(--text)]">
                        {row.name} - {row.priceUsdc || "0"} USDC
                      </li>
                    ))}
                </ul>
              </div>
            </div>

            <button
              type="button"
              onClick={submitForReview}
              disabled={isSubmitting}
              className="inline-flex h-11 items-center justify-center rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] disabled:opacity-60"
            >
              {isSubmitting ? "Submitting..." : "Submit for Review"}
            </button>

            {pendingNotice ? (
              <div className="rounded-2xl border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-900">
                {pendingNotice}
              </div>
            ) : null}
          </div>
        ) : null}

        {stepError ? (
          <div className="mt-5 rounded-2xl border border-rose-300 bg-rose-50 p-3 text-sm text-rose-800">
            {stepError}
          </div>
        ) : null}

        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--border)] pt-5">
          <button
            type="button"
            onClick={prevStep}
            disabled={currentStep === 0 || isBusy}
            className="inline-flex h-10 items-center justify-center rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text)] disabled:opacity-50"
          >
            Back
          </button>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={saveDraft}
              disabled={isBusy}
              className="inline-flex h-10 items-center justify-center rounded-full border border-[var(--border)] px-4 text-sm font-medium text-[var(--text)] disabled:opacity-50"
            >
              {isSavingDraft ? "Saving..." : "Save draft"}
            </button>
            <button
              type="button"
              onClick={nextStep}
              disabled={currentStep === steps.length - 1 || isBusy}
              className="inline-flex h-10 items-center justify-center rounded-full bg-[var(--primary)] px-4 text-sm font-semibold text-[var(--primary-foreground)] disabled:opacity-50"
            >
              {isBusy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : "Next"}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
