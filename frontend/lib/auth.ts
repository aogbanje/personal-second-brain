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
