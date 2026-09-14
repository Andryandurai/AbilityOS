import { useCallback, useEffect, useState } from "react";
import ConfirmDialog from "../components/ConfirmDialog";
import ConsentGate from "../components/ConsentGate";
import DeveloperPanel from "../components/DeveloperPanel";
import KioskView from "../components/KioskView";
import MetricsPanel from "../components/MetricsPanel";
import ProfileSwitcher from "../components/ProfileSwitcher";
import { useAbilityOSDemo } from "../hooks/useAbilityOSDemo";
import * as api from "../services/api";

const TASK_ID = "purchase_ticket";

export default function DemoPage({ resetSignal }) {
  const [users, setUsers] = useState([]);
  const [profiles, setProfiles] = useState({});
  const [activeUserId, setActiveUserId] = useState(null);
  const [consentGranted, setConsentGranted] = useState({});
  const [task, setTask] = useState(null);
  const [baselineToggle, setBaselineToggle] = useState(false);
  const [metrics, setMetrics] = useState(null);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [loadError, setLoadError] = useState(null);

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
    try {
      const demoUsers = await api.listDemoUsers();
      setUsers(demoUsers);
      if (demoUsers.length) setActiveUserId((prev) => prev ?? demoUsers[0].id);

      const [profileEntries, consentEntries] = await Promise.all([
        Promise.all(demoUsers.map((u) => api.getAbilityProfile(u.id).then((p) => [u.id, p]))),
        Promise.all(demoUsers.map((u) => api.getConsent(u.id).then((c) => [u.id, c.granted]))),
      ]);
      setProfiles(Object.fromEntries(profileEntries));
      setConsentGranted(Object.fromEntries(consentEntries));

      const tasks = await api.listTasks();
      setTask(tasks.find((t) => t.task_id === TASK_ID) || tasks[0] || null);

      refreshMetrics();
    } catch (err) {
      setLoadError(err.message);
    }
  }, [refreshMetrics]);

  useEffect(() => {
    loadAll();
  }, [loadAll, resetSignal]);

  useEffect(() => {
    demo.reset();
  }, [activeUserId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (resetSignal) demo.reset();
  }, [resetSignal]); // eslint-disable-line react-hooks/exhaustive-deps

  const activeProfile = activeUserId ? profiles[activeUserId] : null;
  const activeConsent = activeUserId ? consentGranted[activeUserId] : false;

  const handleAgreeConsent = async () => {
    await api.grantConsent(activeUserId, true);
    setConsentGranted((c) => ({ ...c, [activeUserId]: true }));
  };

  const handleStart = () => demo.runAnalysis(activeUserId, TASK_ID, baselineToggle);

  const handleApply = () => demo.applyAdaptations([]);

  const handleConfirm = (ids) => demo.applyAdaptations(ids);

  const handleKioskComplete = async (outcome) => {
    await demo.submitFeedback(outcome);
    refreshMetrics();
  };

  if (loadError) {
    return (
      <div className="card" role="alert">
        <h2>Could not load AbilityOS</h2>
        <p>{loadError}</p>
        <p>Is the Django backend running at the configured API URL? See README.md.</p>
      </div>
    );
  }

  if (!users.length) {
    return <div className="card">Loading AbilityOS demo data…</div>;
  }

  const interactive = state.stage === STAGE.APPLIED;
  const showConfirm = state.stage === STAGE.AWAITING_CONFIRMATION;
  const showApplyButton = state.stage === STAGE.RECOMMENDED;

  return (
    <div className="demo-page">
      <ProfileSwitcher
        users={users}
        profiles={profiles}
        activeUserId={activeUserId}
        onSelect={setActiveUserId}
        disabled={state.busy}
      />

      {!activeConsent ? (
        <ConsentGate onAgree={handleAgreeConsent} />
      ) : (
        <div className="demo-page__grid">
          <div className="stack">
            <div className="card">
              <h2>2. Run the task</h2>
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
              <h2>3. Kiosk</h2>
              <KioskView
                key={state.sessionId || "preview"}
                environment={state.environment}
                barriers={state.barriers}
                appliedEffects={state.appliedEffects}
                profile={activeProfile}
                interactive={interactive}
                baselineMode={state.baselineMode}
                onComplete={handleKioskComplete}
              />
            </div>
          </div>

          <DeveloperPanel
            profile={activeProfile}
            task={task}
            environment={state.environment}
            barriers={state.barriers}
            results={state.results}
            aiUsed={state.aiUsed}
            aiError={null}
          />
        </div>
      )}

      <MetricsPanel data={metrics} loading={metricsLoading} />
    </div>
  );
}
