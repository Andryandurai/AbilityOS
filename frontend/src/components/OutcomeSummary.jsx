const EASE_LABELS = { 1: "Very difficult", 2: "Difficult", 3: "Okay", 4: "Easy", 5: "Very easy" };
const HELPFULNESS_LABELS = { helped: "Helped", somewhat_helped: "Somewhat helped", did_not_help: "Did not help" };

/**
 * Phase 7 section 48: the user-facing outcome summary — plain language
 * only. No barrier IDs, no confidence scores, no adaptation engine
 * internals (section 25); that technical chain lives in DeveloperPanel
 * instead, for the separate developer/system view.
 */
export default function OutcomeSummary({ taskName, completed, adaptive, feedback }) {
  return (
    <div className="card" role="status">
      <h2>{completed ? "Task complete ✓" : "Task not completed"}</h2>
      <dl>
        <div className="row" style={{ justifyContent: "space-between" }}>
          <dt>You completed:</dt>
          <dd>
            <strong>{taskName}</strong>
          </dd>
        </div>
        <div className="row" style={{ justifyContent: "space-between" }}>
          <dt>Experience:</dt>
          <dd>{adaptive ? "Personalized interaction" : "Standard interaction"}</dd>
        </div>
        {feedback?.ease_rating && (
          <div className="row" style={{ justifyContent: "space-between" }}>
            <dt>Your feedback:</dt>
            <dd>{EASE_LABELS[feedback.ease_rating]}</dd>
          </div>
        )}
        {adaptive && feedback?.adaptation_helpfulness && (
          <div className="row" style={{ justifyContent: "space-between" }}>
            <dt>Adaptation:</dt>
            <dd>{HELPFULNESS_LABELS[feedback.adaptation_helpfulness]}</dd>
          </div>
        )}
        {feedback && (
          <div className="row" style={{ justifyContent: "space-between" }}>
            <dt>Assistance:</dt>
            <dd>{feedback.assistance_requested ? "Required" : "Not required"}</dd>
          </div>
        )}
      </dl>
    </div>
  );
}
