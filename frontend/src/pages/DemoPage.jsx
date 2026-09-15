import { useCallback, useEffect, useState } from "react";
import ConfirmDialog from "../components/ConfirmDialog";
import ConsentGate from "../components/ConsentGate";
import DeveloperPanel from "../components/DeveloperPanel";
import FeedbackForm from "../components/FeedbackForm";
import KioskView from "../components/KioskView";
import MetricsPanel from "../components/MetricsPanel";
import OutcomeSummary from "../components/OutcomeSummary";
import { useAbilityOSDemo } from "../hooks/useAbilityOSDemo";
import * as api from "../services/api";

const TASK_ID = "purchase_ticket";

/**
 * The kiosk demo itself — Phase 5/6/7 territory (Adaptation Engine, AI
 * Decision Engine, adaptive UI, feedback/analytics), all already built and
 * verified in an earlier pass on this repo. Phase 2 only changed how this
 * page is *reached*: it now receives an already-selected, already-
 * consented `userId` from the new Select User -> Consent -> Profile ->
 * Summary journey (App.jsx) instead of managing profile selection and
 * consent itself.
 */
export default function DemoPage({ userId, resetSignal }) {
  const [profile, setProfile] = useState(null);
  const [consentGranted, setConsentGranted] = useState(null);
  const [task, setTask] = useState(null);
  const [baselineToggle, setBaselineToggle] = useState(false);
  const [metrics, setMetrics] = useState(null);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [loadError, setLoadError] = useState(null);
  // Phase 6 section 8: a demonstration-only comparison toggle. It never
  // invents or bypasses anything — "original" just means "render with an
  // empty effects object", the exact same real KioskView the applied
  // adaptation already came from.
  const [viewMode, setViewMode] = useState("adaptive");

  const demo = useAbilityOSDemo();
  const { state, STAGE } = demo;

  const refreshMetrics = useCallback(() => {
    setMetricsLoading(true);
    api
      .getBeforeAfter()
      .then(setMetrics)
      .catch(() => {})
      .finally(() => setMetricsLoading(false));
  }, []);

  const loadAll = useCallback(async () => {
    if (!userId) return;
    try {
      const [p, c, tasks] = await Promise.all([
        api.getAbilityProfile(userId),
        api.getConsent(userId),
        api.listTasks(),
      ]);
      setProfile(p);
      setConsentGranted(c.granted);
      setTask(tasks.find((t) => t.task_id === TASK_ID) || tasks[0] || null);
      refreshMetrics();
    } catch (err) {
      setLoadError(err.message);
    }
  }, [userId, refreshMetrics]);

  useEffect(() => {
    loadAll();
  }, [loadAll, resetSignal]);

  useEffect(() => {
    demo.reset();
    setViewMode("adaptive");
  }, [userId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (resetSignal) {
      demo.reset();
      setViewMode("adaptive");
    }
  }, [resetSignal]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleAgreeConsent = async () => {
    await api.grantConsent(userId, true);
    setConsentGranted(true);
  };

  const handleStart = () => demo.runAnalysis(userId, TASK_ID, baselineToggle);

  const handleApply = () => demo.applyAdaptations([]);

  const handleConfirm = (ids) => demo.applyAdaptations(ids);

  // Phase 7 section 7: the task itself finishes (completed or abandoned)
  // before feedback is ever asked for — these mark the session's terminal
  // status server-side; the short feedback form (below) is a separate,
  // later step, not folded into this call.
  const handleKioskComplete = (outcome) => demo.completeTask(outcome);
  const handleKioskAbandon = (outcome) => demo.abandonTask(outcome);

  const handleFeedbackSubmit = async (subjective) => {
    await demo.submitFeedback(subjective);
    refreshMetrics();
  };

  if (!userId) {
    return <div className="card">No profile selected yet.</div>;
  }

  if (loadError) {
    return (
      <div className="card" role="alert">
        <h2>Could not load AbilityOS</h2>
        <p>{loadError}</p>
        <p>Is the Django backend running at the configured API URL? See README.md.</p>
      </div>
    );
  }

  if (!profile) {
    return <div className="card">Loading AbilityOS demo data…</div>;
  }

  // Defensive fallback only — the Select User -> Consent journey (App.jsx)
  // should never let a user reach this page without consent already
  // granted. This exists purely as a backend-truth safety net, not the
  // primary consent UI (that's ConsentPage).
  if (!consentGranted) {
    return <ConsentGate onAgree={handleAgreeConsent} />;
  }

  const interactive = state.stage === STAGE.APPLIED;
  const showConfirm = state.stage === STAGE.AWAITING_CONFIRMATION;
  const showApplyButton = state.stage === STAGE.RECOMMENDED;

  return (
    <div className="demo-page">
      <div className="demo-page__grid">
        <div className="stack">
          <div className="card">
            <h1>Run the task — {profile.label}</h1>
            <label className="row" style={{ marginBottom: "var(--space-3)" }}>
              <input
                type="checkbox"
                checked={baselineToggle}
                onChange={(e) => setBaselineToggle(e.target.checked)}
                disabled={state.stage !== STAGE.IDLE}
              />
              Run in baseline mode (detect barriers, but don't adapt — for the "without AbilityOS"
              comparison)
            </label>
            <div className="row">
              <button className="btn btn--primary" onClick={handleStart} disabled={state.busy || state.stage !== STAGE.IDLE}>
                {state.busy && state.stage === STAGE.IDLE ? "Analyzing…" : "Start Ticket Purchase"}
              </button>
              {showApplyButton && (
                <button className="btn btn--accent" onClick={handleApply} disabled={state.busy}>
                  Apply Approved Adaptation(s)
                </button>
              )}
            </div>
            {state.error && <p className="dev-panel__ai-note">{state.error}</p>}
          </div>

          {showConfirm && (
            <ConfirmDialog
              pending={state.pendingConfirmation}
              onConfirm={handleConfirm}
              onSkip={() => handleConfirm([])}
            />
          )}

          <div className="card">
            <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
              <h2>Kiosk</h2>
              {interactive && (
                <div className="row" role="group" aria-label="Compare original and adaptive experience">
                  <button
                    type="button"
                    className={`btn ${viewMode === "original" ? "btn--primary" : "btn--ghost"}`}
                    aria-pressed={viewMode === "original"}
                    onClick={() => setViewMode("original")}
                  >
                    View Original
                  </button>
                  <button
                    type="button"
                    className={`btn ${viewMode === "adaptive" ? "btn--primary" : "btn--ghost"}`}
                    aria-pressed={viewMode === "adaptive"}
                    onClick={() => setViewMode("adaptive")}
                  >
                    View Adaptive
                  </button>
                </div>
              )}
            </div>
            <KioskView
              key={state.sessionId || "preview"}
              environment={state.environment}
              barriers={state.barriers}
              appliedEffects={viewMode === "original" ? {} : state.appliedEffects}
              profile={profile}
              interactive={interactive}
              baselineMode={state.baselineMode}
              onComplete={handleKioskComplete}
              onAbandon={handleKioskAbandon}
              onEvent={demo.queueEvent}
            />
          </div>

          {state.stage === STAGE.AWAITING_FEEDBACK && (
            <FeedbackForm
              adaptationApplied={!state.baselineMode && state.appliedAdaptations.length > 0}
              defaultAssistance={state.pendingOutcome?.assistance_requested}
              onSubmit={handleFeedbackSubmit}
              busy={state.busy}
            />
          )}

          {state.stage === STAGE.COMPLETED && (
            <OutcomeSummary
              taskName={task?.name}
              completed={Boolean(state.pendingOutcome?.completed)}
              adaptive={!state.baselineMode && state.appliedAdaptations.length > 0}
              feedback={state.feedback}
            />
          )}
        </div>

        <DeveloperPanel
          profile={profile}
          task={task}
          environment={state.environment}
          barriers={state.barriers}
          results={state.results}
          appliedAdaptations={state.appliedAdaptations}
          aiUsed={state.aiUsed}
          aiError={null}
          sessionStatus={state.sessionStatus}
          assistanceCount={state.assistanceCount}
          completionTimeMs={state.completionTimeMs}
          outcomeScore={state.outcomeScore}
          learningSignal={state.learningSignal}
          feedback={state.feedback}
        />
      </div>

      <MetricsPanel data={metrics} loading={metricsLoading} />
    </div>
  );
}
