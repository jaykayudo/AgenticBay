import type { MDXComponents } from "mdx/types";

import { Callout } from "@/components/docs/Callout";
import { DocsTabs, DocsTabItem } from "@/components/docs/DocsTabs";
import { ApiEndpoint } from "@/components/docs/ApiEndpoint";

export function useMDXComponents(components: MDXComponents): MDXComponents {
  return {
    Callout,
    Tabs: DocsTabs,
    Tab: DocsTabItem,
    ApiEndpoint,
    ...components,
  };
}
