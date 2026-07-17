import type { NextConfig } from "next";

// Backend origin, no trailing slash (e.g. https://agentops-api.up.railway.app).
// Server-side fetches (lib/server-api.ts) call this directly. Browser fetches
// (lib/api-client.ts) go through the rewrite below instead of this origin
// directly, so the session cookie set on POST /auth/wallet/verify is scoped
// to *this* app's own domain — required for SameSite=Lax to work when the
// frontend (Vercel) and backend (Railway) are on unrelated domains. See
// docs/Architecture.md.
const BACKEND_ORIGIN = process.env.API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  transpilePackages: ["@agentops/ui"],
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${BACKEND_ORIGIN}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
