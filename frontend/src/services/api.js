/**
 * Thin fetch wrapper over the AbilityOS Django REST API (Part 11).
 *
 * One function per endpoint, kept flat and dependency-free so the rest of
 * the app never has to know about fetch/JSON plumbing — components call
 * `startInteraction(...)`, not `fetch(...)`.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

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

// --- Users / consent / ability profile --------------------------------------
export const listDemoUsers = () => get("/users/demo/");
export const getConsent = (userId) => get(`/users/${userId}/consent/`);
export const grantConsent = (userId, granted = true) =>
  post(`/users/${userId}/consent/`, { granted, scope: ["interaction_adaptation"] });
export const getAbilityProfile = (userId) => get(`/users/${userId}/ability-profile/`);
export const patchAbilityProfile = (userId, payload) =>
  patch(`/users/${userId}/ability-profile/`, payload);

// --- Tasks -------------------------------------------------------------------
export const listTasks = () => get("/tasks/");

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

export const getAdaptationCandidates = (barrierType) =>
  get(`/adaptations/candidates/?barrier_type=${encodeURIComponent(barrierType)}`);

export const recommendAdaptations = (sessionId) =>
  post("/adaptations/recommend/", { session_id: sessionId });

export const applyAdaptations = (sessionId, confirmedIds = []) =>
  post(`/interactions/${sessionId}/apply/`, { confirmed_ids: confirmedIds });

export const submitFeedback = (sessionId, payload) =>
  post(`/interactions/${sessionId}/feedback/`, payload);

export const getSessionSummary = (sessionId) => get(`/interactions/${sessionId}/summary/`);

// --- Analytics -----------------------------------------------------------------
export const getBeforeAfter = () => get("/analytics/before-after/");
export const getDashboard = () => get("/analytics/dashboard/");

export { ApiError };
