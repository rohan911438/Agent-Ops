"use client";

import { usePathname } from "next/navigation";

/** Subtle fade-in on navigation. Keying on pathname forces a remount so the
 * CSS animation (see .page-fade-in in globals.css) restarts on every page
 * change — the layout around it never remounts. */
export function PageTransition({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div key={pathname} className="page-fade-in">
      {children}
    </div>
  );
}
