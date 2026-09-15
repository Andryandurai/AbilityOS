import { useState } from "react";
import JourneyIndicator from "../components/JourneyIndicator";
import "./ProfileFlow.css";

/**
 * Phase 2 consent screen — exact copy from the spec. Always shown as a
 * real step (even for a seeded demo persona whose consent is already
 * granted, the checkbox just starts pre-checked reflecting that real
 * backend state) — unchecking it disables Continue for real, and
 * Continue always performs a real POST, never a client-only "looks
 * granted" shortcut (Phase 2 section 45).
 */
export default function ConsentPage({ alreadyGranted, onAgree, busy }) {
  const [checked, setChecked] = useState(!!alreadyGranted);
  const [submitting, setSubmitting] = useState(false);

  const handleContinue = async () => {
    setSubmitting(true);
    try {
      await onAgree();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="profile-flow">
      <JourneyIndicator currentStep="consent" />
      <div className="card profile-flow__narrow">
        <h1>Before we adapt technology for you</h1>
        <p>
          AbilityOS uses a small set of functional preferences to make digital
          interactions easier.
        </p>
        <p>
          We focus on what you can comfortably do — not on diagnosing medical
          conditions.
        </p>
        <p>We may use information such as:</p>
        <ul>
          <li>preferred text size</li>
          <li>touch precision</li>
          <li>preferred interaction method</li>
          <li>number of choices you prefer at once</li>
        </ul>
        <p>Your information is used only for accessibility adaptation.</p>

        <label className="consent-checkbox">
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => setChecked(e.target.checked)}
          />
          I agree to let AbilityOS use my profile for interaction adaptation.
        </label>

        <button
          className="btn btn--primary profile-flow__cta"
          disabled={!checked || submitting || busy}
          onClick={handleContinue}
        >
          {submitting ? "Saving…" : "Continue"}
        </button>

        <p className="profile-flow__note">Your profile can be edited at any time.</p>
      </div>
    </div>
  );
}
