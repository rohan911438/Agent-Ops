import { NextResponse, type NextMiddleware } from "next/server";
import { jwtVerify } from "jose";

const SESSION_COOKIE_NAME = "agentops_session";
const PUBLIC_PATHS = new Set(["/"]);

// Mirrors apps/api's AUTH_DISABLED default (true) so a fresh clone with no
// env configured still loads the dashboard directly — see
// docs/Architecture.md. Verifies the same HS256 cookie FastAPI issues
// (SESSION_JWT_SECRET must match the API's SESSION_SECRET_KEY) at the edge,
// with no round-trip to the API.
const INSECURE_DEFAULT_SESSION_SECRET = "dev-insecure-secret-change-me";
const authDisabled = process.env.AUTH_DISABLED !== "false";
const sessionSecretEnv = process.env.SESSION_JWT_SECRET || INSECURE_DEFAULT_SESSION_SECRET;

// Same insecure-default check as apps/api/app/config.py's
// _reject_insecure_production_config — see
// docs/ASP-6262-Production-Readiness-Audit.md finding C-2. Next.js
// middleware has no single startup hook, so this throws at module
// evaluation time instead, which still fails the build/boot rather than
// silently serving an open, publicly-known-secret session cookie.
if (
  process.env.NODE_ENV === "production" &&
  (authDisabled || sessionSecretEnv === INSECURE_DEFAULT_SESSION_SECRET)
) {
  throw new Error(
    "Insecure configuration for NODE_ENV=production: AUTH_DISABLED must be " +
      "\"false\" and SESSION_JWT_SECRET must be set to a real secret (matching " +
      "the API's SESSION_SECRET_KEY).",
  );
}

const secret = new TextEncoder().encode(sessionSecretEnv);

function isPublicPath(pathname: string) {
  return PUBLIC_PATHS.has(pathname) || pathname.startsWith("/_next");
}

const middleware: NextMiddleware = async (req) => {
  const { pathname } = req.nextUrl;
  if (authDisabled || isPublicPath(pathname)) {
    return NextResponse.next();
  }

  const token = req.cookies.get(SESSION_COOKIE_NAME)?.value;
  if (token) {
    try {
      await jwtVerify(token, secret);
      return NextResponse.next();
    } catch {
      // falls through to the redirect below — invalid/expired session
    }
  }

  const url = req.nextUrl.clone();
  url.pathname = "/";
  return NextResponse.redirect(url);
};

export default middleware;

export const config = {
  // /api/v1/* is a same-origin rewrite proxy to the FastAPI backend (see
  // next.config.ts) — that backend enforces its own session check, and
  // gating it here too would block unauthenticated calls the login flow
  // itself depends on (POST /api/v1/auth/wallet/nonce, /wallet/verify).
  matcher: ["/((?!_next|api|.*\\..*).*)"],
};
