// Phase 6/7: `onGoToDashboard`/`onViewHistory`/`onExploreWhatIf` are all
// optional -- passed only for the authenticated ("account") entry path
// (see App.jsx), never for the demo flow. Omitting them (as every
// existing demo-mode caller still does) renders this exact same nav as
// before Phase 6, unchanged.
export default function Header({
  view,
  onNavigate,
  onReset,
  onHome,
  onGoToDashboard,
  onViewHistory,
  onExploreWhatIf,
}) {
  return (
    <header className="app-header">
      <button type="button" className="app-header__brand app-header__brand--button" onClick={onHome}>
        <strong>AbilityOS</strong>
        <span className="app-header__tagline">An Operating System for Human Abilities</span>
      </button>
      <nav className="app-header__nav" aria-label="Primary">
        {onGoToDashboard && (
          <button className="btn btn--ghost" onClick={onGoToDashboard}>
            Dashboard
          </button>
        )}
        {onViewHistory && (
          <button className="btn btn--ghost" onClick={onViewHistory}>
            History
          </button>
        )}
        {onExploreWhatIf && (
          <button className="btn btn--ghost" onClick={onExploreWhatIf}>
            What-If
          </button>
        )}
        <button
          className={`btn ${view === "demo" ? "btn--primary" : "btn--ghost"}`}
          aria-current={view === "demo" ? "page" : undefined}
          onClick={() => onNavigate("demo")}
        >
          Kiosk Demo
        </button>
        <button
          className={`btn ${view === "analytics" ? "btn--primary" : "btn--ghost"}`}
          aria-current={view === "analytics" ? "page" : undefined}
          onClick={() => onNavigate("analytics")}
        >
          Analytics
        </button>
        <button className="btn btn--ghost" onClick={onReset}>
          Reset Demo
        </button>
      </nav>
    </header>
  );
}
