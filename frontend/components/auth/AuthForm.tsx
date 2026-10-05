"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { api } from "@/lib/api-client";

type Mode = "login" | "signup";

const COPY: Record<
  Mode,
  { heading: string; action: string; altPrompt: string; altLabel: string; altHref: string }
> = {
  login: {
    heading: "Sign in",
    action: "Sign in",
    altPrompt: "No account yet?",
    altLabel: "Create one",
    altHref: "/signup",
  },
  signup: {
    heading: "Create an account",
    action: "Create account",
    altPrompt: "Already have an account?",
    altLabel: "Sign in",
    altHref: "/login",
  },
};

// Mirrors the backend's SignupRequest min_length, so the obvious mistake is
// caught without a round trip. The server still enforces it.
const MIN_PASSWORD = 12;

export function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const copy = COPY[mode];

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (mode === "signup" && password.length < MIN_PASSWORD) {
      setError(`Password must be at least ${MIN_PASSWORD} characters.`);
      return;
    }

    setBusy(true);
    setError(null);
    try {
      if (mode === "signup") {
        await api.signup(email.trim(), password);
      } else {
        await api.login(email.trim(), password);
      }
      // Honour where the middleware bounced them from, but only for in-app
      // paths -- an absolute URL here would be an open redirect.
      const next = searchParams.get("next");
      router.replace(next?.startsWith("/") ? next : "/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : `${copy.action} failed`);
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm py-12">
      <h1 className="mb-1 text-lg font-semibold tracking-tight">
        {copy.heading}
      </h1>
      <p className="mb-6 text-sm text-neutral-500">
        Your documents, chunks and graph are private to your account.
      </p>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
        className="space-y-2"
      >
        <input
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="you@example.com"
          autoComplete="email"
          required
          className="w-full rounded-md border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm outline-none focus:border-neutral-500"
        />
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Password"
          autoComplete={mode === "signup" ? "new-password" : "current-password"}
          required
          className="w-full rounded-md border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm outline-none focus:border-neutral-500"
        />
        <button
          disabled={busy}
          className="w-full rounded-md bg-neutral-100 px-4 py-2 text-sm font-medium text-neutral-900 disabled:opacity-50"
        >
          {busy ? "…" : copy.action}
        </button>
      </form>

      {mode === "signup" && (
        <p className="mt-2 text-xs text-neutral-600">
          At least {MIN_PASSWORD} characters. Length is the only rule.
        </p>
      )}

      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}

      <p className="mt-6 text-sm text-neutral-500">
        {copy.altPrompt}{" "}
        <Link href={copy.altHref} className="text-neutral-300 hover:underline">
          {copy.altLabel}
        </Link>
      </p>
    </div>
  );
}
