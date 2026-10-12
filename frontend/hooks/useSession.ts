"use client";

import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api-client";
import type { UserResponse } from "@/lib/types";

/**
 * The signed-in user, or null.
 *
 * A 401 here is the expected state for a signed-out visitor, not an error
 * worth showing -- the API client has already redirected to login by the time
 * it surfaces, so this resolves to `user: null` and lets the redirect happen.
 *
 * `enabled: false` skips the request entirely, for callers that already know
 * there is no session to fetch (the auth screens). A hook cannot be called
 * conditionally, so the condition has to live in here.
 */
export function useSession({ enabled = true }: { enabled?: boolean } = {}) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setUser(await api.me());
      setError(null);
    } catch (err) {
      setUser(null);
      setError(err instanceof Error ? err.message : "could not load session");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;
    void refresh();
  }, [enabled, refresh]);

  return { user, loading, error, refresh };
}
