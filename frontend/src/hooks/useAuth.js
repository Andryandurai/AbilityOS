import { useCallback, useEffect, useState } from "react";
import * as api from "../services/api";

/**
 * Phase 1 (Real User Authentication) — a single, centralized authentication
 * abstraction. No component talks to the token or to /api/auth/* directly;
 * everything goes through this hook, mirroring the existing
 * useProfileFlow.js pattern (one hook owns one slice of flow state) rather
 * than introducing a new state-management library.
 *
 * Token storage: localStorage, deliberately. This is a hackathon SPA with
 * no existing cookie/session infrastructure to build on, and Phase 0's
 * audit found no reason to introduce one just for this. The known
 * tradeoff — a token in localStorage is readable by any script that
 * achieves XSS on this origin — is accepted for this project's scope, not
 * overlooked: see docs/AUTHENTICATION.md. Mitigations actually in place:
 * tokens are never logged (console or otherwise), never put in a URL or
 * query string, and are cleared from storage immediately on logout.
 */

const ACCESS_TOKEN_KEY = "abilityos_access_token";
const REFRESH_TOKEN_KEY = "abilityos_refresh_token";

function readStoredTokens() {
  try {
    return {
      access: localStorage.getItem(ACCESS_TOKEN_KEY),
      refresh: localStorage.getItem(REFRESH_TOKEN_KEY),
    };
  } catch {
    // localStorage unavailable (private browsing, disabled storage, etc.)
    // — auth simply doesn't persist across reloads; the rest of the app
    // still works anonymously.
    return { access: null, refresh: null };
  }
}

function storeTokens(access, refresh) {
  try {
    if (access) localStorage.setItem(ACCESS_TOKEN_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  } catch {
    /* non-fatal — see readStoredTokens() */
  }
}

function clearStoredTokens() {
  try {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  } catch {
    /* non-fatal */
  }
}

export function useAuth() {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const refreshUser = useCallback(async () => {
    try {
      const me = await api.getCurrentUser();
      setUser(me);
      return me;
    } catch {
      // Access token missing/expired/invalid — not logged in, not an
      // error the user needs to see.
      api.setAccessToken(null);
      clearStoredTokens();
      setUser(null);
      return null;
    }
  }, []);

  // On mount: if a token survived from a previous session (page reload —
  // there is no routing in Phase 1, so this is the only "persistence
  // across navigation" mechanism there is), attach it and confirm via
  // /me that it's still valid, rather than trusting it blindly.
  useEffect(() => {
    const { access } = readStoredTokens();
    if (access) {
      api.setAccessToken(access);
      refreshUser().finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, [refreshUser]);

  const login = useCallback(async (username, password) => {
    setError(null);
    try {
      const data = await api.login(username, password);
      api.setAccessToken(data.access);
      storeTokens(data.access, data.refresh);
      setUser(data.user);
      return data.user;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, []);

  const register = useCallback(async (payload) => {
    setError(null);
    try {
      return await api.register(payload);
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, []);

  // Phase 1 section 19: the app supports two entry paths -- a real
  // account, and the existing anonymous demo (9 seeded personas) --
  // side by side. Entering the anonymous demo must behave exactly as it
  // did before this phase, for every visitor, including one who happens
  // to also be logged in: without this, api.js would attach the logged-in
  // user's token to every demo request, and assert_owner() (see Phase 1
  // section 11) would then correctly-but-unhelpfully reject
  // getAbilityProfile(<some other demo persona's id>) with 403. Pausing
  // only toggles the outgoing header (api.js's module-level accessToken);
  // it never touches `user` state, localStorage, or calls the backend, so
  // resuming is instant and the real session is never at risk of being
  // dropped just because someone clicked "explore the demo".
  const pauseAuthHeader = useCallback(() => {
    api.setAccessToken(null);
  }, []);

  const resumeAuthHeader = useCallback(() => {
    const { access } = readStoredTokens();
    if (access) api.setAccessToken(access);
  }, []);

  const logout = useCallback(async () => {
    const { refresh } = readStoredTokens();
    try {
      if (refresh) await api.logout(refresh);
    } catch {
      // The frontend still discards its own tokens below even if the
      // blacklist call itself fails (e.g. the access token already
      // expired) — "logged out" on this device is not conditional on
      // that backend call succeeding. See users/views.py::LogoutView for
      // what blacklisting does and does not invalidate.
    }
    api.setAccessToken(null);
    clearStoredTokens();
    setUser(null);
  }, []);

  return {
    user,
    isAuthenticated: Boolean(user),
    isLoading,
    error,
    login,
    register,
    logout,
    refreshUser,
    pauseAuthHeader,
    resumeAuthHeader,
  };
}
