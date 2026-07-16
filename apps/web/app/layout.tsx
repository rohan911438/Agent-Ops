import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { QueryProvider } from "@/lib/query-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentOps Cloud — The Enterprise Control Plane for AI Agents",
  description:
    "Discover, observe, and optimize every AI agent running across your enterprise.",
};

// Mirrors middleware.ts: ClerkProvider requires a publishable key, so it's
// only mounted once Clerk is actually configured — local dev works without
// ever creating a Clerk project.
const clerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

function Providers({ children }: { children: React.ReactNode }) {
  if (clerkConfigured) {
    return <ClerkProvider>{children}</ClerkProvider>;
  }
  return <>{children}</>;
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <Providers>
      <html lang="en" className="dark">
        <body>
          <QueryProvider>{children}</QueryProvider>
        </body>
      </html>
    </Providers>
  );
}
