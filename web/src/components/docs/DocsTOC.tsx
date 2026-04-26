"use client";

import { useEffect, useState } from "react";

interface Heading {
  id: string;
  text: string;
  level: number;
}

function extractHeadings(): Heading[] {
  const elements = document.querySelectorAll<HTMLElement>(".docs-prose h2, .docs-prose h3");
  return Array.from(elements).map((el) => ({
    id: el.id,
    text: el.textContent?.replace(/#$/, "").trim() ?? "",
    level: Number(el.tagName[1]),
  }));
}

export function DocsTOC() {
  const [headings, setHeadings] = useState<Heading[]>([]);
  const [active, setActive] = useState<string>("");

  useEffect(() => {
    setHeadings(extractHeadings());

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.find((e) => e.isIntersecting);
        if (visible) setActive(visible.target.id);
      },
      { rootMargin: "0px 0px -60% 0px", threshold: 0 }
    );

    document
      .querySelectorAll(".docs-prose h2, .docs-prose h3")
      .forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, []);

  if (headings.length === 0) return null;

  return (
    <nav className="py-6 pl-4">
      <p className="mb-3 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
        On this page
      </p>
      <ul className="space-y-1">
        {headings.map((h) => (
          <li key={h.id} style={{ paddingLeft: h.level === 3 ? "0.75rem" : 0 }}>
            <a
              href={`#${h.id}`}
              className={`block text-sm transition-colors ${
                active === h.id
                  ? "font-medium text-primary"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {h.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
