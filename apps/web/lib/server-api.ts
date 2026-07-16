import { auth } from "@clerk/nextjs/server";
import { apiFetch } from "./api-client";

/** Server-side fetch helper — attaches the Clerk session token when one
 * exists. In local dev (no Clerk keys configured) this resolves to no
 * token, which the API accepts since auth is skipped when unconfigured. */
export async function serverApiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let token: string | null = null;
  try {
    token = await (await auth()).getToken();
  } catch {
    token = null;
  }
  return apiFetch<T>(path, init, token);
}
