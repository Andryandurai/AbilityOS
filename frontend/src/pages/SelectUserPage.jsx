import { useEffect, useState } from "react";
import JourneyIndicator from "../components/JourneyIndicator";
import * as api from "../services/api";
import { summarizeProfileAsBullets } from "../constants/abilityProfile";
import "./ProfileFlow.css";

/**
 * "Who are we adapting technology for?" (Phase 2 section 10). The frontend
 * never hardcodes what a persona needs — each card's bullet list is
 * derived from the real profile fetched from the backend.
 */
export default function SelectUserPage({ onSelect }) {
  const [users, setUsers] = useState([]);
  const [profiles, setProfiles] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const demoUsers = await api.listDemoUsers();
        const profileEntries = await Promise.all(
          demoUsers.map((u) => api.getAbilityProfile(u.id).then((p) => [u.id, p]))
        );
        if (cancelled) return;
        setUsers(demoUsers);
        setProfiles(Object.fromEntries(profileEntries));
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="profile-flow">
      <JourneyIndicator currentStep="select-user" />
      <div className="card profile-flow__intro">
        <h1>Who are we adapting technology for?</h1>
        <p>Choose a demo profile to see AbilityOS adapt the same task differently for each person.</p>
      </div>

      {loading && <div className="card">Loading demo profiles…</div>}
      {error && (
        <div className="card" role="alert">
          <p>Unable to load demo profiles. Please try again.</p>
          <p className="dev-panel__ai-note">{error}</p>
        </div>
      )}

      {!loading && !error && (
        <div className="user-select__grid">
          {users.map((user) => {
            const profile = profiles[user.id];
            const needs = summarizeProfileAsBullets(profile);
            return (
              <div key={user.id} className="card user-select__card">
                <h2>{profile?.label || user.display_name}</h2>
                {needs.length > 0 ? (
                  <>
                    <p className="user-select__needs-label">AbilityOS understands:</p>
                    <ul className="user-select__needs">
                      {needs.map((text) => (
                        <li key={text}>{text}</li>
                      ))}
                    </ul>
                  </>
                ) : (
                  <p className="user-select__needs-label">No specific needs — typical profile.</p>
                )}
                <button className="btn btn--primary" onClick={() => onSelect(user.id)}>
                  Select
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
