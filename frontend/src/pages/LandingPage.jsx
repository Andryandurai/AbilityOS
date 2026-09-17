import { useEffect, useState } from "react";
import * as api from "../services/api";
import "./LandingPage.css";

/**
 * Phase 1 landing page. Deliberately simple — this is the project's front
 * door, not the demo itself (that starts once "Explore AbilityOS" is
 * clicked). It doubles as the visible proof that the full chain
 * (React -> Django -> Database) actually works: the status line below the
 * button is a live result of GET /api/health/, not a decorative claim.
 */
export default function LandingPage({ onExplore, onLogin, onRegister, authenticatedUser, onLogout, onGoToDashboard }) {
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState(null);

  useEffect(() => {
    api
      .getHealth()
      .then(setHealth)
      .catch((err) => setHealthError(err.message));
  }, []);

  return (
    <div className="landing">
      <div className="landing__card">
        <h1 className="landing__title">ABILITYOS</h1>
        <p className="landing__tagline">
          "Technology that adapts to the person — not the other way around."
        </p>
        <p className="landing__blurb">
          AbilityOS is a software decision-making layer that sits between a person and
          the technology they use. It keeps a consented, functional Ability Profile,
          understands the task someone is trying to complete and the environment
          they're in, identifies the specific barrier standing in the way, and applies
          the smallest useful change that removes it — without changing what the task
          actually is.
        </p>

        <button className="btn btn--primary landing__cta" onClick={onExplore} autoFocus>
          Explore AbilityOS
        </button>

        {/* Phase 1 (Real User Authentication) section 19 — a second,
            independent entry path alongside the existing anonymous demo
            above. Neither path requires the other. */}
        <div className="row" style={{ justifyContent: "center", marginTop: "12px" }}>
          {authenticatedUser ? (
            <>
              <span>
                Welcome, <strong>{authenticatedUser.display_name || authenticatedUser.username}</strong>
              </span>
              {/* Phase 2 section 24 / Phase 4 section 12: the authenticated
                  counterpart to "Explore AbilityOS" above -- opens this
                  account's personalized Dashboard instead of picking a demo
                  persona. First-time setup (Consent -> Questionnaire ->
                  Profile Summary) is reached from there. */}
              <button type="button" className="btn btn--primary" onClick={onGoToDashboard}>
                Go to my Dashboard
              </button>
              <button type="button" className="btn btn--ghost" onClick={onLogout}>
                Log out
              </button>
            </>
          ) : (
            <>
              <button type="button" className="btn btn--ghost" onClick={onLogin}>
                Log in
              </button>
              <button type="button" className="btn btn--ghost" onClick={onRegister}>
                Create an account
              </button>
            </>
          )}
        </div>

        <div className="landing__status" role="status" aria-live="polite">
          {health && (
            <>
              <span className="landing__status-dot landing__status-dot--ok" aria-hidden="true" />
              Backend connected — {health.database.engine} database reachable
              {health.database.seeded_user_count != null &&
                ` (${health.database.seeded_user_count} users seeded)`}
              . AI Decision Engine:{" "}
              {health.ai_decision_engine.configured
                ? `live (${health.ai_decision_engine.provider})`
                : "deterministic fallback (no provider configured)"}
              .
            </>
          )}
          {healthError && (
            <>
              <span className="landing__status-dot landing__status-dot--error" aria-hidden="true" />
              Could not reach the backend: {healthError}
            </>
          )}
          {!health && !healthError && (
            <>
              <span className="landing__status-dot landing__status-dot--pending" aria-hidden="true" />
              Checking backend connection…
            </>
          )}
        </div>
      </div>
    </div>
  );
}
