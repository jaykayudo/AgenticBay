"use client";

import { isValidElement, useState } from "react";
import type { ReactElement } from "react";

interface TabItemProps {
  label: string;
  children: React.ReactNode;
}

interface TabsProps {
  children: React.ReactNode;
}

export function DocsTabItem({ children }: TabItemProps) {
  return <>{children}</>;
}

function isTabItem(el: unknown): el is ReactElement<TabItemProps> {
  return isValidElement(el) && typeof (el as ReactElement<TabItemProps>).props.label === "string";
}

export function DocsTabs({ children }: TabsProps) {
  const items = (Array.isArray(children) ? children : [children]).filter(isTabItem);
  const [active, setActive] = useState(0);

  if (items.length === 0) return null;

  return (
    <div className="my-6 overflow-hidden rounded-lg border border-border">
      <div className="flex overflow-x-auto border-b border-border bg-muted/30">
        {items.map((item, i) => (
          <button
            key={i}
            onClick={() => setActive(i)}
            className={`shrink-0 px-4 py-2.5 text-sm font-medium transition-colors ${
              active === i
                ? "border-b-2 border-primary text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {item.props.label}
          </button>
        ))}
      </div>
      <div className="p-4">{items[active]?.props.children ?? null}</div>
    </div>
  );
}
