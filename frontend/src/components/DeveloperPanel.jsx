import "./DeveloperPanel.css";

const BARRIER_LABELS = {
  small_tap_targets: "Small tap targets",
  low_contrast: "Low contrast / small text",
  too_many_choices: "Too many simultaneous choices",
  audio_only_alert: "Audio-only alert",
  fatigue_degraded_precision: "Fatigue-degraded precision",
};

function RiskPill({ level }) {
  return <span className={`pill pill--${level}`}>{level} risk</span>;
}

function CandidateRow({ candidate, isWinner }) {
  return (
    <li className={`candidate-row ${isWinner ? "candidate-row--winner" : ""}`}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <strong>{candidate.display_name}</strong>
        <span>score {candidate.score.toFixed(2)}</span>
      </div>
      <div className="candidate-row__breakdown">
        benefit {candidate.breakdown.accessibility_benefit.toFixed(2)} · task-fit{" "}
        {candidate.breakdown.task_relevance.toFixed(2)} · preference {candidate.breakdown.user_preference.toFixed(2)} ·
        confidence {candidate.breakdown.confidence.toFixed(2)} − cost {candidate.breakdown.interaction_cost.toFixed(2)} −
        risk {candidate.breakdown.risk.toFixed(2)}
      </div>
    </li>
  );
}

/**
 * The judge-facing "why" panel (Part 14/39). Shows the same nine-stage loop
 * from Part 3 populated with the real API responses for the current
 * session — not a canned explanation.
 */
export default function DeveloperPanel({ profile, task, environment, barriers, results, aiUsed, aiError }) {
  return (
    <div className="card dev-panel">
      <h2>Developer / Explanation Panel</h2>
      <p className="dev-panel__subtitle">
        PERSON → ABILITY PROFILE → TASK → ENVIRONMENT → BARRIER DETECTION → ADAPTATION DECISION → SAFETY VALIDATION →
        RESULT
      </p>

      <section className="dev-panel__section">
        <h3>Ability Profile in use</h3>
        {profile ? (
          <ul className="dev-panel__dims">
            {Object.entries(profile.dimensions)
              .filter(([, v]) => v.level !== "typical")
              .map(([key, v]) => (
                <li key={key}>
                  <strong>{key}</strong>: {v.level} <span className="pill pill--neutral">confidence {v.confidence.toFixed(2)}</span>{" "}
                  <span className="pill pill--neutral">{v.source}</span>
                </li>
              ))}
          </ul>
        ) : (
          <p>No profile selected yet.</p>
        )}
      </section>

      <section className="dev-panel__section">
        <h3>Task &amp; Environment</h3>
        <p>
          Task: <strong>{task?.name || "—"}</strong>
          {environment && (
            <>
              {" "}
              · Environment: <strong>{environment.environment_id}</strong> (contrast{" "}
              {environment.data.contrast?.toFixed?.(2)}, {environment.data.visible_choice_count} visible choices)
            </>
          )}
        </p>
      </section>

      <section className="dev-panel__section">
        <h3>Detected barriers</h3>
        {barriers.length === 0 ? (
          <p>No barriers detected for this profile/task/environment combination.</p>
        ) : (
          <ul className="dev-panel__barriers">
            {barriers.map((b) => (
              <li key={b.id}>
                <span className="pill pill--high">{BARRIER_LABELS[b.barrier_type] || b.barrier_type}</span>
                <span> severity {b.severity.toFixed(2)} · confidence {b.confidence.toFixed(2)}</span>
                <div className="dev-panel__evidence">{b.evidence}</div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="dev-panel__section">
        <h3>
          AI reasoning{" "}
          <span className={`pill ${aiUsed ? "pill--low" : "pill--neutral"}`}>
            {aiUsed ? "AI decision engine" : "Deterministic fallback"}
          </span>
        </h3>
        {aiError && (
          <p className="dev-panel__ai-note">AI unavailable — deterministic fallback used ({aiError}).</p>
        )}
        {!aiUsed && !aiError && (
          <p className="dev-panel__ai-note">
            No AI provider configured — using the deterministic Adaptation Engine scoring formula.
          </p>
        )}

        {results.map((r) => (
          <div key={r.id} className="dev-panel__decision">
            <h4>
              Barrier: {BARRIER_LABELS[r.barrier_type] || r.barrier_type} →{" "}
              <span className="pill pill--low">{r.display_name}</span>
              {r.requires_confirmation && <RiskPill level="high" />}
            </h4>
            <p className="dev-panel__rationale">&ldquo;{r.rationale}&rdquo;</p>
            <details>
              <summary>Show {r.candidates_considered.length} candidate adaptation(s) considered</summary>
              <ul className="candidate-list">
                {r.candidates_considered.map((c) => (
                  <CandidateRow key={c.adaptation} candidate={c} isWinner={c.adaptation === r.adaptation.name} />
                ))}
              </ul>
            </details>
            <p className="dev-panel__validation">
              Rule engine: {r.approved ? "✓ approved" : "✗ rejected"}
              {r.applied ? " · applied to the interface" : ""}
            </p>
          </div>
        ))}
      </section>
    </div>
  );
}
