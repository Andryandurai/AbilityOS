import { useCallback, useState } from "react";
import * as api from "../services/api";

/**
 * Drives the Select User -> Consent -> Ability Profile -> Summary journey
 * (Phase 2 section 19) against the real API — mirrors the established
 * useAbilityOSDemo pattern (a custom hook owning one multi-step flow's
 * state) rather than introducing a new state-management library.
 *
 * The backend is always the source of truth: nothing here is ever set to
 * "saved"/"granted" without the corresponding API call actually
 * succeeding (Phase 2 section 45).
 */

export function useProfileFlow() {
  const [userId, setUserId] = useState(null);
  const [profile, setProfile] = useState(null);
  const [consent, setConsentState] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const selectUser = useCallback(async (id) => {
    setLoading(true);
    setError(null);
    try {
      const [p, c] = await Promise.all([api.getAbilityProfile(id), api.getConsent(id)]);
      setUserId(id);
      setProfile(p);
      setConsentState(c);
      return { profile: p, consent: c };
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const agreeToConsent = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    setError(null);
    try {
      const c = await api.grantConsent(userId, true);
      setConsentState(c);
      return c;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [userId]);

  const saveProfile = useCallback(
    async (dimensions, preferredModality) => {
      if (!userId) return;
      setLoading(true);
      setError(null);
      try {
        const p = await api.patchAbilityProfile(userId, {
          dimensions,
          preferred_modality: preferredModality,
        });
        setProfile(p);
        return p;
      } catch (err) {
        setError(err.message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [userId]
  );

  const clearProfile = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    setError(null);
    try {
      const p = await api.clearAbilityProfile(userId);
      setProfile(p);
      return p;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [userId]);

  const reset = useCallback(() => {
    setUserId(null);
    setProfile(null);
    setConsentState(null);
    setError(null);
  }, []);

  return {
    userId,
    profile,
    consent,
    loading,
    error,
    selectUser,
    agreeToConsent,
    saveProfile,
    clearProfile,
    reset,
  };
}
