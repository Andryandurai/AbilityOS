/**
 * Thin fetch wrapper over the AbilityOS Django REST API (Part 11).
 *
 * One function per endpoint, kept flat and dependency-free so the rest of
 * the app never has to know about fetch/JSON plumbing — components call
 * `startInteraction(...)`, not `fetch(...)`.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:4343/api";

class ApiError extends Error {
  constructor(message, status, body) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new ApiError(
      `Could not reach the AbilityOS backend at ${BASE_URL}. Is the Django server running?`,
      0,
      null
    );
  }

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const message = data?.detail || `Request to ${path} failed (${response.status}).`;
    throw new ApiError(message, response.status, data);
  }
  return data;
}

const get = (path) => request(path, { method: "GET" });
const post = (path, body) => request(path, { method: "POST", body: JSON.stringify(body || {}) });
const patch = (path, body) => request(path, { method: "PATCH", body: JSON.stringify(body || {}) });
const del = (path) => request(path, { method: "DELETE" });

// --- Foundation ----------------------------------------------------------------
export const getHealth = () => get("/health/");

// --- Users / consent / ability profile --------------------------------------
export const listDemoUsers = () => get("/users/demo/");
export const getConsent = (userId) => get(`/users/${userId}/consent/`);
export const grantConsent = (userId, granted = true) =>
  post(`/users/${userId}/consent/`, { granted, scope: ["interaction_adaptation"] });
export const getAbilityProfile = (userId) => get(`/users/${userId}/ability-profile/`);
export const patchAbilityProfile = (userId, payload) =>
  patch(`/users/${userId}/ability-profile/`, payload);
export const clearAbilityProfile = (userId) => del(`/users/${userId}/ability-profile/`);

// --- Tasks -------------------------------------------------------------------
export const listTasks = () => get("/tasks/");

// Phase 3 Task Understanding Engine — deterministic task_id -> TaskDescriptor
// lookup, independent of any interaction session.
export const analyzeTask = (taskId) => post("/tasks/analyze/", { task_id: taskId });

// Phase 3 Environment Understanding Engine — deterministic environment_id ->
// EnvironmentDescriptor lookup, independent of any interaction session. Not
// to be confused with analyzeEnvironment() below, which is the session-bound
// call the orchestrated kiosk workflow uses.
export const analyzeEnvironmentFixture = (environmentId) =>
  post("/environment/analyze/", { environment_id: environmentId });

// --- Core AbilityOS workflow (Part 5) ----------------------------------------
export const startInteraction = ({ userId, taskId, environmentId, baselineMode }) =>
  post("/interactions/start/", {
    user_id: userId,
    task_id: taskId,
    environment_id: environmentId,
    baseline_mode: !!baselineMode,
  });

export const analyzeEnvironment = (sessionId, imageBase64) =>
  post("/environment/analyze/", { session_id: sessionId, image_base64: imageBase64 });

export const detectBarriers = (sessionId) => post("/barriers/detect/", { session_id: sessionId });

// Phase 4 Barrier Detection Engine — standalone, deterministic, no session
// required. Returns a BarrierDetectionResponse (see constants/taskEnvironment.js).
export const detectBarriersStandalone = (userId, taskId, environmentId) =>
  post("/barriers/detect/", { user_id: userId, task_id: taskId, environment_id: environmentId });

export const getAdaptationCandidates = (barrierType) =>
  get(`/adaptations/candidates/?barrier_type=${encodeURIComponent(barrierType)}`);

// Phase 5 Adaptation Engine + AI Decision Engine — standalone, no session
// required. Returns an AdaptationRecommendationResponse (see
// constants/taskEnvironment.js).
export const recommendAdaptationStandalone = (userId, taskId, environmentId) =>
  post("/adaptations/recommend/", { user_id: userId, task_id: taskId, environment_id: environmentId });

export const recommendAdaptations = (sessionId) =>
  post("/adaptations/recommend/", { session_id: sessionId });

export const applyAdaptations = (sessionId, confirmedIds = []) =>
  post(`/interactions/${sessionId}/apply/`, { confirmed_ids: confirmedIds });

export const submitFeedback = (sessionId, payload) =>
  post(`/interactions/${sessionId}/feedback/`, payload);

export const getSessionSummary = (sessionId) => get(`/interactions/${sessionId}/summary/`);

// --- Phase 7: step-level tracking + explicit lifecycle -----------------------
// `events` is a plain array of {event_type, step?, control_id?, metadata?} —
// callers accumulate a queue locally and flush it in one call rather than
// firing a request per tap (Phase 7 section 29).
export const recordEvents = (sessionId, events) =>
  post(`/interactions/${sessionId}/events/`, { events });

export const completeSession = (sessionId) => post(`/interactions/${sessionId}/complete/`, {});

export const abandonSession = (sessionId, reason) =>
  post(`/interactions/${sessionId}/abandon/`, { reason });

// --- Analytics -----------------------------------------------------------------
export const getBeforeAfter = () => get("/analytics/before-after/");
export const getDashboard = () => get("/analytics/dashboard/");
export const getAdaptationEffectiveness = () => get("/analytics/adaptations/");
export const getBarrierOutcomes = () => get("/analytics/barriers/");
export const getRecentSessions = (limit = 10) => get(`/analytics/sessions/?limit=${limit}`);

export { ApiError };
