import { useEffect, useState } from "react";
import * as api from "../services/api";
import "./ProfileFlow.css";
import "./SuggestedProfilesPage.css";

const DIMENSION_LABELS = {
  vision: "Vision",
  hearing: "Hearing",
  dexterity: "Dexterity",
  reach: "Reach",
  mobility: "Mobility",
  speech: "Speech",
  cognition: "Cognition",
  fatigue: "Fatigue",
  reaction_speed: "Reaction Speed",
  interaction_sensitivity: "Interaction Sensitivity",
};

/**
 * Phase 3 (Profile Suggestions & User Profile Selection) — reuses
 * SelectUserPage.jsx's card/grid visual language (section 16). Suggestions
 * are deterministic and explainable (every card shows exactly which
 * dimensions caused it) -- never a fabricated confidence score, never AI.
 *
 * Nothing on this page ever writes to AbilityProfile: accepting,
 * rejecting, or manually adding a profile only ever creates/updates a
 * UserProfileSelection row (see docs/PROFILE_SUGGESTIONS.md's mutation
 * rule) through the existing validated API.
 */
export default function SuggestedProfilesPage({ userId, onComplete, onBack }) {
  const [phase, setPhase] = useState("loading"); // loading | error | browsing | confirming
  const [suggestions, setSuggestions] = useState([]);
  const [allProfiles, setAllProfiles] = useState([]);
  const [selections, setSelections] = useState({}); // { [profile_key]: status }
  const [showAddPicker, setShowAddPicker] = useState(false);
  const [busyKey, setBusyKey] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [suggestionData, selectionRows] = await Promise.all([
          api.getProfileSuggestions(userId),
          api.getProfileSelections(userId),
        ]);
        if (cancelled) return;
        setSuggestions(suggestionData.suggestions);
        setAllProfiles(suggestionData.all_profiles);
        setSelections(Object.fromEntries(selectionRows.map((r) => [r.profile_key, r.status])));
        setPhase("browsing");
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
          setPhase("error");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [userId]);

  const setStatus = async (profileKey, status) => {
    setBusyKey(profileKey);
    setError(null);
    try {
      await api.upsertProfileSelection(userId, profileKey, status);
      setSelections((prev) => ({ ...prev, [profileKey]: status }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyKey(null);
    }
  };

  const removeSelection = async (profileKey) => {
    setBusyKey(profileKey);
    setError(null);
    try {
      await api.deleteProfileSelection(userId, profileKey);
      setSelections((prev) => {
        const next = { ...prev };
        delete next[profileKey];
        return next;
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyKey(null);
    }
  };

  if (phase === "loading") {
    return (
      <div className="profile-flow">
        <div className="card profile-flow__narrow">Loading suggested profiles…</div>
      </div>
    );
  }

  if (phase === "error") {
    return (
      <div className="profile-flow">
        <div className="card profile-flow__narrow" role="alert">
          <p>Unable to load suggested profiles.</p>
          <p className="suggested-profiles__error">{error}</p>
        </div>
      </div>
    );
  }

  if (phase === "confirming") {
    const selectedEntries = allProfiles.filter((p) =>
      ["accepted", "manually_added"].includes(selections[p.profile_key])
    );
    return (
      <div className="profile-flow">
        <div className="card profile-flow__wide">
          <h1>Your selected profiles</h1>
          {selectedEntries.length === 0 ? (
            <p>You haven't selected any profiles — that's okay, you can always add one later.</p>
          ) : (
            <ul className="suggested-profiles__confirm-list">
              {selectedEntries.map((p) => (
                <li key={p.profile_key}>✓ {p.name}</li>
              ))}
            </ul>
          )}
          <p className="profile-flow__subtitle">
            These selections will be used to personalize your AbilityOS experience.
          </p>
          <div className="row profile-flow__actions">
            <button type="button" className="btn btn--ghost" onClick={() => setPhase("browsing")}>
              Back
            </button>
            <button type="button" className="btn btn--primary" onClick={onComplete}>
              Confirm &amp; Continue
            </button>
          </div>
        </div>
      </div>
    );
  }

  const suggestedKeys = new Set(suggestions.map((s) => s.profile_key));
  const addedProfiles = allProfiles.filter(
    (p) => !suggestedKeys.has(p.profile_key) && selections[p.profile_key] === "manually_added"
  );
  const pickableProfiles = allProfiles.filter((p) => !suggestedKeys.has(p.profile_key) && !selections[p.profile_key]);

  return (
    <div className="profile-flow">
      <div className="card profile-flow__intro">
        <h1>Suggested Profiles</h1>
        <p>
          Based on the abilities you selected, AbilityOS found these profile patterns that may help personalize
          your experience.
        </p>
      </div>

      {error && (
        <div className="card" role="alert">
          <p className="suggested-profiles__error">{error}</p>
        </div>
      )}

      {suggestions.length === 0 ? (
        <div className="card">
          <p>No specific profile patterns matched your current answers — that's completely fine. You can still add
          a profile manually below.</p>
        </div>
      ) : (
        <div className="user-select__grid">
          {suggestions.map((s) => {
            const status = selections[s.profile_key];
            return (
              <div key={s.profile_key} className="card user-select__card">
                <h2>{s.name}</h2>
                <p className="user-select__needs-label">Matches your profile:</p>
                <ul className="user-select__needs">
                  {s.matched_dimensions.map((dim) => (
                    <li key={dim}>
                      ✓ {DIMENSION_LABELS[dim] || dim}
                    </li>
                  ))}
                </ul>
                {status === "accepted" ? (
                  <div className="row">
                    <span className="suggested-profiles__status suggested-profiles__status--accepted">
                      ✓ Selected
                    </span>
                    <button
                      type="button"
                      className="btn btn--ghost"
                      onClick={() => setStatus(s.profile_key, "rejected")}
                      disabled={busyKey === s.profile_key}
                    >
                      Not for me
                    </button>
                  </div>
                ) : status === "rejected" ? (
                  <div className="row">
                    <span className="suggested-profiles__status">Not relevant</span>
                    <button
                      type="button"
                      className="btn btn--ghost"
                      onClick={() => setStatus(s.profile_key, "accepted")}
                      disabled={busyKey === s.profile_key}
                    >
                      Select after all
                    </button>
                  </div>
                ) : (
                  <div className="row">
                    <button
                      type="button"
                      className="btn btn--primary"
                      onClick={() => setStatus(s.profile_key, "accepted")}
                      disabled={busyKey === s.profile_key}
                    >
                      Select
                    </button>
                    <button
                      type="button"
                      className="btn btn--ghost"
                      onClick={() => setStatus(s.profile_key, "rejected")}
                      disabled={busyKey === s.profile_key}
                    >
                      Not for me
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {addedProfiles.length > 0 && (
        <div className="card">
          <p className="user-select__needs-label">Manually added</p>
          <div className="user-select__grid">
            {addedProfiles.map((p) => (
              <div key={p.profile_key} className="card user-select__card">
                <h2>{p.name}</h2>
                <p>{p.description}</p>
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => removeSelection(p.profile_key)}
                  disabled={busyKey === p.profile_key}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        {showAddPicker ? (
          <>
            <p className="user-select__needs-label">Add another profile</p>
            {pickableProfiles.length === 0 ? (
              <p>Every profile has already been suggested or added.</p>
            ) : (
              <ul className="suggested-profiles__picker-list">
                {pickableProfiles.map((p) => (
                  <li key={p.profile_key}>
                    <button
                      type="button"
                      className="btn btn--ghost"
                      onClick={() => setStatus(p.profile_key, "manually_added")}
                      disabled={busyKey === p.profile_key}
                    >
                      + {p.name}
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <button type="button" className="btn btn--ghost" onClick={() => setShowAddPicker(false)}>
              Close
            </button>
          </>
        ) : (
          <button type="button" className="btn btn--ghost" onClick={() => setShowAddPicker(true)}>
            + Add another profile
          </button>
        )}
      </div>

      <div className="row profile-flow__actions">
        {onBack && (
          <button type="button" className="btn btn--ghost" onClick={onBack}>
            Back
          </button>
        )}
        <button type="button" className="btn btn--primary" onClick={() => setPhase("confirming")}>
          Continue
        </button>
      </div>
    </div>
  );
}
