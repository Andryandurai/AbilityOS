import { useState } from "react";
import AnalyticsPage from "./pages/AnalyticsPage";
import DemoPage from "./pages/DemoPage";
import Header from "./components/Header";

export default function App() {
  const [view, setView] = useState("demo");
  const [resetSignal, setResetSignal] = useState(0);

  const handleReset = () => {
    setResetSignal((n) => n + 1);
    setView("demo");
  };

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <Header view={view} onNavigate={setView} onReset={handleReset} />
      <main id="main-content">
        {view === "demo" ? <DemoPage resetSignal={resetSignal} /> : <AnalyticsPage key={resetSignal} />}
      </main>
    </div>
  );
}
