export default function Header({ view, onNavigate, onReset }) {
  return (
    <header className="app-header">
      <div className="app-header__brand">
        <strong>AbilityOS</strong>
        <span className="app-header__tagline">An Operating System for Human Abilities</span>
      </div>
      <nav className="app-header__nav" aria-label="Primary">
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
