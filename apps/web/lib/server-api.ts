import { cookies } from "next/headers";
import { apiFetch } from "./api-client";

/** Server-side (RSC) fetch helper. A server-to-server fetch doesn't
 * automatically carry the visiting browser's cookies, so this forwards the
 * incoming request's Cookie header by hand — that's what lets FastAPI see
 * the session cookie issued by POST /auth/wallet/verify. */
export async function serverApiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const cookieStore = await cookies();
  const cookieHeader = cookieStore.toString();

  return apiFetch<T>(path, {
    ...init,
    headers: {
      ...(cookieHeader ? { Cookie: cookieHeader } : {}),
      ...init?.headers,
    },
  });
}
