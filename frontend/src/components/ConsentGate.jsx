import { useState } from "react";

/**
 * Part 27 (Privacy): AbilityOS never uses a person's functional profile
 * without a visible, explicit consent step. Blocks the rest of the demo
 * until the presenter agrees on behalf of whichever demo persona is active.
 */
export default function ConsentGate({ onAgree }) {
  const [submitting, setSubmitting] = useState(false);

  const handleAgree = async () => {
    setSubmitting(true);
    try {
      await onAgree();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card" role="dialog" aria-labelledby="consent-title" style={{ maxWidth: 560, margin: "48px auto" }}>
      <h2 id="consent-title">Before we start</h2>
      <p>
        AbilityOS uses your functional interaction profile only to adapt the current
        interaction — what you can comfortably see, reach, hear or process right now.
        It is <strong>not</strong> a medical record, and it is never used to diagnose you.
      </p>
      <p>
        You can change or clear this profile at any time, and nothing is shared outside
        this session.
      </p>
      <div className="row" style={{ justifyContent: "flex-end", marginTop: "var(--space-4)" }}>
        <button className="btn btn--primary" onClick={handleAgree} disabled={submitting} autoFocus>
          {submitting ? "Recording consent…" : "I Agree"}
        </button>
      </div>
    </div>
  );
}
