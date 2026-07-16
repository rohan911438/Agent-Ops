import type { Metadata } from "next";
import { QueryProvider } from "@/lib/query-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentOps Cloud — The Enterprise Control Plane for AI Agents",
  description:
    "Discover, observe, and optimize every AI agent running across your enterprise.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
