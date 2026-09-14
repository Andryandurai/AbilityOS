import { useEffect, useState } from "react";
import * as api from "../services/api";

/**
 * Simple analytics dashboard (Part 22) — total interactions, completion,
 * adaptation usage and profile distribution, all from GET
 * /api/analytics/dashboard/.
 */
export default function AnalyticsPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getDashboard().then(setData).catch((err) => setError(err.message));
  }, []);

  if (error) return <div className="card">Could not load analytics: {error}</div>;
  if (!data) return <div className="card">Loading analytics…</div>;

  return (
    <div className="stack">
      <div className="card">
        <h2>AbilityOS Analytics</h2>
        <p className="dev-panel__ai-note">{data.note}</p>
        <div className="row" style={{ gap: "var(--space-6)" }}>
          <Stat label="Total interactions" value={data.total_interactions} />
          <Stat label="Completed tasks" value={data.completed_tasks} />
          <Stat
            label="Overall completion rate"
            value={data.overall.completion_rate != null ? `${Math.round(data.overall.completion_rate * 100)}%` : "—"}
          />
          <Stat label="Avg. errors" value={data.overall.avg_errors ?? "—"} />
          <Stat label="Avg. time (s)" value={data.overall.avg_time_seconds ?? "—"} />
        </div>
      </div>

      <div className="card">
        <h3>Adaptations applied</h3>
        {data.adaptations_used.length === 0 ? (
          <p>No adaptations have been applied yet — run the kiosk demo first.</p>
        ) : (
          <ul>
            {data.adaptations_used.map((a) => (
              <li key={a.adaptation__name}>
                {a.adaptation__display_name} — used {a.times_used} time(s)
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card">
        <h3>Sessions by Ability Profile</h3>
        <ul>
          {data.profile_distribution.map((p) => (
            <li key={p.user__ability_profile__label || "unlabeled"}>
              {p.user__ability_profile__label || "(no profile)"} — {p.count} session(s)
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div>
      <div style={{ fontSize: "1.6rem", fontWeight: 800, color: "var(--color-primary)" }}>{value}</div>
      <div style={{ color: "var(--color-text-muted)", fontSize: "0.85rem" }}>{label}</div>
    </div>
  );
}
