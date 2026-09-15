import { useState } from "react";
import "../pages/ProfileFlow.css";

const EASE_OPTIONS = [
  { value: 1, label: "Very difficult" },
  { value: 2, label: "Difficult" },
  { value: 3, label: "Okay" },
  { value: 4, label: "Easy" },
  { value: 5, label: "Very easy" },
];

const HELPFULNESS_OPTIONS = [
  { value: "helped", label: "Yes" },
  { value: "somewhat_helped", label: "Somewhat" },
  { value: "did_not_help", label: "No" },
];

const ASSISTANCE_OPTIONS = [
  { value: false, label: "No" },
  { value: true, label: "Yes" },
];

const COMMENT_MAX_LENGTH = 500;

/**
 * Phase 7 section 12: the short, user-facing feedback screen — three plain
 * questions plus an optional comment, nothing technical (no barrier IDs,
 * no confidence scores, no adaptation engine internals; see section 25).
 * Shown once, after the task is already complete or abandoned server-side.
 */
export default function FeedbackForm({ adaptationApplied, defaultAssistance, onSubmit, busy }) {
  const [easeRating, setEaseRating] = useState(null);
  const [helpfulness, setHelpfulness] = useState(null);
  const [assistanceRequired, setAssistanceRequired] = useState(defaultAssistance ?? false);
  const [comment, setComment] = useState("");

  const canSubmit = easeRating !== null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    onSubmit({
      ease_rating: easeRating,
      adaptation_helpfulness: adaptationApplied ? helpfulness : undefined,
      assistance_requested: assistanceRequired,
      optional_comment: comment.trim() || undefined,
    });
  };

  return (
    <form className="card" onSubmit={handleSubmit} aria-labelledby="feedback-title">
      <h2 id="feedback-title">How was the experience?</h2>

      <fieldset className="profile-editor__group">
        <legend>
          <span className="profile-editor__question">How was the experience?</span>
        </legend>
        <div className="profile-editor__options" role="radiogroup" aria-label="How was the experience?">
          {EASE_OPTIONS.map((opt) => (
            <label key={opt.value} className="profile-editor__option">
              <input
                type="radio"
                name="ease_rating"
                checked={easeRating === opt.value}
                onChange={() => setEaseRating(opt.value)}
              />
              {opt.label}
            </label>
          ))}
        </div>
      </fieldset>

      {adaptationApplied && (
        <fieldset className="profile-editor__group">
          <legend>
            <span className="profile-editor__question">Did the adapted interface help?</span>
          </legend>
          <div className="profile-editor__options" role="radiogroup" aria-label="Did the adapted interface help?">
            {HELPFULNESS_OPTIONS.map((opt) => (
              <label key={opt.value} className="profile-editor__option">
                <input
                  type="radio"
                  name="adaptation_helpfulness"
                  checked={helpfulness === opt.value}
                  onChange={() => setHelpfulness(opt.value)}
                />
                {opt.label}
              </label>
            ))}
          </div>
        </fieldset>
      )}

      <fieldset className="profile-editor__group">
        <legend>
          <span className="profile-editor__question">Did you need help from another person?</span>
        </legend>
        <div className="profile-editor__options" role="radiogroup" aria-label="Did you need help from another person?">
          {ASSISTANCE_OPTIONS.map((opt) => (
            <label key={String(opt.value)} className="profile-editor__option">
              <input
                type="radio"
                name="assistance_required"
                checked={assistanceRequired === opt.value}
                onChange={() => setAssistanceRequired(opt.value)}
              />
              {opt.label}
            </label>
          ))}
        </div>
      </fieldset>

      <div className="profile-editor__group" style={{ borderTop: "1px solid var(--color-border)", paddingTop: "var(--space-4)" }}>
        <label htmlFor="optional_comment" className="profile-editor__question" style={{ display: "block", marginBottom: "var(--space-2)" }}>
          What could be improved? <span style={{ fontWeight: 400 }}>(optional)</span>
        </label>
        <textarea
          id="optional_comment"
          value={comment}
          onChange={(e) => setComment(e.target.value.slice(0, COMMENT_MAX_LENGTH))}
          maxLength={COMMENT_MAX_LENGTH}
          rows={3}
          style={{ width: "100%", fontFamily: "inherit", fontSize: "1rem", padding: "var(--space-2)" }}
        />
      </div>

      <div className="row" style={{ justifyContent: "flex-end", marginTop: "var(--space-4)" }}>
        <button type="submit" className="btn btn--primary" disabled={!canSubmit || busy}>
          {busy ? "Submitting…" : "Submit feedback"}
        </button>
      </div>
    </form>
  );
}
