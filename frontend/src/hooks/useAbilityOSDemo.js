import { useCallback, useState } from "react";
import * as api from "../services/api";

/**
 * Drives the AbilityOS core loop (Part 5) end-to-end against the real API —
 * every stage here is one network call, not a hardcoded transition. Kept
 * out of DemoPage so the pipeline logic is testable/readable on its own.
 *
 * Phase 7 extends the tail of this loop: APPLIED -> (kiosk interaction,
 * events queued locally) -> AWAITING_FEEDBACK (session marked complete/
 * abandoned server-side, objective outcome captured) -> COMPLETED (the
 * short subjective feedback form submitted, learning signal + outcome
 * score available from the session summary).
 */

const STAGE = {
  IDLE: "idle",
  STARTED: "started",
  ENVIRONMENT_READY: "environment_ready",
  BARRIERS_DETECTED: "barriers_detected",
  RECOMMENDED: "recommended",
  AWAITING_CONFIRMATION: "awaiting_confirmation",
  APPLIED: "applied",
  AWAITING_FEEDBACK: "awaiting_feedback",
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
  pendingEvents: [],
  pendingOutcome: null,
  sessionStatus: null,
  feedback: null,
  learningSignal: null,
  outcomeScore: null,
  assistanceCount: null,
  completionTimeMs: null,
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

  // Phase 7 section 8/29: accumulate step-relevant events locally — no
  // network call per tap. Safe to call before a session exists (the
  // pre-interaction UI has nothing to flush yet).
  const queueEvent = useCallback((eventType, { step, controlId, metadata } = {}) => {
    setState((s) => ({
      ...s,
      pendingEvents: [...s.pendingEvents, { event_type: eventType, step, control_id: controlId, metadata }],
    }));
  }, []);

  const flushEvents = useCallback(
    async (extraEvents = []) => {
      const events = [...state.pendingEvents, ...extraEvents];
      if (!state.sessionId || events.length === 0) return;
      try {
        await api.recordEvents(state.sessionId, events);
      } catch {
        // Best-effort: losing granular event telemetry must never block the
        // person from completing or abandoning their task.
      }
      setState((s) => ({ ...s, pendingEvents: [] }));
    },
    [state.sessionId, state.pendingEvents]
  );

  const completeTask = useCallback(
    async (outcome) => {
      if (!state.sessionId) return;
      setState((s) => ({ ...s, busy: true, error: null }));
      // completeSession() itself records the task_completed audit event
      // server-side — this only flushes whatever step-level events are
      // still queued locally.
      await flushEvents();
      try {
        const payload = await api.completeSession(state.sessionId);
        setState((s) => ({
          ...s,
          stage: STAGE.AWAITING_FEEDBACK,
          sessionStatus: payload.status,
          pendingOutcome: outcome,
          busy: false,
        }));
      } catch (err) {
        setState((s) => ({ ...s, busy: false, error: err.message }));
        throw err;
      }
    },
    [state.sessionId, flushEvents]
  );

  const abandonTask = useCallback(
    async (outcome, reason = "") => {
      if (!state.sessionId) return;
      setState((s) => ({ ...s, busy: true, error: null }));
      // abandonSession() itself records the task_abandoned audit event
      // (with `reason`) server-side — this only flushes queued step events.
      await flushEvents();
      try {
        const payload = await api.abandonSession(state.sessionId, reason);
        setState((s) => ({
          ...s,
          stage: STAGE.AWAITING_FEEDBACK,
          sessionStatus: payload.status,
          pendingOutcome: outcome,
          busy: false,
        }));
      } catch (err) {
        setState((s) => ({ ...s, busy: false, error: err.message }));
        throw err;
      }
    },
    [state.sessionId, flushEvents]
  );

  // Phase 7 section 12/13: the short subjective feedback screen. Merges
  // with the objective outcome already captured by completeTask/
  // abandonTask into the one existing /feedback/ call.
  const submitFeedback = useCallback(
    async (subjective) => {
      if (!state.sessionId) return;
      setState((s) => ({ ...s, busy: true, error: null }));
      try {
        const payload = { ...(state.pendingOutcome || {}), ...subjective };
        const { feedback } = await api.submitFeedback(state.sessionId, payload);
        const summary = await api.getSessionSummary(state.sessionId);
        setState((s) => ({
          ...s,
          stage: STAGE.COMPLETED,
          feedback,
          learningSignal: summary.learning_signal,
          outcomeScore: summary.outcome_score,
          assistanceCount: summary.assistance_count,
          completionTimeMs: summary.completion_time_ms,
          busy: false,
        }));
      } catch (err) {
        setState((s) => ({ ...s, busy: false, error: err.message }));
        throw err;
      }
    },
    [state.sessionId, state.pendingOutcome]
  );

  return {
    state,
    STAGE,
    runAnalysis,
    applyAdaptations,
    queueEvent,
    completeTask,
    abandonTask,
    submitFeedback,
    reset,
  };
}
