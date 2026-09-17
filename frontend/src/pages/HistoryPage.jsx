import { useEffect, useState } from "react";
import * as api from "../services/api";
import { summarizeProfile } from "../constants/abilityProfile";
import "./ProfileFlow.css";
import "./HistoryPage.css";

const STATUS_LABELS = {
  started: "In progress",
  analyzed: "In progress",
  adapted: "In progress",
  in_progress: "In progress",
  completed: "Completed",
  abandoned: "Abandoned",
  failed: "Failed",
};

function formatDate(isoString) {
  if (!isoString) return "—";
  return new Date(isoString).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

/**
 * Phase 6 (Feedback + History + Analytics Integration) — a presentation
 * layer over data the existing engine already stores. Nothing here
 * recomputes a barrier, an adaptation, or a score: the list comes from
 * GET /api/users/{id}/sessions/ (new, but only a shaped read over the
 * existing InteractionSession/Barrier/AdaptationResult/Feedback rows —
 * see docs/HISTORY_ANALYTICS.md), and "View Details" reuses the same
 * GET /api/interactions/{id}/summary/ every developer/explanation panel
 * already used. A session's `ability_profile_snapshot` — not the user's
 * current AbilityProfile — is what's shown, exactly as it was recorded at
 * session start (section 22/37).
 */
export default function HistoryPage({ userId, onBack, onStartExperience }) {
  const [phase, setPhase] = useState("loading"); // loading | ready | error
  const [sessions, setSessions] = useState([]);
  const [error, setError] = useState(null);
  const [retryKey, setRetryKey] = useState(0);
  const [expandedId, setExpandedId] = useState(null);
  const [details, setDetails] = useState({}); // { [sessionId]: { phase, data?, error? } }

  useEffect(() => {
    if (!userId) return undefined;
    let cancelled = false;
    setPhase("loading");
    setError(null);
    api
      .getUserSessions(userId)
      .then((data) => {
        if (cancelled) return;
        setSessions(data.sessions);
        setPhase("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err);
        setPhase("error");
      });
    return () => {
      cancelled = true;
    };
  }, [userId, retryKey]);

  const toggleDetails = (sessionId) => {
    if (expandedId === sessionId) {
      setExpandedId(null);
      return;
    }
    setExpandedId(sessionId);
    if (details[sessionId]) return; // already fetched once — don't re-request

    setDetails((d) => ({ ...d, [sessionId]: { phase: "loading" } }));
    api
      .getSessionSummary(sessionId)
      .then((data) => {
        setDetails((d) => ({ ...d, [sessionId]: { phase: "ready", data } }));
      })
      .catch((err) => {
        setDetails((d) => ({ ...d, [sessionId]: { phase: "error", error: err.message } }));
      });
  };

  const sessionExpired = error?.status === 401 || error?.status === 403;

  return (
    <div className="profile-flow history">
      <div className="card profile-flow__intro">
        <h1>Interaction History</h1>
        <p>Your previous AbilityOS sessions.</p>
      </div>

      {phase === "loading" && <div className="card">Loading your interaction history…</div>}

      {phase === "error" && (
        <div className="card" role="alert">
          <p className="history__error">
            {sessionExpired ? "Your session has expired." : "Unable to load your interaction history."}
          </p>
          {!sessionExpired && <p className="history__error">{error?.message}</p>}
          <button type="button" className="btn btn--ghost" onClick={() => setRetryKey((n) => n + 1)}>
            Retry
          </button>
        </div>
      )}

      {phase === "ready" && sessions.length === 0 && (
        <div className="card">
          <p>No AbilityOS sessions yet.</p>
          <p className="profile-flow__subtitle">Start an experience to see your interactions here.</p>
          <button type="button" className="btn btn--primary" onClick={onStartExperience}>
            Start Experience
          </button>
        </div>
      )}

      {phase === "ready" && sessions.length > 0 && (
        <div className="stack">
          {sessions.map((session) => {
            const detail = details[session.session_id];
            const expanded = expandedId === session.session_id;
            return (
              <div key={session.session_id} className="card history__card">
                <div className="history__card-header">
                  <div>
                    <h2 className="history__task-name">{session.task_name}</h2>
                    <p className="history__date">{formatDate(session.created_at)}</p>
                  </div>
                  <span className={`pill ${session.status === "completed" ? "pill--low" : "pill--neutral"}`}>
                    {STATUS_LABELS[session.status] || session.status}
                  </span>
                </div>

                <dl className="history__facts">
                  <div>
                    <dt>Environment</dt>
                    <dd>{session.environment_name || "—"}</dd>
                  </div>
                  <div>
                    <dt>Barriers detected</dt>
                    <dd>{session.barriers_detected}</dd>
                  </div>
                  <div>
                    <dt>Adaptations applied</dt>
                    <dd>{session.adaptations_applied}</dd>
                  </div>
                  <div>
                    <dt>Feedback</dt>
                    <dd>{session.feedback_submitted ? "✓ Submitted" : "Not submitted"}</dd>
                  </div>
                </dl>

                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => toggleDetails(session.session_id)}
                  aria-expanded={expanded}
                >
                  {expanded ? "Hide Details" : "View Details"}
                </button>

                {expanded && (
                  <div className="history__detail">
                    {(!detail || detail.phase === "loading") && <p>Loading details…</p>}
                    {detail?.phase === "error" && (
                      <p className="history__error">Unable to load details. {detail.error}</p>
                    )}
                    {detail?.phase === "ready" && (
                      <SessionDetail data={detail.data} />
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {onBack && (
        <div className="row profile-flow__actions">
          <button type="button" className="btn btn--ghost" onClick={onBack}>
            Back to Dashboard
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * The read-only "what happened during this session" breakdown. Every value
 * here comes straight from the stored session summary (barriers,
 * adaptation results, feedback, and the session's own profile snapshot) —
 * nothing is recomputed against the user's current Ability Profile.
 */
function SessionDetail({ data }) {
  const snapshotEntries = summarizeProfile({ dimensions: data.ability_profile_snapshot });
  const appliedAdaptations = data.adaptation_results.filter((r) => r.applied);

  return (
    <div className="stack">
      <div>
        <p className="history__detail-label">Ability Profile used for this session</p>
        {snapshotEntries.length === 0 ? (
          <p>Typical profile — no specific adaptations were relevant.</p>
        ) : (
          <ul className="profile-summary__list">
            {snapshotEntries.map((entry) => (
              <li key={entry.text}>
                <span aria-hidden="true">{entry.emoji}</span> {entry.text}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <p className="history__detail-label">Barriers</p>
        {data.barriers.length === 0 ? (
          <p>No barriers detected.</p>
        ) : (
          <ul className="history__list">
            {data.barriers.map((b) => (
              <li key={b.id}>{b.type.replaceAll("_", " ")}</li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <p className="history__detail-label">Adaptations applied</p>
        {appliedAdaptations.length === 0 ? (
          <p>No adaptations were applied.</p>
        ) : (
          <ul className="history__list">
            {appliedAdaptations.map((r) => (
              <li key={r.id}>{r.display_name}</li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <p className="history__detail-label">Feedback</p>
        {data.feedback ? (
          <p>
            {data.feedback.ease_rating ? `Ease: ${data.feedback.ease_rating}/5` : "No ease rating given"}
            {data.feedback.adaptation_helpfulness &&
              ` · Adaptation helpfulness: ${data.feedback.adaptation_helpfulness.replaceAll("_", " ")}`}
            {data.feedback.optional_comment && ` · "${data.feedback.optional_comment}"`}
          </p>
        ) : (
          <p>Not submitted.</p>
        )}
      </div>
    </div>
  );
}
