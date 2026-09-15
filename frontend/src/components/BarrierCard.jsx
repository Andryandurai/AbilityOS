import { useState } from "react";
import "./BarrierCard.css";

const DIMENSION_LABELS = {
  dexterity: "Dexterity",
  vision: "Vision",
  cognition: "Cognition",
  hearing: "Hearing",
};

function evidenceLines(barrier) {
  const { barrier_type: type, evidence } = barrier;
  if (type === "small_tap_targets") {
    return {
      environment: (evidence.controls || [])
        .map((c) => `${c.id}: ${c.width} × ${c.height}px`)
        .join(", "),
      rule: evidence.threshold ? `Minimum configured target = ${evidence.threshold.min_width} × ${evidence.threshold.min_height}px` : "",
    };
  }
  if (type === "low_contrast_text") {
    return {
      environment: `Contrast ratio = ${evidence.contrast_ratio}:1`,
      rule: `Minimum configured ratio = ${evidence.threshold}:1 (WCAG AA)`,
    };
  }
  if (type === "too_many_choices") {
    return {
      environment: `${evidence.choice_count} simultaneous choices`,
      rule: `Maximum configured comfortable choices = ${evidence.threshold}`,
    };
  }
  if (type === "audio_only_alert") {
    return {
      environment: (evidence.alerts || []).map((a) => `${a.id}: audio-only, critical`).join(", "),
      rule: "No visual alternative present for a critical audio alert",
    };
  }
  return { environment: JSON.stringify(evidence), rule: "" };
}

/** One detected barrier, with an expandable "Why was this detected?"
 * panel (Phase 4 section 28) tracing Ability -> Task/Environment fact ->
 * Rule -> Result — the deterministic reasoning behind the card, not
 * generic AI language. */
export default function BarrierCard({ barrier }) {
  const [expanded, setExpanded] = useState(false);
  const { environment, rule } = evidenceLines(barrier);
  const severityPct = Math.round(barrier.severity * 100);

  return (
    <div className="barrier-card">
      <div className="barrier-card__header">
        <h3>{barrier.title}</h3>
        <span className="pill pill--high">{DIMENSION_LABELS[barrier.ability_dimension] || barrier.ability_dimension}</span>
      </div>

      <div className="barrier-card__severity" role="img" aria-label={`Severity ${severityPct} percent`}>
        <div className="barrier-card__severity-bar">
          <div className="barrier-card__severity-fill" style={{ width: `${severityPct}%` }} />
        </div>
        <span>Severity: {severityPct}%</span>
      </div>

      <p>{barrier.description}</p>

      <button
        type="button"
        className="barrier-card__why-toggle"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        {expanded ? "Hide" : "Why was this detected?"}
      </button>

      {expanded && (
        <dl className="barrier-card__why">
          <div>
            <dt>Ability</dt>
            <dd>
              {barrier.evidence.ability_value} ({DIMENSION_LABELS[barrier.ability_dimension] || barrier.ability_dimension})
            </dd>
          </div>
          <div>
            <dt>Environment</dt>
            <dd>{environment || "—"}</dd>
          </div>
          {rule && (
            <div>
              <dt>Rule</dt>
              <dd>{rule}</dd>
            </div>
          )}
          <div>
            <dt>Result</dt>
            <dd>{barrier.description}</dd>
          </div>
          <div>
            <dt>Confidence</dt>
            <dd>{Math.round(barrier.confidence * 100)}%</dd>
          </div>
        </dl>
      )}
    </div>
  );
}
