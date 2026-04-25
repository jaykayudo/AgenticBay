"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

import type { PaymentModalData, PromptModalData } from "@/lib/ws/userAgentSocket";

type PaymentResponse = { confirmed: boolean };
type PromptResponse = { answer?: string; selected_option?: string };

type ChatModalContextValue = {
  showPaymentModal: (data: PaymentModalData, onRespond: (response: PaymentResponse) => void) => void;
  showPromptModal: (data: PromptModalData, onRespond: (response: PromptResponse) => void) => void;
};

type ModalState =
  | {
      type: "payment";
      data: PaymentModalData;
      onRespond: (response: PaymentResponse) => void;
    }
  | {
      type: "prompt";
      data: PromptModalData;
      onRespond: (response: PromptResponse) => void;
    }
  | null;

const ChatModalContext = createContext<ChatModalContextValue | null>(null);

export function ChatModalProvider({ children }: { children: ReactNode }) {
  const [modal, setModal] = useState<ModalState>(null);
  const [promptAnswer, setPromptAnswer] = useState("");

  const close = () => {
    setModal(null);
    setPromptAnswer("");
  };

  return (
    <ChatModalContext.Provider
      value={{
        showPaymentModal: (data, onRespond) => setModal({ type: "payment", data, onRespond }),
        showPromptModal: (data, onRespond) => {
          setPromptAnswer("");
          setModal({ type: "prompt", data, onRespond });
        },
      }}
    >
      {children}

      {modal ? (
        <div
          className="fixed inset-0 z-[70] flex items-end justify-center bg-black/45 px-4 py-4 sm:items-center"
          role="dialog"
          aria-modal="true"
        >
          <section className="app-panel w-full max-w-lg p-5 sm:p-6">
            {modal.type === "payment" ? (
              <div className="space-y-5">
                <div>
                  <h2 className="text-lg font-semibold text-[var(--text)]">Confirm payment</h2>
                  <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                    {modal.data.description ?? "Confirm this payment request to continue."}
                  </p>
                </div>
                <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface-2)] p-4">
                  <p className="text-sm text-[var(--text-muted)]">Amount</p>
                  <p className="mt-2 text-2xl font-semibold text-[var(--text)]">
                    {String(modal.data.amount ?? "--")} {String(modal.data.currency ?? "USDC")}
                  </p>
                  {modal.data.invoice_id ?? modal.data.invoiceId ? (
                    <p className="mt-2 break-all text-xs text-[var(--text-muted)]">
                      Invoice: {String(modal.data.invoice_id ?? modal.data.invoiceId)}
                    </p>
                  ) : null}
                </div>
                <div className="flex flex-col gap-3 sm:flex-row">
                  <button
                    type="button"
                    onClick={() => {
                      modal.onRespond({ confirmed: false });
                      close();
                    }}
                    className="inline-flex h-11 flex-1 items-center justify-center rounded-full border border-[var(--border)] px-5 text-sm font-semibold text-[var(--text)]"
                  >
                    Decline
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      modal.onRespond({ confirmed: true });
                      close();
                    }}
                    className="inline-flex h-11 flex-1 items-center justify-center rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)]"
                  >
                    Confirm
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-5">
                <div>
                  <h2 className="text-lg font-semibold text-[var(--text)]">
                    {modal.data.title ?? "Input needed"}
                  </h2>
                  <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                    {modal.data.prompt ?? modal.data.question ?? "Please answer to continue."}
                  </p>
                </div>
                {modal.data.options?.length ? (
                  <div className="grid gap-2">
                    {modal.data.options.map((option) => (
                      <button
                        key={option}
                        type="button"
                        onClick={() => {
                          modal.onRespond({ selected_option: option, answer: option });
                          close();
                        }}
                        className="rounded-2xl border border-[var(--border)] px-4 py-3 text-left text-sm font-medium text-[var(--text)] transition hover:bg-[var(--surface-2)]"
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                ) : (
                  <textarea
                    value={promptAnswer}
                    onChange={(event) => setPromptAnswer(event.target.value)}
                    className="min-h-28 w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-[var(--text)]"
                    placeholder="Type your answer"
                  />
                )}
                <div className="flex flex-col gap-3 sm:flex-row">
                  <button
                    type="button"
                    onClick={close}
                    className="inline-flex h-11 flex-1 items-center justify-center rounded-full border border-[var(--border)] px-5 text-sm font-semibold text-[var(--text)]"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={!modal.data.options?.length && !promptAnswer.trim()}
                    onClick={() => {
                      modal.onRespond({ answer: promptAnswer.trim() });
                      close();
                    }}
                    className="inline-flex h-11 flex-1 items-center justify-center rounded-full bg-[var(--primary)] px-5 text-sm font-semibold text-[var(--primary-foreground)] disabled:opacity-55"
                  >
                    Send response
                  </button>
                </div>
              </div>
            )}
          </section>
        </div>
      ) : null}
    </ChatModalContext.Provider>
  );
}

export function useChatModal() {
  const context = useContext(ChatModalContext);
  if (!context) {
    throw new Error("useChatModal must be used inside ChatModalProvider.");
  }
  return context;
}
