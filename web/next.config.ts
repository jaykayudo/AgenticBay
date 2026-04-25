import createMDX from "@next/mdx";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  pageExtensions: ["js", "jsx", "md", "mdx", "ts", "tsx"],
  turbopack: {
    root: import.meta.dirname,
  },
};

const withMDX = createMDX({});

export default withMDX(nextConfig);
