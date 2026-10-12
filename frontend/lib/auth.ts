/**
 * Session plumbing shared by the middleware and the API client.
 *
 * The session itself is an httpOnly cookie set by the backend, so nothing here
 * can read or forge it -- this is only the name and the redirect, defined once
 * so the middleware and the 401 handler cannot drift apart.
 */

export const SESSION_COOKIE = "psb_session";

export const LOGIN_PATH = "/login";
export const SIGNUP_PATH = "/signup";

/** Routes reachable without a session. */
export const PUBLIC_PATHS = [LOGIN_PATH, SIGNUP_PATH];

export function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`),
  );
}

/**
 * Validate a `?next=` value before navigating to it.
 *
 * `next` arrives in the URL, so it is attacker-controlled: a login link can be
 * crafted with any value and the victim lands wherever it points *after*
 * authenticating. A bare `startsWith("/")` is not enough -- `//evil.com` is a
 * protocol-relative URL, and browsers normalise the backslash in `/\evil.com`
 * to the same thing. Both leave the site.
 *
 * Returns the path only when it is unambiguously in-app, else the fallback.
 */
export function safeNextPath(
  next: string | null,
  fallback = "/dashboard",
): string {
  if (!next) return fallback;
  if (!next.startsWith("/")) return fallback;
  // Rejects "//host" and "/\host" -- the two spellings of "leave this origin".
  if (next.startsWith("//") || next.startsWith("/\\")) return fallback;
  return next;
}

/**
 * Bounce to login, preserving where the user was headed.
 *
 * Uses a hard assignment rather than the router because this is called from
 * the fetch wrapper, which has no hook context.
 */
export function redirectToLogin(): void {
  if (typeof window === "undefined") return;
  if (isPublicPath(window.location.pathname)) return;

  const next = window.location.pathname + window.location.search;
  window.location.assign(`${LOGIN_PATH}?next=${encodeURIComponent(next)}`);
}
