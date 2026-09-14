import { useCallback, useState } from "react";
import * as api from "../services/api";

/**
 * Drives the AbilityOS core loop (Part 5) end-to-end against the real API —
 * every stage here is one network call, not a hardcoded transition. Kept
 * out of DemoPage so the pipeline logic is testable/readable on its own.
 */

const STAGE = {
  IDLE: "idle",
  STARTED: "started",
  ENVIRONMENT_READY: "environment_ready",
  BARRIERS_DETECTED: "barriers_detected",
  RECOMMENDED: "recommended",
  AWAITING_CONFIRMATION: "awaiting_confirmation",
  APPLIED: "applied",
  COMPLETED: "completed",
};

const initialState = {
  stage: STAGE.IDLE,
  sessionId: null,
  environment: null,
  barriers: [],
  results: [],
  aiUsed: false,
  pendingConfirmation: [],
  appliedEffects: {},
  appliedAdaptations: [],
  baselineMode: false,
  error: null,
  busy: false,
};

export function useAbilityOSDemo() {
  const [state, setState] = useState(initialState);

  const reset = useCallback(() => setState(initialState), []);

  const runAnalysis = useCallback(async (userId, taskId = "purchase_ticket", baselineMode = false) => {
    setState((s) => ({ ...s, busy: true, error: null }));
    try {
      const { session_id } = await api.startInteraction({ userId, taskId, baselineMode });
      const environment = await api.analyzeEnvironment(session_id);
      const { barriers } = await api.detectBarriers(session_id);
      const { ai_used, results } = await api.recommendAdaptations(session_id);

      const pendingConfirmation = results.filter((r) => r.requires_confirmation && r.approved);

      setState((s) => ({
        ...s,
        stage: pendingConfirmation.length ? STAGE.AWAITING_CONFIRMATION : STAGE.RECOMMENDED,
        sessionId: session_id,
        environment,
        barriers,
        results,
        aiUsed: ai_used,
        pendingConfirmation,
        baselineMode,
        busy: false,
      }));
      return { sessionId: session_id, pendingConfirmation };
    } catch (err) {
      setState((s) => ({ ...s, busy: false, error: err.message }));
      throw err;
    }
  }, []);

  const applyAdaptations = useCallback(
    async (confirmedIds = []) => {
      if (!state.sessionId) return;
      setState((s) => ({ ...s, busy: true, error: null }));
      try {
        const payload = await api.applyAdaptations(state.sessionId, confirmedIds);
        setState((s) => ({
          ...s,
          stage: STAGE.APPLIED,
          appliedEffects: payload.ui_effects,
          appliedAdaptations: payload.applied_adaptations,
          pendingConfirmation: [],
          busy: false,
        }));
        return payload;
      } catch (err) {
        setState((s) => ({ ...s, busy: false, error: err.message }));
        throw err;
      }
    },
    [state.sessionId]
  );

  const submitFeedback = useCallback(
    async (feedback) => {
      if (!state.sessionId) return;
      setState((s) => ({ ...s, busy: true, error: null }));
      try {
        await api.submitFeedback(state.sessionId, feedback);
        setState((s) => ({ ...s, stage: STAGE.COMPLETED, busy: false }));
      } catch (err) {
        setState((s) => ({ ...s, busy: false, error: err.message }));
        throw err;
      }
    },
    [state.sessionId]
  );

  return { state, STAGE, runAnalysis, applyAdaptations, submitFeedback, reset };
}
