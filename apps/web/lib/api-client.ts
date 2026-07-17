// In the browser, fetches go to a same-origin relative path that
// next.config.ts rewrites to the backend server-side — this keeps the
// session cookie scoped to this app's own domain (required for
// SameSite=Lax when the frontend and backend live on unrelated domains,
// e.g. Vercel + Railway). Server-side (RSC, middleware-adjacent code)
// fetches the backend directly, since Node's fetch has no implicit origin
// to resolve a relative URL against, and there's no browser cookie policy
// to work around for a server-to-server call.
const BROWSER_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const SERVER_API_URL = process.env.API_URL ? `${process.env.API_URL}/api/v1` : BROWSER_API_URL;

function resolveApiUrl(): string {
  return typeof window === "undefined" ? SERVER_API_URL : BROWSER_API_URL;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  // FormData bodies need the browser to set their own multipart boundary —
  // a forced "application/json" here would silently break file uploads.
  const isFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;

  const res = await fetch(`${resolveApiUrl()}${path}`, {
    ...init,
    // Carries the httpOnly session cookie FastAPI set on login — see
    // app/auth/session.py. Works cross-port in local dev and cross-subdomain
    // in prod because both are same-site (SameSite=Lax).
    credentials: "include",
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
    cache: "no-store",
  });

  if (!res.ok) {
    throw new ApiError(res.status, await res.text());
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}
