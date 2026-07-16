"use client";

import Link from "next/link";
import { cn } from "../lib/utils";

export interface SidebarItem {
  label: string;
  href: string;
  icon?: React.ReactNode;
}

export function Sidebar({
  items,
  activeHref,
  header,
  footer,
}: {
  items: SidebarItem[];
  activeHref: string;
  header?: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <aside className="flex h-full w-60 shrink-0 flex-col border-r border-border bg-card">
      {header && <div className="px-4 py-4">{header}</div>}
      <nav className="flex flex-1 flex-col gap-1 px-3">
        {items.map((item) => {
          const isActive = activeHref === item.href || activeHref.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
              )}
            >
              {item.icon}
              {item.label}
            </Link>
          );
        })}
      </nav>
      {footer && <div className="px-4 py-4">{footer}</div>}
    </aside>
  );
}
