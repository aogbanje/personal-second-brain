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
 */
export function useSession() {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);
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
    void refresh();
  }, [refresh]);

  return { user, loading, error, refresh };
}
