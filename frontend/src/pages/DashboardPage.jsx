import { useEffect, useState } from "react";
import * as api from "../services/api";
import { hasCustomizedDimensions, summarizeProfile } from "../constants/abilityProfile";
import "./ProfileFlow.css";
import "./DashboardPage.css";

/**
 * Phase 4 (Personalized Dashboard) — the authenticated home screen.
 *
 * `profile` is not re-fetched here: App.jsx's useProfileFlow already holds
 * it (selectUser() is awaited before this page is ever rendered), so this
 * page reuses that single source of truth rather than issuing a second,
 * possibly-inconsistent GET .../ability-profile/ (section 27's "reuse
 * existing state" guidance).
 *
 * The only new reads are the same profile-suggestions / profile-selections
 * pair SuggestedProfilesPage.jsx already fetches (Phase 3) — needed
 * because GET .../profile-selections/ intentionally has no display `name`
 * field of its own (see docs/PROFILE_SUGGESTIONS.md); `all_profiles` from
 * the suggestions endpoint is the one place that name lives.
 */
export default function DashboardPage({
  user,
  profile,
  consentGranted,
  onSetupProfile,
  onEditProfile,
  onManageProfiles,
  onStartExperience,
  onGrantConsent,
  onViewHistory,
  onExploreWhatIf,
  onHome,
  onLogout,
}) {
  const [phase, setPhase] = useState("loading"); // loading | ready | error
  const [allProfiles, setAllProfiles] = useState([]);
  const [selections, setSelections] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [error, setError] = useState(null);
  const [retryKey, setRetryKey] = useState(0);

  const userId = user?.id;

  useEffect(() => {
    if (!userId) return undefined;
    let cancelled = false;
    setPhase("loading");
    setError(null);
    (async () => {
      try {
        // Phase 6: getUserSessions() joins the same Promise.all as the
        // existing Phase 3 fetches rather than a separate effect -- one
        // combined loading/error/retry state for Dashboard's initial load,
        // matching how the two Phase 3 calls were already handled.
        const [suggestionData, selectionRows, sessionData] = await Promise.all([
          api.getProfileSuggestions(userId),
          api.getProfileSelections(userId),
          api.getUserSessions(userId),
        ]);
        if (cancelled) return;
        setAllProfiles(suggestionData.all_profiles);
        setSelections(selectionRows);
        setSessions(sessionData.sessions);
        setPhase("ready");
      } catch (err) {
        if (!cancelled) {
          setError(err);
          setPhase("error");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [userId, retryKey]);

  const summaryEntries = summarizeProfile(profile);
  const hasProfile = hasCustomizedDimensions(profile);
  const selectionByKey = Object.fromEntries(selections.map((row) => [row.profile_key, row.status]));
  const selectedProfiles = allProfiles.filter((p) =>
    ["accepted", "manually_added"].includes(selectionByKey[p.profile_key])
  );
  const sessionExpired = error?.status === 401 || error?.status === 403;
  const completedSessionCount = sessions.filter((s) => s.status === "completed").length;

  return (
    <div className="profile-flow dashboard">
      <div className="dashboard__topbar">
        <div>
          <h1 className="dashboard__welcome">Welcome back, {user?.display_name || user?.username}</h1>
          <p className="profile-flow__subtitle dashboard__subtitle">
            Here's how AbilityOS currently understands you.
          </p>
        </div>
        <div className="row dashboard__topbar-actions">
          <button type="button" className="btn btn--ghost" onClick={onHome}>
            Home
          </button>
          <button type="button" className="btn btn--ghost" onClick={onLogout}>
            Log out
          </button>
        </div>
      </div>

      <div className="card">
        <h2>Your Ability Profile</h2>
        {hasProfile ? (
          <ul className="profile-summary__list dashboard__profile-list">
            {summaryEntries.map((entry) => (
              <li key={entry.text}>
                <span aria-hidden="true">{entry.emoji}</span> {entry.text}
              </li>
            ))}
          </ul>
        ) : (
          <p>
            You haven't set up your Ability Profile yet — AbilityOS doesn't have any specific adaptations to apply
            for you yet.
          </p>
        )}
        <div className="row profile-flow__actions dashboard__actions">
          <button type="button" className="btn btn--ghost" onClick={hasProfile ? onEditProfile : onSetupProfile}>
            {hasProfile ? "Edit Ability Profile" : "Set up your Ability Profile"}
          </button>
        </div>
      </div>

      <div className="card">
        <h2>Selected Profiles</h2>
        {phase === "loading" && <p>Loading your selected profiles…</p>}
        {phase === "error" && (
          <div role="alert">
            <p className="suggested-profiles__error">
              {sessionExpired ? "Your session has expired." : "Unable to load your selected profiles."}
            </p>
            {!sessionExpired && <p className="suggested-profiles__error">{error?.message}</p>}
            {sessionExpired ? (
              <button type="button" className="btn btn--ghost" onClick={onLogout}>
                Log in again
              </button>
            ) : (
              <button type="button" className="btn btn--ghost" onClick={() => setRetryKey((n) => n + 1)}>
                Retry
              </button>
            )}
          </div>
        )}
        {phase === "ready" && (
          <>
            {selectedProfiles.length === 0 ? (
              <p>You haven't selected any profiles yet.</p>
            ) : (
              <div className="user-select__grid dashboard__profiles-grid">
                {selectedProfiles.map((p) => (
                  <div key={p.profile_key} className="card user-select__card dashboard__profile-card">
                    <h3>{p.name}</h3>
                    <p>{p.description}</p>
                  </div>
                ))}
              </div>
            )}
            <div className="row profile-flow__actions dashboard__actions">
              <button type="button" className="btn btn--ghost" onClick={onManageProfiles}>
                Manage Profiles
              </button>
            </div>
          </>
        )}
      </div>

      <div className="card">
        <h2>Recent Activity</h2>
        {phase === "loading" && <p>Loading your recent activity…</p>}
        {phase === "ready" && (
          <>
            {sessions.length === 0 ? (
              <p>No AbilityOS sessions yet.</p>
            ) : (
              <p>
                {completedSessionCount} completed session{completedSessionCount === 1 ? "" : "s"} out of{" "}
                {sessions.length} total.
              </p>
            )}
            <div className="row profile-flow__actions dashboard__actions">
              <button type="button" className="btn btn--ghost" onClick={onViewHistory}>
                View Interaction History
              </button>
            </div>
          </>
        )}
      </div>

      <div className="card dashboard__start-card">
        {consentGranted ? (
          <>
            <h2>Ready to see it in action?</h2>
            <p>
              Start an experience and AbilityOS will identify the barriers this profile creates for a task, and the
              smallest useful adaptation that removes them — using your Ability Profile.
            </p>
            <div className="row dashboard__start-actions">
              <button type="button" className="btn btn--primary dashboard__start-btn" onClick={onStartExperience}>
                Start Experience
              </button>
              {/* Phase 7 (Advanced Adaptive Intelligence & What-If
                  Simulation) section 13: the dashboard's required entry
                  point into the simulation experience -- gated on consent
                  the same as Start Experience, since What-If runs the same
                  engine against this profile (see docs/PHASE_7.md). */}
              <button type="button" className="btn btn--ghost" onClick={onExploreWhatIf}>
                Explore What-If
              </button>
            </div>
          </>
        ) : (
          <>
            <h2>Ready to see it in action?</h2>
            <p>
              AbilityOS needs your consent before it can use your Ability Profile to adapt anything for you.
            </p>
            <button type="button" className="btn btn--primary dashboard__start-btn" onClick={onGrantConsent}>
              Grant Consent
            </button>
          </>
        )}
      </div>
    </div>
  );
}
