import { useEffect, useState } from "react";
import * as api from "../services/api";
import "./AnalyticsPage.css";

/**
 * AbilityOS Outcome Analytics (Phase 7 section 16/40) — accessibility
 * outcomes only, not a generic business dashboard. Every number here comes
 * from real InteractionSession/InteractionEvent/Feedback rows (seed +
 * live), via GET /api/analytics/{dashboard,before-after,adaptations,
 * barriers,sessions}/ — never hardcoded (Phase 7 section 34/38).
 */

const OUTCOME_LABELS = {
  positive_observed_outcome: { text: "✓ Positive observed outcome", pill: "pill--low" },
  negative_observed_outcome: { text: "✗ Negative observed outcome", pill: "pill--high" },
  inconclusive: { text: "△ Inconclusive", pill: "pill--medium" },
  insufficient_data: { text: "— Insufficient data yet", pill: "pill--neutral" },
};

function Stat({ label, value }) {
  return (
    <div>
      <div style={{ fontSize: "1.6rem", fontWeight: 800, color: "var(--color-primary)" }}>{value}</div>
      <div style={{ color: "var(--color-text-muted)", fontSize: "0.85rem" }}>{label}</div>
    </div>
  );
}

function OutcomeBadge({ state }) {
  const info = OUTCOME_LABELS[state] || { text: state, pill: "pill--neutral" };
  return <span className={`pill ${info.pill}`}>{info.text}</span>;
}

// A text-labeled bar meter — the percentage is always printed alongside
// the bar, so meaning never depends on color or bar length alone (Phase 7
// section 41: "no color-only meaning", "text alternatives for visual
// metrics").
function BarMeter({ label, value, formatted }) {
  const pct = value == null ? 0 : Math.round(value * 100);
  return (
    <div className="analytics-bar">
      <div className="analytics-bar__label">
        <span>{label}</span>
        <span>{value == null ? "Not enough sessions yet" : formatted}</span>
      </div>
      <div className="analytics-bar__track" role="img" aria-label={`${label}: ${value == null ? "not enough sessions yet" : formatted}`}>
        <div className="analytics-bar__fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function ComparisonRow({ label, standard, adaptive, format }) {
  return (
    <div className="analytics-comparison__row">
      <BarMeter label={`${label} — Standard`} value={standard} formatted={format(standard)} />
      <BarMeter label={`${label} — Adaptive`} value={adaptive} formatted={format(adaptive)} />
    </div>
  );
}

export default function AnalyticsPage() {
  const [dashboard, setDashboard] = useState(null);
  const [beforeAfter, setBeforeAfter] = useState(null);
  const [adaptations, setAdaptations] = useState(null);
  const [barriers, setBarriers] = useState(null);
  const [recentSessions, setRecentSessions] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([
      api.getDashboard(),
      api.getBeforeAfter(),
      api.getAdaptationEffectiveness(),
      api.getBarrierOutcomes(),
      api.getRecentSessions(10),
    ])
      .then(([d, ba, ad, br, rs]) => {
        setDashboard(d);
        setBeforeAfter(ba);
        setAdaptations(ad);
        setBarriers(br);
        setRecentSessions(rs);
      })
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <div className="card">Could not load analytics: {error}</div>;
  if (!dashboard) return <div className="card">Loading analytics…</div>;

  // Phase 7 section 39: "no data" is a distinct state from "measured
  // zero" — never render 0%/0/0 as if it were a real measurement.
  if (dashboard.empty) {
    return (
      <div className="card">
        <h1>AbilityOS Outcome Analytics</h1>
        <p>No interaction data yet.</p>
        <p className="dev-panel__ai-note">
          Complete an AbilityOS task to begin measuring accessibility outcomes.
        </p>
      </div>
    );
  }

  return (
    <div className="stack">
      <div className="card">
        <h1>AbilityOS Outcome Analytics</h1>
        <p className="dev-panel__ai-note">{dashboard.note}</p>
        <div className="row" style={{ gap: "var(--space-6)", flexWrap: "wrap" }}>
          <Stat label="Total sessions" value={dashboard.total_interactions} />
          <Stat label="Completed" value={dashboard.completed_tasks} />
          <Stat label="Abandoned" value={dashboard.abandoned_tasks} />
          <Stat
            label="Completion rate"
            value={dashboard.overall.completion_rate != null ? `${Math.round(dashboard.overall.completion_rate * 100)}%` : "—"}
          />
          <Stat
            label="Assistance rate"
            value={dashboard.overall.assistance_rate != null ? `${Math.round(dashboard.overall.assistance_rate * 100)}%` : "—"}
          />
          <Stat label="Avg. ease" value={dashboard.overall.avg_ease != null ? `${dashboard.overall.avg_ease}/5` : "—"} />
        </div>
      </div>

      {beforeAfter && (
        <div className="card">
          <h2>Standard vs. Adaptive</h2>
          <p className="dev-panel__ai-note">
            Same task and environment, compared with AbilityOS's adaptation switched off ("standard") vs. on
            ("adaptive"). {beforeAfter.without_abilityos.sessions === 0 || beforeAfter.with_abilityos.sessions === 0
              ? "Not enough sessions yet for a full comparison."
              : null}
          </p>
          <div className="analytics-comparison">
            <ComparisonRow
              label="Completion"
              standard={beforeAfter.without_abilityos.completion_rate}
              adaptive={beforeAfter.with_abilityos.completion_rate}
              format={(v) => (v == null ? "—" : `${Math.round(v * 100)}%`)}
            />
            <ComparisonRow
              label="Assistance requested"
              standard={beforeAfter.without_abilityos.assistance_rate}
              adaptive={beforeAfter.with_abilityos.assistance_rate}
              format={(v) => (v == null ? "—" : `${Math.round(v * 100)}%`)}
            />
          </div>
          <dl className="analytics-comparison__extra">
            <div>
              <dt>Avg. errors (standard / adaptive)</dt>
              <dd>
                {beforeAfter.without_abilityos.avg_errors ?? "—"} / {beforeAfter.with_abilityos.avg_errors ?? "—"}
              </dd>
            </div>
            <div>
              <dt>Avg. time in seconds (standard / adaptive)</dt>
              <dd>
                {beforeAfter.without_abilityos.avg_time_seconds ?? "—"} / {beforeAfter.with_abilityos.avg_time_seconds ?? "—"}
              </dd>
            </div>
          </dl>
        </div>
      )}

      <div className="card">
        <h2>Adaptation effectiveness</h2>
        {adaptations.empty ? (
          <p>No adaptations have been applied yet — run the kiosk demo first.</p>
        ) : (
          <ul className="analytics-effectiveness-list">
            {adaptations.adaptations.map((a) => (
              <li key={a.adaptation_id} className="analytics-effectiveness-item">
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <strong>{a.display_name}</strong>
                  <OutcomeBadge state={a.observed_outcome} />
                </div>
                <p className="dev-panel__evidence">
                  Evidence: {a.sessions} adaptive session{a.sessions === 1 ? "" : "s"}
                  {a.completion_rate != null && ` · completion ${Math.round(a.completion_rate * 100)}%`}
                  {a.avg_ease != null && ` · avg. ease ${a.avg_ease}/5`}
                  {a.assistance_rate != null && ` · assistance ${Math.round(a.assistance_rate * 100)}%`}
                  {a.confidence != null && ` · confidence ${a.confidence}`}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card">
        <h2>Barrier outcomes</h2>
        {barriers.empty ? (
          <p>No barriers have been detected yet.</p>
        ) : (
          <ul className="analytics-effectiveness-list">
            {barriers.barriers.map((b) => (
              <li key={b.barrier_type} className="analytics-effectiveness-item">
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <strong>{b.barrier_type.replaceAll("_", " ")}</strong>
                  <OutcomeBadge state={b.observed_outcome} />
                </div>
                <p className="dev-panel__evidence">
                  Detected {b.frequency} time{b.frequency === 1 ? "" : "s"}
                  {b.associated_adaptations.length > 0 &&
                    ` · addressed by ${b.associated_adaptations.map((x) => x.adaptation__display_name).join(", ")}`}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card">
        <h2>Recent sessions</h2>
        {recentSessions.empty ? (
          <p>No sessions yet.</p>
        ) : (
          <table className="metrics-panel__table">
            <thead>
              <tr>
                <th scope="col">Task</th>
                <th scope="col">Mode</th>
                <th scope="col">Result</th>
                <th scope="col">Ease</th>
                <th scope="col">Assistance</th>
              </tr>
            </thead>
            <tbody>
              {recentSessions.sessions.map((s) => (
                <tr key={s.session_id}>
                  <td>
                    {s.task_name}
                    {s.is_seed && <span className="pill pill--neutral"> demo data</span>}
                  </td>
                  <td>{s.experience_mode}</td>
                  <td>{s.status}</td>
                  <td>{s.ease_rating ? `${s.ease_rating}/5` : "—"}</td>
                  <td>{s.assistance_requested == null ? "—" : s.assistance_requested ? "Yes" : "No"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <h2>Adaptations applied</h2>
        {dashboard.adaptations_used.length === 0 ? (
          <p>No adaptations have been applied yet — run the kiosk demo first.</p>
        ) : (
          <ul>
            {dashboard.adaptations_used.map((a) => (
              <li key={a.adaptation__name}>
                {a.adaptation__display_name} — used {a.times_used} time(s)
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card">
        <h2>Sessions by Ability Profile</h2>
        <ul>
          {dashboard.profile_distribution.map((p) => (
            <li key={p.user__ability_profile__label || "unlabeled"}>
              {p.user__ability_profile__label || "(no profile)"} — {p.count} session(s)
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
