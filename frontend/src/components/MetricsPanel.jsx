function MetricRow({ label, before, after, format = (v) => v, betterIsLower = true }) {
  const improved = before != null && after != null && (betterIsLower ? after < before : after > before);
  return (
    <tr>
      <th scope="row">{label}</th>
      <td>{before == null ? "—" : format(before)}</td>
      <td className={improved ? "metrics-panel__improved" : ""}>{after == null ? "—" : format(after)}</td>
    </tr>
  );
}

/**
 * Before/after evaluation table (Part 18/21). Every number here comes from
 * GET /api/analytics/before-after/, which aggregates real InteractionSession
 * + Feedback rows (seed + live) — never hardcoded, and always labelled.
 */
export default function MetricsPanel({ data, loading }) {
  if (loading) return <div className="card">Loading metrics…</div>;
  if (!data) return null;

  const { without_abilityos: before, with_abilityos: after, note } = data;

  // Phase 7 section 15/39: "not enough sessions yet" is a distinct state
  // from "measured zero" — never render an empty bucket as if 0% were a
  // real completion rate.
  if (before.sessions === 0 && after.sessions === 0) {
    return (
      <div className="card">
        <h2>Before / After AbilityOS</h2>
        <p>Not enough sessions yet.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h2>Before / After AbilityOS</h2>
      <p className="dev-panel__ai-note">{note}</p>
      <table className="metrics-panel__table">
        <thead>
          <tr>
            <th scope="col">Metric</th>
            <th scope="col">Without AbilityOS ({before.sessions} sessions)</th>
            <th scope="col">With AbilityOS ({after.sessions} sessions)</th>
          </tr>
        </thead>
        <tbody>
          <MetricRow
            label="Completion rate"
            before={before.completion_rate}
            after={after.completion_rate}
            format={(v) => `${Math.round(v * 100)}%`}
            betterIsLower={false}
          />
          <MetricRow label="Avg. time (seconds)" before={before.avg_time_seconds} after={after.avg_time_seconds} />
          <MetricRow label="Avg. errors" before={before.avg_errors} after={after.avg_errors} />
          <MetricRow
            label="Assistance requested"
            before={before.assistance_rate}
            after={after.assistance_rate}
            format={(v) => `${Math.round(v * 100)}%`}
          />
          <MetricRow
            label="Avg. ease (1-5)"
            before={before.avg_ease}
            after={after.avg_ease}
            betterIsLower={false}
          />
        </tbody>
      </table>
    </div>
  );
}
