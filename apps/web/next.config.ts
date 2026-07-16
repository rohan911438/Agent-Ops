import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@agentops/ui"],
  reactStrictMode: true,
};

export default nextConfig;
