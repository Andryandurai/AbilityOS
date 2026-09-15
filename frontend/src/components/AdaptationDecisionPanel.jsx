import "./AdaptationDecisionPanel.css";

/** The `candidates` list only carries {adaptation_id, score} — this turns
 * "increase_target_size" into "Increase target size" for display, since
 * the backend doesn't send a display name for every candidate (only for
 * the final selected_adaptation). */
function humanize(adaptationId) {
  const words = adaptationId.split("_");
  return words[0].charAt(0).toUpperCase() + words[0].slice(1) + " " + words.slice(1).join(" ");
}

/**
 * Phase 5 developer reasoning view (section 33): Candidate Interventions ->
 * AI Decision -> Safety Validation -> Approved Adaptation. Shows the full
 * chain a judge needs to see — this panel only ever *displays* the
 * decision, it never applies anything to the kiosk (Phase 6's job).
 */
export default function AdaptationDecisionPanel({ recommendation, onOpenKiosk }) {
  const { barriers, candidates, selected_adaptation: selected, reason } = recommendation;

  // Phase 6 section 39 ("safe default"): only ever offer to open the
  // adaptive kiosk when the backend actually approved and validated a
  // selection. No approved adaptation -> the standard kiosk is still
  // reachable via the header's Kiosk Demo link, just nothing here claims
  // an adaptation exists when it doesn't.
  if (!selected) {
    return (
      <div className="adaptation-decision">
        <h3>Adaptation Decision</h3>
        <p>{reason || "No approved adaptation is available."}</p>
        <p className="dev-panel__ai-note">
          Personalized adaptation is unavailable for this combination — the standard kiosk experience would be used.
        </p>
      </div>
    );
  }

  return (
    <div className="adaptation-decision">
      <h3>Adaptation Decision</h3>

      <section className="adaptation-decision__section">
        <h4>Detected Barrier{barriers.length > 1 ? "s" : ""}</h4>
        <p>{barriers.map((b) => b.title).join(", ")}</p>
      </section>

      <section className="adaptation-decision__section">
        <h4>Candidate Interventions</h4>
        <ul className="adaptation-decision__candidates">
          {candidates.map((c) => {
            const isSelected = c.adaptation_id === selected.adaptation_id;
            return (
              <li key={c.adaptation_id} className={isSelected ? "adaptation-decision__candidate--selected" : ""}>
                <span aria-hidden="true">{isSelected ? "✓" : "○"}</span> {humanize(c.adaptation_id)}
                <span className="adaptation-decision__score"> — score {c.score.toFixed(2)}</span>
              </li>
            );
          })}
        </ul>
      </section>

      <section className="adaptation-decision__section">
        <h4>
          AI Decision{" "}
          <span className={`pill ${selected.source === "ai" ? "pill--low" : "pill--neutral"}`}>
            {selected.source === "ai" ? "AI decision engine" : "Deterministic fallback"}
          </span>
        </h4>
        <p>
          Selected: <strong>{selected.name}</strong>
        </p>
        <p className="adaptation-decision__reason">&ldquo;{selected.reason}&rdquo;</p>
        {selected.ai_error && (
          <p className="dev-panel__ai-note">AI unavailable — deterministic fallback used ({selected.ai_error}).</p>
        )}
      </section>

      <section className="adaptation-decision__section">
        <h4>Safety Validation</h4>
        <p className="adaptation-decision__approved">
          ✓ Approved{selected.requires_confirmation ? " (requires confirmation before use)" : ""}
        </p>
        <p>Score: {selected.score.toFixed(2)}</p>
      </section>

      {onOpenKiosk && (
        <button className="btn btn--primary adaptation-decision__open-kiosk" onClick={onOpenKiosk}>
          Open Adaptive Kiosk
        </button>
      )}
    </div>
  );
}
