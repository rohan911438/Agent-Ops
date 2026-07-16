import { NextResponse, type NextMiddleware } from "next/server";
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isPublicRoute = createRouteMatcher(["/", "/sign-in(.*)", "/sign-up(.*)"]);

// Clerk isn't configured until NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY /
// CLERK_SECRET_KEY are set (see apps/web/.env.example). Rather than throw
// on every request in local dev, fall through to a no-op middleware —
// mirrors the API's auth_enabled check in app/config.py.
const clerkConfigured = Boolean(
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY && process.env.CLERK_SECRET_KEY,
);

const middleware: NextMiddleware = clerkConfigured
  ? clerkMiddleware(async (auth, req) => {
      if (!isPublicRoute(req)) {
        await auth.protect();
      }
    })
  : () => NextResponse.next();

export default middleware;

export const config = {
  matcher: ["/((?!_next|.*\\..*).*)", "/(api|trpc)(.*)"],
};
