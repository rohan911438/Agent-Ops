const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

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

  const res = await fetch(`${API_URL}${path}`, {
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
