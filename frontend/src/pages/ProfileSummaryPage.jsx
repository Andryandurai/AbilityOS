import { useState } from "react";
import JourneyIndicator from "../components/JourneyIndicator";
import { summarizeProfile } from "../constants/abilityProfile";
import "./ProfileFlow.css";

/**
 * Phase 2 sections 9/21: the human-friendly "AbilityOS Understands" summary,
 * plus an optional Developer View exposing the raw level/confidence/source
 * data this profile will hand to Barrier Detection in later phases.
 */
export default function ProfileSummaryPage({ profile, consent, onContinue, onEditAgain, onClearProfile, busy }) {
  const [showDeveloperView, setShowDeveloperView] = useState(false);
  const entries = summarizeProfile(profile);

  return (
    <div className="profile-flow">
      <JourneyIndicator currentStep="summary" />
      <div className="card profile-flow__wide">
        <h1>AbilityOS Understands</h1>

        {entries.length === 0 ? (
          <p>No specific adaptations needed — this profile is typical across the board.</p>
        ) : (
          <ul className="profile-summary__list">
            {entries.map((entry) => (
              <li key={entry.text}>
                <span aria-hidden="true">{entry.emoji}</span> {entry.text}
              </li>
            ))}
          </ul>
        )}

        <div className="row profile-flow__actions">
          <button className="btn btn--ghost" onClick={onEditAgain}>
            Edit Profile
          </button>
          <button className="btn btn--ghost" onClick={onClearProfile} disabled={busy}>
            Clear Profile
          </button>
          <button className="btn btn--primary" onClick={onContinue}>
            Continue to Task &amp; Environment
          </button>
        </div>

        <button
          type="button"
          className="profile-summary__dev-toggle"
          onClick={() => setShowDeveloperView((v) => !v)}
          aria-expanded={showDeveloperView}
        >
          {showDeveloperView ? "Hide" : "Show"} Developer View
        </button>

        {showDeveloperView && (
          <div className="profile-summary__dev-panel">
            <h2>Ability Profile</h2>
            <ul className="profile-summary__dev-list">
              {Object.entries(profile?.dimensions || {}).map(([key, dim]) => (
                <li key={key}>
                  <strong>{key}</strong>: {dim.level}{" "}
                  <span className="pill pill--neutral">confidence {dim.confidence.toFixed(2)}</span>{" "}
                  <span className="pill pill--neutral">{dim.source}</span>
                </li>
              ))}
              <li>
                <strong>preferred_modality</strong>: {profile?.preferred_modality}
              </li>
            </ul>
            <h2>Consent</h2>
            <p>
              granted: <strong>{consent?.granted ? "true" : "false"}</strong> · scope:{" "}
              {(consent?.scope || []).join(", ") || "none"}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
