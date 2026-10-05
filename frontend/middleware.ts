import { NextResponse, type NextRequest } from "next/server";

import { LOGIN_PATH, SESSION_COOKIE, isPublicPath } from "@/lib/auth";

/**
 * Keeps signed-out visitors off the app shell.
 *
 * This is a presence check on the cookie, not a validity check -- the middleware
 * cannot verify a token without calling the API on every navigation. Real
 * enforcement is the backend's `current_user` dependency, which 401s on an
 * expired or unknown session; the API client turns that into the same redirect.
 * So this only saves a pointless render, and a stale cookie still ends up here
 * one request later.
 *
 * Works in development because cookies ignore ports: one set by
 * localhost:8000 is visible to localhost:3000. A deployment that splits the API
 * onto another domain would need the backend to set an explicit `Domain=`.
 */
export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  if (isPublicPath(pathname)) return NextResponse.next();
  if (request.cookies.has(SESSION_COOKIE)) return NextResponse.next();

  const url = request.nextUrl.clone();
  url.pathname = LOGIN_PATH;
  url.search = `?next=${encodeURIComponent(pathname + search)}`;
  return NextResponse.redirect(url);
}

export const config = {
  // Everything except Next's own assets and the favicon.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
