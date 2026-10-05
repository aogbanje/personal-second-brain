"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { useSession } from "@/hooks/useSession";
import { api } from "@/lib/api-client";
import { LOGIN_PATH, isPublicPath } from "@/lib/auth";

const NAV = [
  { href: "/dashboard", label: "Library" },
  { href: "/chat", label: "Chat" },
  { href: "/graph", label: "Graph" },
];

/**
 * App chrome: nav plus who you are signed in as.
 *
 * Renders nothing on the auth screens. Hiding it here rather than moving
 * dashboard/chat/graph into a second route group keeps every existing URL and
 * file path untouched -- and this has to be a client component anyway to read
 * the session, so `usePathname` costs nothing extra.
 */
export function SiteHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const { user } = useSession();
  const [busy, setBusy] = useState(false);

  if (isPublicPath(pathname)) return null;

  async function signOut() {
    setBusy(true);
    try {
      await api.logout();
      // replace, not push: the back button should not return to a page that is
      // about to bounce off the middleware.
      router.replace(LOGIN_PATH);
    } finally {
      setBusy(false);
    }
  }

  return (
    <header className="border-b border-neutral-800 bg-neutral-900/50 backdrop-blur sticky top-0 z-20">
      <nav className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-3">
        <Link href="/dashboard" className="font-semibold tracking-tight">
          PSB
        </Link>
        <div className="flex gap-1 text-sm">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-md px-3 py-1.5 text-neutral-400 transition hover:bg-neutral-800 hover:text-neutral-100"
            >
              {item.label}
            </Link>
          ))}
        </div>
        {user && (
          <div className="ml-auto flex items-center gap-3 text-sm">
            <span className="text-neutral-500">{user.email}</span>
            <button
              onClick={() => void signOut()}
              disabled={busy}
              className="rounded-md px-3 py-1.5 text-neutral-400 transition hover:bg-neutral-800 hover:text-neutral-100 disabled:opacity-50"
            >
              {busy ? "…" : "Sign out"}
            </button>
          </div>
        )}
      </nav>
    </header>
  );
}
