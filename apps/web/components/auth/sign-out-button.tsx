"use client";

import { useRouter } from "next/navigation";
import { Button, type ButtonProps } from "@agentops/ui";
import { apiFetch } from "@/lib/api-client";

export function SignOutButton({
  children = "Sign out",
  variant = "ghost",
  ...props
}: Partial<ButtonProps>) {
  const router = useRouter();

  async function handleSignOut() {
    await apiFetch("/auth/logout", { method: "POST" });
    router.push("/");
    router.refresh();
  }

  return (
    <Button size="sm" variant={variant} onClick={handleSignOut} {...props}>
      {children}
    </Button>
  );
}
