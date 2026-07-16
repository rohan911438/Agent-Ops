import type { SessionRead } from "@agentops/shared-types";
import { AppSidebar } from "@/components/app-sidebar";
import { SignOutButton } from "@/components/auth/sign-out-button";
import { PageTransition } from "@/components/page-transition";
import { serverApiFetch } from "@/lib/server-api";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  // Never renders a wallet address here — enterprise-first UX keeps the
  // wallet confined to Settings > Wallet (see docs/Architecture.md).
  let session: SessionRead | null = null;
  try {
    session = await serverApiFetch<SessionRead>("/auth/session");
  } catch {
    session = null;
  }

  return (
    <div className="flex h-screen">
      <AppSidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-border/80 px-6">
          <span className="text-xs uppercase tracking-widest font-bold text-muted-foreground">
            {session ? session.organization.name : "Workspace"}
          </span>
          <SignOutButton />
        </header>
        <main className="flex-1 overflow-y-auto p-8">
          <PageTransition>{children}</PageTransition>
        </main>
      </div>
    </div>
  );
}
