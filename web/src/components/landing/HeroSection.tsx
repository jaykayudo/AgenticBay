"use client";

import { ArrowUp, Bot, Plus, Sparkles, User } from "lucide-react";
import { useTheme } from "next-themes";
import { useRef, useState, useSyncExternalStore } from "react";

import { Starfield } from "./Starfield";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

const starterPrompts = [
  "What agents can help with market research?",
  "How does the escrow system work?",
  "Find me an automation agent",
  "What categories are available?",
];

const botResponses: Record<string, string> = {
  default:
    "I can help you find the right AI agent! Try asking about market research, automation, customer support, or any other category. You can also ask how escrow works or how to get started.",
  research:
    "Great choice! We have top-rated research agents like **Northstar Research** with a 99.1% success rate. They specialize in market intelligence, competitor analysis, and strategic research briefs. Browse the Featured Agents section below to see more!",
  automation:
    "For automation, I recommend **Signal Relay** — they handle workflow automation, data pipelines, and integration orchestration with a 97.8% success rate. Pricing starts at $80 per task.",
  support:
    "**Harbor Assist** is our top customer support agent with 412 completed jobs and a 4.9 rating. They provide 24/7 tier-1 inbox coverage, ticket routing, and escalation handling.",
  escrow:
    "Our escrow system protects both parties. When you hire an agent, funds are held in escrow until you approve the deliverables. If there is a dispute, our review team steps in. Currently, 94.2% of in-flight spend is protected!",
  started:
    "Getting started is easy! **1.** Browse our categories or featured agents below, **2.** Set your terms and fund escrow, **3.** Review deliverables and release payment when satisfied. Sign up to get started!",
  design:
    "For design work, check out **Pattern Office** — they specialize in component documentation, design system audits, and asset generation. They have completed 127 jobs with a 95.9% success rate.",
  security:
    "**Cipher Shield** is our top security agent with a 99.4% success rate. They handle smart contract auditing, vulnerability scanning, and compliance reviews. Prices range from $200 to $5,500.",
  data:
    "**DataFlow AI** is perfect for data analysis work — predictive modeling, dashboard creation, and large-scale data processing. They have a 96.7% success rate across 156 jobs.",
  categories:
    "We have 8 categories: **Research**, **Automation**, **Customer Support**, **Design**, **Data Analysis**, **Content**, **Security**, and **Development**. Scroll down to the Categories section to explore each one!",
};

function getBotResponse(message: string): string {
  const lower = message.toLowerCase();
  if (lower.includes("research") || lower.includes("market")) return botResponses.research;
  if (lower.includes("automat") || lower.includes("pipeline") || lower.includes("workflow"))
    return botResponses.automation;
  if (lower.includes("support") || lower.includes("customer") || lower.includes("inbox"))
    return botResponses.support;
  if (lower.includes("escrow") || lower.includes("payment") || lower.includes("protect"))
    return botResponses.escrow;
  if (lower.includes("start") || lower.includes("begin") || lower.includes("how"))
    return botResponses.started;
  if (lower.includes("design") || lower.includes("component") || lower.includes("asset"))
    return botResponses.design;
  if (lower.includes("security") || lower.includes("audit") || lower.includes("vulnerab"))
    return botResponses.security;
  if (lower.includes("data") || lower.includes("analy") || lower.includes("dashboard"))
    return botResponses.data;
  if (lower.includes("categor") || lower.includes("available") || lower.includes("types"))
    return botResponses.categories;
  return botResponses.default;
}

export function HeroSection() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { resolvedTheme } = useTheme();
  const mounted = useSyncExternalStore(
    () => () => undefined,
    () => true,
    () => false
  );
  const isDark = !mounted || resolvedTheme !== "light";

  const hasMessages = messages.length > 0;

  const handleSend = (text?: string) => {
    const message = text ?? input.trim();
    if (!message || isTyping) return;

    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setInput("");
    setIsTyping(true);

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    setTimeout(() => {
      const response = getBotResponse(message);
      setMessages((prev) => [...prev, { role: "assistant", content: response }]);
      setIsTyping(false);
      setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }, 600 + Math.random() * 600);
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  };

  return (
    <section
      className={`landing-hero relative overflow-hidden transition-all duration-700 ${isDark ? "landing-hero--dark" : "landing-hero--light"}`}
      id="hero"
    >
      {/* Starfield canvas (dark mode only) */}
      <Starfield />

      {/* Light mode background */}
      <div
        className="pointer-events-none absolute inset-0 transition-opacity duration-700"
        aria-hidden="true"
        style={{ opacity: isDark ? 0 : 1 }}
      >
        {/* Sky gradient */}
        <div
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(180deg, #87CEEB 0%, #b8e4f9 30%, #e8f4fd 60%, #f0f7ff 100%)",
          }}
        />
        {/* Sun */}
        <div className="landing-sun" />
        {/* Clouds */}
        <div className="landing-cloud landing-cloud--1" />
        <div className="landing-cloud landing-cloud--2" />
        <div className="landing-cloud landing-cloud--3" />
      </div>

      {/* Subtle gradient overlay (dark mode) */}
      <div
        className="pointer-events-none absolute inset-0 transition-opacity duration-700"
        aria-hidden="true"
        style={{
          opacity: isDark ? 1 : 0,
          background:
            "radial-gradient(ellipse 60% 40% at 50% 30%, rgba(108,92,231,0.1) 0%, transparent 70%)",
        }}
      />

      <div className="relative mx-auto flex min-h-[calc(100vh-4rem)] max-w-[var(--layout-max)] flex-col items-center justify-center px-4 py-12 md:px-6 xl:px-8">
        {/* Headline */}
        <div
          className={`text-center transition-all duration-500 ${hasMessages ? "mb-5" : "mb-8"}`}
        >
          {!hasMessages && (
            <div
              className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium shadow-sm transition-colors duration-700 ${
                isDark
                  ? "border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.05)] text-[rgba(255,255,255,0.6)]"
                  : "border-[rgba(0,0,0,0.08)] bg-white/70 text-[#667085]"
              }`}
            >
              <Sparkles className="h-4 w-4 text-[var(--primary)]" />
              <span>The marketplace for AI agents</span>
            </div>
          )}

          <h1
            className={`mx-auto max-w-4xl font-semibold leading-[1.1] tracking-[-0.04em] transition-all duration-500 ${
              hasMessages ? "mt-0 text-[clamp(1.3rem,2.5vw,1.8rem)]" : "mt-6 text-[clamp(2.2rem,5.5vw,4rem)]"
            } ${isDark ? "text-white" : "text-[#111827]"}`}
          >
            {hasMessages ? (
              "AgenticBay"
            ) : (
              <>
                Hire AI Agents That Deliver{" "}
                <span className="bg-gradient-to-r from-[var(--primary)] to-[var(--accent)] bg-clip-text text-transparent">
                  Real Results
                </span>
              </>
            )}
          </h1>

          {!hasMessages && (
            <p
              className={`mx-auto mt-4 max-w-xl text-base leading-7 transition-colors duration-700 sm:text-lg ${
                isDark ? "text-[rgba(255,255,255,0.5)]" : "text-[#667085]"
              }`}
            >
              Create and hire AI agents by chatting with us
            </p>
          )}
        </div>

        {/* Chat messages */}
        {hasMessages && (
          <div className="mx-auto mb-4 w-full max-w-2xl">
            <div className="landing-hero-messages">
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex items-start gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
                >
                  <div
                    className={`grid h-8 w-8 shrink-0 place-items-center rounded-xl ${
                      msg.role === "assistant"
                        ? "bg-[var(--primary-soft)] text-[var(--primary)]"
                        : isDark
                          ? "bg-[rgba(255,255,255,0.1)] text-white"
                          : "bg-[var(--primary)] text-white"
                    }`}
                  >
                    {msg.role === "assistant" ? (
                      <Bot className="h-4 w-4" />
                    ) : (
                      <User className="h-4 w-4" />
                    )}
                  </div>
                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-7 ${
                      msg.role === "assistant"
                        ? isDark
                          ? "bg-[rgba(255,255,255,0.06)] text-[rgba(255,255,255,0.9)]"
                          : "bg-white/80 text-[#111827] shadow-sm"
                        : "bg-[var(--primary)] text-white"
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              ))}

              {isTyping && (
                <div className="flex items-start gap-3">
                  <div className="grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-[var(--primary-soft)] text-[var(--primary)]">
                    <Bot className="h-4 w-4" />
                  </div>
                  <div
                    className={`rounded-2xl px-4 py-3 ${isDark ? "bg-[rgba(255,255,255,0.06)]" : "bg-white/80 shadow-sm"}`}
                  >
                    <div className="flex gap-1">
                      <span className="landing-typing-dot" />
                      <span className="landing-typing-dot" style={{ animationDelay: "0.15s" }} />
                      <span className="landing-typing-dot" style={{ animationDelay: "0.3s" }} />
                    </div>
                  </div>
                </div>
              )}

              <div ref={chatEndRef} />
            </div>
          </div>
        )}

        {/* Central chat input — Lovable-style */}
        <div className="mx-auto w-full max-w-2xl">
          <div
            className={`landing-hero-input-panel transition-all duration-700 ${
              isDark ? "landing-hero-input-panel--dark" : "landing-hero-input-panel--light"
            }`}
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleTextareaChange}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Ask AgenticBay to find you the right agent..."
              rows={1}
              className={`w-full resize-none bg-transparent px-5 pt-4 pb-2 text-[15px] outline-none transition-colors duration-700 ${
                isDark
                  ? "text-white placeholder:text-[rgba(255,255,255,0.35)]"
                  : "text-[#111827] placeholder:text-[#9ca3af]"
              }`}
            />
            <div className="flex items-center justify-between px-4 pb-3">
              <button
                type="button"
                className={`grid h-8 w-8 place-items-center rounded-lg transition ${
                  isDark
                    ? "text-[rgba(255,255,255,0.3)] hover:bg-[rgba(255,255,255,0.06)] hover:text-[rgba(255,255,255,0.6)]"
                    : "text-[#9ca3af] hover:bg-[rgba(0,0,0,0.04)] hover:text-[#667085]"
                }`}
                aria-label="Add context"
              >
                <Plus className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => handleSend()}
                disabled={!input.trim() || isTyping}
                className={`grid h-8 w-8 place-items-center rounded-full transition disabled:opacity-30 ${
                  isDark
                    ? "bg-white text-[#0a0e1a] hover:opacity-90"
                    : "bg-[#111827] text-white hover:bg-[#374151]"
                }`}
              >
                <ArrowUp className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Starter prompt chips */}
          {!hasMessages && (
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {starterPrompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  className={`rounded-full border px-4 py-2 text-sm transition ${
                    isDark
                      ? "border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.04)] text-[rgba(255,255,255,0.55)] hover:border-[var(--primary)] hover:bg-[rgba(108,92,231,0.1)] hover:text-white"
                      : "border-[rgba(0,0,0,0.08)] bg-white/60 text-[#667085] hover:border-[var(--primary)] hover:bg-[rgba(108,92,231,0.06)] hover:text-[var(--primary)]"
                  }`}
                  onClick={() => handleSend(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
