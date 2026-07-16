"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@agentops/ui";

const tabs = [
  { label: "Workspace", href: "/settings/workspace" },
  { label: "Wallet", href: "/settings/wallet" },
  { label: "API Keys", href: "/settings/api-keys" },
  { label: "Users", href: "/settings/users" },
];

export function SettingsTabs() {
  const pathname = usePathname();
  return (
    <div className="flex gap-1 border-b border-border">
      {tabs.map((tab) => (
        <Link
          key={tab.href}
          href={tab.href}
          className={cn(
            "border-b-2 px-3 py-2 text-sm font-medium",
            pathname === tab.href
              ? "border-foreground text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground",
          )}
        >
          {tab.label}
        </Link>
      ))}
    </div>
  );
}
