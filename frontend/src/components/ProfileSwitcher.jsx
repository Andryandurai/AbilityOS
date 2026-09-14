const DIMENSION_LABELS = {
  vision: "Vision",
  hearing: "Hearing",
  dexterity: "Dexterity",
  cognition: "Cognition",
  fatigue: "Fatigue",
};

function summarizeProfile(profile) {
  if (!profile) return [];
  return Object.entries(profile.dimensions || {})
    .filter(([, v]) => v.level !== "typical")
    .map(([key, v]) => `${DIMENSION_LABELS[key] || key}: ${v.level}`);
}

/**
 * Lets the presenter switch which Ability Profile is "in the chair" (Part
 * 13/16). Switching profiles and re-running the same task is the single
 * most important demo beat — it proves AbilityOS is one engine, not one
 * feature (Part 16 step 9).
 */
export default function ProfileSwitcher({ users, profiles, activeUserId, onSelect, disabled }) {
  return (
    <div className="card">
      <h2>1. Ability Profile</h2>
      <p className="visually-hidden" id="profile-switcher-help">
        Select which demo persona is currently using the kiosk.
      </p>
      <div className="row" role="radiogroup" aria-describedby="profile-switcher-help">
        {users.map((user) => {
          const profile = profiles[user.id];
          const active = user.id === activeUserId;
          return (
            <button
              key={user.id}
              type="button"
              role="radio"
              aria-checked={active}
              disabled={disabled}
              onClick={() => onSelect(user.id)}
              className="btn"
              style={{
                flex: "1 1 220px",
                textAlign: "left",
                background: active ? "var(--color-primary)" : "var(--color-surface)",
                color: active ? "#fff" : "var(--color-text)",
                border: `2px solid ${active ? "var(--color-primary)" : "var(--color-border)"}`,
              }}
            >
              <div style={{ fontWeight: 700 }}>{user.display_name}</div>
              <div style={{ fontSize: "0.85rem", opacity: 0.85, marginTop: 4 }}>
                {summarizeProfile(profile).join(" · ") || "typical profile"}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
