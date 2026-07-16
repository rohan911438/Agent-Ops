"use client";

import { usePathname } from "next/navigation";
import { Sidebar, type SidebarItem } from "@agentops/ui";

const navItems: SidebarItem[] = [
  { label: "Health Scan", href: "/health-scan" },
  { label: "Overview", href: "/overview" },
  { label: "Agents", href: "/agents" },
  { label: "Recommendations", href: "/recommendations" },
  { label: "Activity", href: "/activity" },
  { label: "Settings", href: "/settings" },
];

export function AppSidebar() {
  const pathname = usePathname();
  return (
    <Sidebar
      items={navItems}
      activeHref={pathname}
      header={<span className="text-sm font-semibold tracking-tight">AgentOps Cloud</span>}
    />
  );
}
