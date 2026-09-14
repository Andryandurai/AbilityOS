/**
 * Part 7/26 safety gate: a high-risk adaptation (e.g. switching the whole
 * input modality to voice) is approved by the rule engine but still needs
 * an explicit human confirmation before it is ever applied — the LLM
 * proposes, the rule engine disposes, and the presenter has final say.
 */
export default function ConfirmDialog({ pending, onConfirm, onSkip }) {
  if (!pending.length) return null;

  return (
    <div className="card" role="alertdialog" aria-labelledby="confirm-title" style={{ borderColor: "var(--color-warning)" }}>
      <h2 id="confirm-title">Confirmation required</h2>
      <p>
        The rule engine approved the following higher-risk adaptation(s), but they change the
        interaction significantly enough to need explicit confirmation before being applied:
      </p>
      <ul>
        {pending.map((r) => (
          <li key={r.id}>
            <strong>{r.adaptation.display_name}</strong> — {r.adaptation.description}
          </li>
        ))}
      </ul>
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn btn--ghost" onClick={onSkip}>
          Skip these, apply the rest
        </button>
        <button className="btn btn--primary" onClick={() => onConfirm(pending.map((r) => r.id))}>
          Confirm and apply
        </button>
      </div>
    </div>
  );
}
