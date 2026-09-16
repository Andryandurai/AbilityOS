import "./DeveloperPanel.css";

// Phase 6 section 7: the frontend's known-safe presentation vocabulary —
// mirrors backend/adaptations/services/config.py's ALLOWED_UI_EFFECT_KEYS.
// An effect key outside this list is never silently applied; it's
// surfaced here as a visible developer-facing warning instead.
const KNOWN_UI_EFFECT_KEYS = new Set([
  "button_scale",
  "spacing_scale",
  "contrast",
  "text_scale",
  "flow",
  "choice_limit",
  "progress_indicator",
  "voice_prompts",
  "tts",
  "banner_alert",
  "haptics",
  "voice_input",
  "confirm_step",
  "reachable_layout",
  "touch_text_mode",
  "extended_timeout_seconds",
]);

const BARRIER_LABELS = {
  small_tap_targets: "Small tap targets",
  low_contrast: "Low contrast / small text",
  too_many_choices: "Too many simultaneous choices",
  audio_only_alert: "Audio-only alert",
  fatigue_degraded_precision: "Fatigue-degraded precision",
  controls_out_of_reach: "Controls outside comfortable reach",
  voice_only_input: "Voice-only / speech-dependent interaction",
  excessive_interaction_burden: "Excessive interaction burden",
  time_limited_interaction: "Time-limited interaction",
  accidental_activation_risk: "Accidental activation risk",
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
const EASE_LABELS = { 1: "1/5 — Very difficult", 2: "2/5 — Difficult", 3: "3/5 — Okay", 4: "4/5 — Easy", 5: "5/5 — Very easy" };
const HELPFULNESS_LABELS = { helped: "Helped", somewhat_helped: "Somewhat helped", did_not_help: "Did not help" };
const SESSION_STATUS_LABELS = {
  started: "Started", analyzed: "Analyzed", adapted: "Adapted", in_progress: "In progress",
  completed: "Completed", abandoned: "Abandoned", failed: "Failed",
};

export default function DeveloperPanel({
  profile, task, environment, barriers, results, appliedAdaptations, aiUsed, aiError,
  sessionStatus, assistanceCount, completionTimeMs, outcomeScore, learningSignal, feedback,
}) {
  // Phase 6 section 34 (Developer/System view): a single consolidated
  // line showing exactly what's live on the kiosk right now. `results`
  // is fetched once at recommend-time and its `applied` flag is never
  // refreshed after the later apply step, so it can't be trusted alone —
  // `appliedAdaptations` (the apply response's own adaptation-name list)
  // is the source of truth for what's actually live.
  const appliedNames = new Set(appliedAdaptations || []);
  const appliedResults = results.filter((r) => r.applied || appliedNames.has(r.adaptation?.name));

  // Defensive/visible-only check: flag any ui_effects key the frontend
  // doesn't recognize. KioskView already ignores unknown keys when
  // rendering, so this never changes behavior — it just makes an
  // unrecognized key visible to a developer instead of silently doing
  // nothing.
  const unknownEffectKeys = [
    ...new Set(
      appliedResults.flatMap((r) => Object.keys(r.adaptation?.ui_effects || {})).filter((key) => !KNOWN_UI_EFFECT_KEYS.has(key))
    ),
  ];

  // Phase 8 section 56: a judge-legible "at a glance" summary — the same
  // facts the sections below show in full detail, condensed into one row
  // so a judge can read the whole story without scrolling.
  const primaryBarrier = barriers[0];
  const primaryAdaptation = appliedResults[0]?.adaptation?.display_name;
  const resultText =
    sessionStatus === "completed"
      ? assistanceCount > 0
        ? "Completed with assistance"
        : "Completed independently"
      : sessionStatus === "abandoned"
        ? "Not completed"
        : sessionStatus
          ? "In progress"
          : "Not started yet";

  return (
    <div className="card dev-panel">
      <h2>Developer / Explanation Panel</h2>
      <p className="dev-panel__subtitle">
        PERSON → ABILITY PROFILE → TASK → ENVIRONMENT → BARRIER DETECTION → ADAPTATION DECISION → SAFETY VALIDATION →
        RESULT
      </p>

      <dl className="dev-panel__glance">
        <div>
          <dt>WHO</dt>
          <dd>{profile?.label || "—"}</dd>
        </div>
        <div>
          <dt>WHAT</dt>
          <dd>{task?.name || "—"}</dd>
        </div>
        <div>
          <dt>WHERE</dt>
          <dd>{environment?.environment_id || "—"}</dd>
        </div>
        <div>
          <dt>WHY</dt>
          <dd>{primaryBarrier ? BARRIER_LABELS[primaryBarrier.barrier_type] || primaryBarrier.barrier_type : "No barrier detected"}</dd>
        </div>
        <div>
          <dt>CHANGE</dt>
          <dd>{primaryAdaptation || "None applied"}</dd>
        </div>
        <div>
          <dt>RESULT</dt>
          <dd>{resultText}</dd>
        </div>
      </dl>

      <p className="dev-panel__user">
        User: <strong>{profile?.label || "—"}</strong>
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
              <span className="pill pill--low">{r.adaptation.display_name}</span>
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
              {(r.applied || appliedNames.has(r.adaptation?.name)) ? " · applied to the interface" : ""}
            </p>
          </div>
        ))}

        <p className="dev-panel__applied-summary">
          {appliedResults.length > 0
            ? `Applied: ✓ ${appliedResults.map((r) => r.adaptation.display_name).join(", ")}`
            : "Applied: none yet — waiting for confirmation or apply step."}
        </p>
        {unknownEffectKeys.length > 0 && (
          <p className="dev-panel__ai-note" role="status">
            Note: applied adaptation includes unrecognized effect key(s) ({unknownEffectKeys.join(", ")}) — ignored by
            the kiosk renderer, standard presentation used for those.
          </p>
        )}
      </section>

      {sessionStatus && (
        <section className="dev-panel__section">
          <h3>
            Outcome{" "}
            <span className="pill pill--neutral">{SESSION_STATUS_LABELS[sessionStatus] || sessionStatus}</span>
          </h3>
          <ul className="dev-panel__dims">
            <li>
              Interaction: completed in{" "}
              <strong>{completionTimeMs != null ? `${Math.round(completionTimeMs / 1000)} sec` : "—"}</strong>
            </li>
            <li>
              Assistance:{" "}
              <strong>
                {assistanceCount == null
                  ? "—"
                  : assistanceCount === 0
                    ? "No"
                    : `Yes (${assistanceCount} request${assistanceCount > 1 ? "s" : ""})`}
              </strong>
            </li>
            {feedback && (
              <>
                <li>
                  Feedback:{" "}
                  <strong>{feedback.ease_rating ? EASE_LABELS[feedback.ease_rating] : "not rated"}</strong>
                </li>
                {feedback.adaptation_helpfulness && (
                  <li>
                    Adaptation helpful: <strong>{HELPFULNESS_LABELS[feedback.adaptation_helpfulness]}</strong>
                  </li>
                )}
              </>
            )}
          </ul>

          {outcomeScore && (
            <p className="dev-panel__evidence">
              Outcome score (Phase 7 section 18, deterministic — see analytics/config.py):{" "}
              <strong>{outcomeScore.score.toFixed(2)}</strong> / 1.00
            </p>
          )}

          {learningSignal ? (
            <div className="dev-panel__decision">
              <h4>Learning signal</h4>
              <p className="dev-panel__validation">
                {learningSignal.independence_improved ? "✓ Positive" : learningSignal.successful ? "Partial" : "✗ Negative"}
                {" · "}
                <span className="dev-panel__evidence">
                  {learningSignal.adaptation_id} resolved {learningSignal.barrier_type} for {learningSignal.task_id}
                </span>
              </p>
              <p className="dev-panel__evidence">
                Structured evidence, not a statistical claim — confidence {learningSignal.confidence.toFixed(2)} from
                this one session (Phase 7 section 50).
              </p>
            </div>
          ) : (
            <p className="dev-panel__evidence">
              No learning signal for this session (no adaptation was applied, or feedback hasn't been submitted yet).
            </p>
          )}
        </section>
      )}
    </div>
  );
}
