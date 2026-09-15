import { useState } from "react";
import AnalyticsPage from "./pages/AnalyticsPage";
import DemoPage from "./pages/DemoPage";
import LandingPage from "./pages/LandingPage";
import SelectUserPage from "./pages/SelectUserPage";
import ConsentPage from "./pages/ConsentPage";
import AbilityProfileEditorPage from "./pages/AbilityProfileEditorPage";
import ProfileSummaryPage from "./pages/ProfileSummaryPage";
import TaskEnvironmentPage from "./pages/TaskEnvironmentPage";
import Header from "./components/Header";
import { useProfileFlow } from "./hooks/useProfileFlow";

/**
 * Journey (Phase 2 section 19, extended by Phase 3/6 section 10/19):
 *   Landing -> Select Demo User -> Consent -> Ability Profile -> Profile
 *   Summary -> Task & Environment (analyze, detect barriers, recommend an
 *   adaptation) -> "Open Adaptive Kiosk" -> the real, working adaptive
 *   kiosk (DemoPage/KioskView) -> complete task.
 *
 * "Open Adaptive Kiosk" (Phase 6) is the hand-off: it navigates into
 * DemoPage, which re-runs the same deterministic pipeline against the
 * session-based backend and renders whatever it approves — the frontend
 * never carries the standalone screen's decision over directly, so there
 * is no path where a client-side value reaches the kiosk without passing
 * through backend safety validation again. The header's "Kiosk Demo" nav
 * reaches the same page directly, unchanged since Phase 2.
 */
export default function App() {
  const [entered, setEntered] = useState(false);
  const [stage, setStage] = useState("select-user");
  const [taskView, setTaskView] = useState("demo");
  const [resetSignal, setResetSignal] = useState(0);

  const flow = useProfileFlow();

  const handleExplore = () => {
    setEntered(true);
    setStage("select-user");
  };

  const handleGoHome = () => {
    setEntered(false);
    flow.reset();
  };

  const handleReset = () => {
    flow.reset();
    setStage("select-user");
    setTaskView("demo");
    setResetSignal((n) => n + 1);
  };

  const handleSelectUser = async (userId) => {
    await flow.selectUser(userId);
    setStage("consent");
  };

  const handleAgreeConsent = async () => {
    await flow.agreeToConsent();
    setStage("profile");
  };

  const handleSaveProfile = async (dimensions, modality) => {
    await flow.saveProfile(dimensions, modality);
    setStage("summary");
  };

  const handleContinueToTaskEnvironment = () => {
    setStage("task-environment");
  };

  // Phase 6: hands off from the standalone Task/Environment/Barrier/
  // Adaptation-decision screens into the real, working adaptive kiosk
  // (DemoPage/KioskView) — same session-based backend pipeline, same
  // deterministic scoring, so it re-derives the identical decision rather
  // than trusting anything computed client-side.
  const handleOpenKiosk = () => {
    setTaskView("demo");
    setStage("task");
  };

  const handleHeaderNavigate = (view) => {
    setTaskView(view);
    if (view === "analytics") {
      setStage("analytics");
    } else if (flow.userId && flow.consent?.granted) {
      setStage("task");
    } else {
      setStage("select-user");
    }
  };

  if (!entered) {
    return (
      <div className="app-shell">
        <LandingPage onExplore={handleExplore} />
      </div>
    );
  }

  const showChrome = stage === "task" || stage === "analytics" || stage === "task-environment";

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      {showChrome && (
        <Header view={taskView} onNavigate={handleHeaderNavigate} onReset={handleReset} onHome={handleGoHome} />
      )}
      <main id="main-content">
        {stage === "select-user" && <SelectUserPage onSelect={handleSelectUser} />}

        {stage === "consent" && (
          <ConsentPage alreadyGranted={flow.consent?.granted} onAgree={handleAgreeConsent} busy={flow.loading} />
        )}

        {stage === "profile" && (
          <AbilityProfileEditorPage
            profile={flow.profile}
            onSave={handleSaveProfile}
            busy={flow.loading}
            error={flow.error}
          />
        )}

        {stage === "summary" && (
          <ProfileSummaryPage
            profile={flow.profile}
            consent={flow.consent}
            onContinue={handleContinueToTaskEnvironment}
            onEditAgain={() => setStage("profile")}
            onClearProfile={flow.clearProfile}
            busy={flow.loading}
          />
        )}

        {stage === "task-environment" && (
          <TaskEnvironmentPage
            userId={flow.userId}
            profileLabel={flow.profile?.label}
            onBackToSummary={() => setStage("summary")}
            onOpenKiosk={handleOpenKiosk}
          />
        )}

        {stage === "task" && <DemoPage userId={flow.userId} resetSignal={resetSignal} />}
        {stage === "analytics" && <AnalyticsPage key={resetSignal} />}
      </main>
    </div>
  );
}
