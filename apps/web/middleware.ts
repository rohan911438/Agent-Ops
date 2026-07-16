import { NextResponse, type NextMiddleware } from "next/server";
import { jwtVerify } from "jose";

const SESSION_COOKIE_NAME = "agentops_session";
const PUBLIC_PATHS = new Set(["/"]);

// Mirrors apps/api's AUTH_DISABLED default (true) so a fresh clone with no
// env configured still loads the dashboard directly — see
// docs/Architecture.md. Verifies the same HS256 cookie FastAPI issues
// (SESSION_JWT_SECRET must match the API's SESSION_SECRET_KEY) at the edge,
// with no round-trip to the API.
const authDisabled = process.env.AUTH_DISABLED !== "false";
const secret = new TextEncoder().encode(
  process.env.SESSION_JWT_SECRET || "dev-insecure-secret-change-me",
);

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
  matcher: ["/((?!_next|.*\\..*).*)"],
};
