import { useState } from "react";
import AdaptationDecisionPanel from "../components/AdaptationDecisionPanel";
import * as api from "../services/api";
import { ABILITY_QUESTIONS, summarizeProfile } from "../constants/abilityProfile";
import "./ProfileFlow.css";
import "./WhatIfPage.css";

const TASK_ID = "purchase_ticket";

/**
 * Phase 7 (Advanced Adaptive Intelligence, What-If Simulation & Decision
 * Support) — a controlled, side-effect-free "what if this dimension were
 * different" exploration.
 *
 * Reuses the existing engine and UI, not new ones: `POST /api/what-if/simulate/`
 * runs the exact same `AdaptationRecommender.recommend()` pipeline the
 * standalone Task & Environment demo already uses (Phase 3/4/5), and both
 * the "Current State" and "Simulated State" panels below are the existing
 * `AdaptationDecisionPanel` component (Phase 5) — unmodified, just fed a
 * simulation result instead of a real one. `onOpenKiosk` is intentionally
 * never passed to it here: nothing about a simulation can be "opened" in
 * the adaptive kiosk (section 20/21 — the real kiosk experience is
 * Task & Environment's job, not this page's).
 *
 * `profile` is the same `flow.profile` App.jsx already holds — not
 * re-fetched — so "Current Profile" always reflects the real, current
 * AbilityProfile, the same source of truth Dashboard/History already use.
 */
export default function WhatIfPage({ profile, onBack }) {
  const [dimensionKey, setDimensionKey] = useState(ABILITY_QUESTIONS[0].key);
  const [simulatedValue, setSimulatedValue] = useState("");
  const [phase, setPhase] = useState("idle"); // idle | loading | ready | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const question = ABILITY_QUESTIONS.find((q) => q.key === dimensionKey);
  const currentLevel = profile?.dimensions?.[dimensionKey]?.level || question.options[0].value;
  const currentLabel = question.options.find((o) => o.value === currentLevel)?.label || currentLevel;

  const resetResult = () => {
    setResult(null);
    setPhase("idle");
    setError(null);
  };

  const handleDimensionChange = (key) => {
    setDimensionKey(key);
    setSimulatedValue("");
    resetResult();
  };

  const handleValueChange = (value) => {
    setSimulatedValue(value);
    resetResult();
  };

  const handleRunSimulation = async () => {
    if (!simulatedValue) return;
    setPhase("loading");
    setError(null);
    try {
      const data = await api.runWhatIfSimulation({
        taskId: TASK_ID,
        overrides: { [dimensionKey]: simulatedValue },
      });
      setResult(data);
      setPhase("ready");
    } catch (err) {
      setError(err);
      setPhase("error");
    }
  };

  const summaryEntries = summarizeProfile(profile);

  return (
    <div className="profile-flow what-if">
      <div className="card profile-flow__intro">
        <h1>What-If Analysis</h1>
        <p>Explore how a different ability level would change AbilityOS's barrier and adaptation decisions.</p>
      </div>

      <div className="card">
        <h2>Current Profile</h2>
        {summaryEntries.length === 0 ? (
          <p>Typical profile — no specific adaptations currently apply.</p>
        ) : (
          <ul className="profile-summary__list">
            {summaryEntries.map((entry) => (
              <li key={entry.text}>
                <span aria-hidden="true">{entry.emoji}</span> {entry.text}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card">
        <h2>Simulate a change</h2>
        <div className="what-if__controls">
          <label className="what-if__field">
            <span>Select a dimension</span>
            <select value={dimensionKey} onChange={(e) => handleDimensionChange(e.target.value)}>
              {ABILITY_QUESTIONS.map((q) => (
                <option key={q.key} value={q.key}>
                  {q.heading}
                </option>
              ))}
            </select>
          </label>

          <div className="what-if__field">
            <span>Current value</span>
            <p className="what-if__current-value">{currentLabel}</p>
          </div>

          <label className="what-if__field">
            <span>Simulated value</span>
            <select value={simulatedValue} onChange={(e) => handleValueChange(e.target.value)}>
              <option value="">Choose a value…</option>
              {question.options.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <button
          type="button"
          className="btn btn--primary what-if__run-btn"
          onClick={handleRunSimulation}
          disabled={!simulatedValue || phase === "loading"}
        >
          {phase === "loading" ? "Running simulation…" : "Run Simulation"}
        </button>

        {phase === "error" && (
          <div role="alert">
            <p className="what-if__error">Unable to run the simulation.</p>
            <p className="what-if__error">{error?.message}</p>
          </div>
        )}
      </div>

      {phase === "ready" && result && (
        <>
          <div className="what-if__comparison">
            <div className="card">
              <h2>Current State</h2>
              <AdaptationDecisionPanel recommendation={result.current} />
            </div>
            <div className="card">
              <h2>Simulated State</h2>
              <AdaptationDecisionPanel recommendation={result.simulated} />
            </div>
          </div>

          <div className="card">
            <h2>What Changed?</h2>
            <WhatChanged changes={result.changes} current={result.current} simulated={result.simulated} />
          </div>
        </>
      )}

      <div className="card what-if__safety-note">
        <p>
          <strong>Simulation only.</strong> No changes were made to your profile or history.
        </p>
      </div>

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

/** Factual differences only — no "better"/"worse"/"ideal" labels. */
function WhatChanged({ changes, current, simulated }) {
  const hasBarrierChange = changes.barriers_added.length > 0 || changes.barriers_removed.length > 0;

  if (!hasBarrierChange && !changes.adaptation_changed) {
    return <p>No change — the same barriers and adaptation apply either way.</p>;
  }

  return (
    <ul className="what-if__changes">
      {changes.barriers_removed.map((type) => (
        <li key={`removed-${type}`}>Barrier removed: {type.replaceAll("_", " ")}</li>
      ))}
      {changes.barriers_added.map((type) => (
        <li key={`added-${type}`}>Barrier added: {type.replaceAll("_", " ")}</li>
      ))}
      {changes.adaptation_changed && (
        <li>
          Adaptation changed: {current.selected_adaptation?.name || "none required"} →{" "}
          {simulated.selected_adaptation?.name || "none required"}
        </li>
      )}
    </ul>
  );
}
