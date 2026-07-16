import { UserButton } from "@clerk/nextjs";
import { AppSidebar } from "@/components/app-sidebar";

const clerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen">
      <AppSidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-border px-6">
          <span className="text-sm text-muted-foreground">Workspace</span>
          {clerkConfigured ? (
            <UserButton afterSignOutUrl="/" />
          ) : (
            <span className="text-xs text-muted-foreground">dev mode — auth disabled</span>
          )}
        </header>
        <main className="flex-1 overflow-y-auto p-8">{children}</main>
      </div>
    </div>
  );
}
