import { useEffect, useState } from "react";
import AnalyticsPage from "./pages/AnalyticsPage";
import DashboardPage from "./pages/DashboardPage";
import DemoPage from "./pages/DemoPage";
import HistoryPage from "./pages/HistoryPage";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import QuestionnairePage from "./pages/QuestionnairePage";
import SuggestedProfilesPage from "./pages/SuggestedProfilesPage";
import SelectUserPage from "./pages/SelectUserPage";
import ConsentPage from "./pages/ConsentPage";
import AbilityProfileEditorPage from "./pages/AbilityProfileEditorPage";
import ProfileSummaryPage from "./pages/ProfileSummaryPage";
import TaskEnvironmentPage from "./pages/TaskEnvironmentPage";
import WhatIfPage from "./pages/WhatIfPage";
import Header from "./components/Header";
import { hasCustomizedDimensions } from "./constants/abilityProfile";
import { useProfileFlow } from "./hooks/useProfileFlow";
import { useAuth } from "./hooks/useAuth";

/**
 * Journey (Phase 2 section 19, extended by Phase 3/4/6):
 *   Demo path: Landing -> Select Demo User -> Consent -> Ability Profile ->
 *   Profile Summary -> Task & Environment (analyze, detect barriers,
 *   recommend an adaptation) -> "Open Adaptive Kiosk" -> the real, working
 *   adaptive kiosk (DemoPage/KioskView) -> complete task.
 *
 *   Account path: Landing -> Dashboard (the account's home screen) ->
 *   first visit only: "Set up your Ability Profile" -> Consent ->
 *   Questionnaire -> Profile Summary -> Suggested Profiles -> back to
 *   Dashboard, which shows the profile summary, selected profiles, and a
 *   "Start Experience" entry point into the same Task & Environment ->
 *   Kiosk flow as the demo path.
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
  // Phase 1 (Real User Authentication) section 19: a second, independent
  // "screen" shown from the landing page, alongside (not instead of) the
  // existing demo flow below. null means "show the landing page as-is".
  const [authView, setAuthView] = useState(null); // null | "login" | "register"
  // Phase 2 (Onboarding, Consent & Questionnaire) section 24: which of the
  // two ways into the *same* `entered` flow below produced this session --
  // a demo persona picked from SelectUserPage, or a real logged-in
  // account skipping straight to Welcome. Consent's "what happens next"
  // (section 19's diagram) is the only place this actually branches.
  const [entryMode, setEntryMode] = useState("demo"); // "demo" | "account"
  // Phase 4 (Personalized Dashboard) section 15: SuggestedProfilesPage is
  // now reachable from two places -- straight after the Profile Summary
  // (first-time setup) and from the Dashboard's "Manage Profiles" link
  // (any time after). "Back" needs to return wherever it was opened from.
  const [suggestedProfilesOrigin, setSuggestedProfilesOrigin] = useState("summary"); // "summary" | "dashboard"

  const flow = useProfileFlow();
  const auth = useAuth();

  // Phase 4 section 16: defense in depth for the Dashboard's authentication
  // guard. Nothing in the UI can normally reach stage "dashboard" while
  // logged out (it's only ever set from an authenticated branch, and the
  // Dashboard's own "Log out" button already returns here synchronously --
  // see handleLogout below), but if the session ever ends while already on
  // it some other way -- a token that stops being valid mid-visit -- this
  // bounces back to the landing page rather than leaving a personalized
  // page rendered with no user behind it.
  useEffect(() => {
    if (
      entered &&
      (stage === "dashboard" || stage === "history" || stage === "what-if") &&
      !auth.isLoading &&
      !auth.isAuthenticated
    ) {
      setEntered(false);
    }
  }, [entered, stage, auth.isLoading, auth.isAuthenticated]);

  const handleExplore = () => {
    // See useAuth.js's pauseAuthHeader() docstring: entering the existing
    // anonymous demo must behave identically whether or not the visitor
    // also happens to be logged in.
    auth.pauseAuthHeader();
    setEntryMode("demo");
    setEntered(true);
    setStage("select-user");
  };

  // Phase 2 section 24 / Phase 4 section 12: the authenticated counterpart
  // to handleExplore -- the user is already known (auth.user.id), so this
  // skips SelectUserPage entirely. It now lands on the Dashboard (the
  // account's home screen) rather than jumping straight into onboarding;
  // a user who hasn't set up an Ability Profile yet sees that as an empty
  // state there with its own explicit "Set up your Ability Profile" entry
  // point (handleSetupProfile below) instead of being forced into it.
  // Still reuses useProfileFlow exactly as the demo path does (selectUser
  // doesn't care whether the id belongs to a demo persona or a real
  // account) so Consent/the manual editor/the summary screen all keep
  // working unmodified for this path too.
  const handleGoToDashboard = async () => {
    auth.resumeAuthHeader();
    setEntryMode("account");
    await flow.selectUser(auth.user.id);
    setEntered(true);
    setStage("dashboard");
  };

  // Phase 4 section 12: Dashboard's "Set up" / "Edit" Ability Profile
  // actions. An empty/never-set-up profile still goes through the existing
  // Phase 2 front door (consent -> questionnaire); an already-set-up one
  // goes straight to the existing manual editor (stage "profile") to tweak
  // specific dimensions without repeating the whole questionnaire.
  const handleSetupProfile = () => setStage("welcome");
  const handleEditProfileFromDashboard = () => setStage("profile");

  const handleManageProfiles = () => {
    setSuggestedProfilesOrigin("dashboard");
    setStage("suggested-profiles");
  };

  const handleStartExperienceFromDashboard = () => setStage("task-environment");

  // Phase 5 section 13: the same ConsentPage every other path already uses
  // -- no second consent UI. Reached only when Dashboard's "Start
  // Experience" card finds `flow.consent?.granted` false (see the render
  // below), which the orchestrator itself would otherwise reject with a
  // 409 on session start.
  const handleGrantConsentFromDashboard = () => setStage("consent");

  // Phase 6 (Feedback + History + Analytics Integration) section 23/25:
  // Dashboard's "View Interaction History" and the Header's own shortcut
  // (added for entryMode === "account" only, see the Header render below)
  // both reach the same new "history" stage; "Back to Dashboard" returns
  // the same way every other Dashboard-adjacent screen does.
  const handleViewHistory = () => setStage("history");

  // Phase 7 (Advanced Adaptive Intelligence & What-If Simulation) section
  // 13/14/25: the dashboard's required "Explore What-If" entry point.
  // WhatIfPage itself calls the backend directly (request.user determines
  // the profile server-side); nothing here passes a profile or user id.
  const handleExploreWhatIf = () => setStage("what-if");

  const handleGoHome = () => {
    setEntered(false);
    flow.reset();
    auth.resumeAuthHeader();
  };

  const handleLogin = async (username, password) => {
    await auth.login(username, password);
    setAuthView(null);
  };

  const handleLogout = async () => {
    await auth.logout();
    // Phase 4 section 16: logging out from the Dashboard (unlike the demo
    // flow's Header, nothing else currently calls this while `entered`) must
    // return to the landing page immediately -- relying solely on the
    // authentication-guard effect above would leave a one-frame window where
    // `stage` is still "dashboard" but `auth.user` is already null.
    setEntered(false);
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
    // Phase 5 section 13: reachable a second time now, from Dashboard's
    // "Grant Consent" (handleGrantConsentFromDashboard) -- e.g. consent was
    // revoked after onboarding already produced a real profile. Sending
    // that case through the questionnaire again would be a pointless,
    // unwanted detour, so an already-customized profile returns straight
    // to the Dashboard instead. A never-onboarded account (the common
    // first-time case) still continues into the questionnaire exactly as
    // before -- this is a strict extension of Phase 2 section 24's
    // original demo-vs-account branch, not a change to it.
    if (entryMode === "account" && hasCustomizedDimensions(flow.profile)) {
      setStage("dashboard");
      return;
    }
    setStage(entryMode === "account" ? "questionnaire" : "profile");
  };

  // Phase 2: the questionnaire already wrote the confirmed answers to the
  // real AbilityProfile server-side (POST .../confirm/); this just
  // refreshes `flow`'s local copy from that same source of truth so the
  // existing ProfileSummaryPage renders the real, saved result -- not a
  // second, locally-guessed shape.
  const handleQuestionnaireComplete = async () => {
    await flow.selectUser(auth.user.id);
    setStage("summary");
  };

  const handleSaveProfile = async (dimensions, modality) => {
    await flow.saveProfile(dimensions, modality);
    setStage("summary");
  };

  const handleContinueToTaskEnvironment = () => {
    setStage("task-environment");
  };

  // Phase 3 (Profile Suggestions & User Profile Selection) section 22: the
  // only other branch point in the whole flow -- a real account continues
  // from the existing ProfileSummaryPage into the new Suggested Profiles
  // step; a demo persona's "Continue to Task & Environment" button keeps
  // its exact pre-Phase-3 behaviour.
  const handleProfileSummaryContinue = () => {
    if (entryMode === "account") {
      setSuggestedProfilesOrigin("summary");
      setStage("suggested-profiles");
    } else {
      handleContinueToTaskEnvironment();
    }
  };

  // Phase 4 section 12: first-time setup now ends at the Dashboard (the
  // account's home screen) rather than jumping straight into Task &
  // Environment -- "Start Experience" there (handleStartExperienceFromDashboard)
  // is the explicit entry point into that flow instead.
  const handleSuggestedProfilesComplete = () => {
    setStage("dashboard");
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

  // Phase 1 section 20: avoids a one-frame flash of "not logged in" while
  // the initial GET /api/auth/me/ (useAuth.js's mount effect) is still
  // confirming whether a stored token is still valid.
  if (!entered && auth.isLoading) {
    return <div className="app-shell" />;
  }

  if (!entered) {
    if (authView === "login") {
      return (
        <div className="app-shell">
          <LoginPage
            onLogin={handleLogin}
            onSwitchToRegister={() => setAuthView("register")}
            onBack={() => setAuthView(null)}
          />
        </div>
      );
    }
    if (authView === "register") {
      return (
        <div className="app-shell">
          <RegisterPage onRegister={auth.register} onSwitchToLogin={() => setAuthView("login")} />
        </div>
      );
    }
    return (
      <div className="app-shell">
        <LandingPage
          onExplore={handleExplore}
          onLogin={() => setAuthView("login")}
          onRegister={() => setAuthView("register")}
          authenticatedUser={auth.user}
          onLogout={handleLogout}
          onGoToDashboard={handleGoToDashboard}
        />
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
        <Header
          view={taskView}
          onNavigate={handleHeaderNavigate}
          onReset={handleReset}
          onHome={handleGoHome}
          // Phase 6 section 24: only offered for the account entry path --
          // Header's own rendering of these is entirely opt-in (see
          // Header.jsx), so the demo flow's chrome is byte-for-byte
          // unchanged when these are omitted.
          onGoToDashboard={entryMode === "account" ? handleGoToDashboard : undefined}
          onViewHistory={entryMode === "account" ? handleViewHistory : undefined}
          onExploreWhatIf={entryMode === "account" ? handleExploreWhatIf : undefined}
        />
      )}
      <main id="main-content">
        {stage === "select-user" && <SelectUserPage onSelect={handleSelectUser} />}

        {stage === "welcome" && (
          <div className="profile-flow">
            <div className="card profile-flow__narrow">
              <h1>Welcome, {auth.user?.display_name || auth.user?.username}</h1>
              <p>
                Let's set up your Ability Profile so AbilityOS knows how you prefer to interact with technology.
              </p>
              <button type="button" className="btn btn--primary profile-flow__cta" onClick={() => setStage("consent")}>
                Continue
              </button>
            </div>
          </div>
        )}

        {stage === "consent" && (
          <ConsentPage alreadyGranted={flow.consent?.granted} onAgree={handleAgreeConsent} busy={flow.loading} />
        )}

        {stage === "questionnaire" && (
          <QuestionnairePage onComplete={handleQuestionnaireComplete} onCancel={() => setStage("profile")} />
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
            onContinue={handleProfileSummaryContinue}
            onEditAgain={() => setStage("profile")}
            onClearProfile={flow.clearProfile}
            busy={flow.loading}
          />
        )}

        {stage === "suggested-profiles" && (
          <SuggestedProfilesPage
            userId={flow.userId}
            onComplete={handleSuggestedProfilesComplete}
            onBack={() => setStage(suggestedProfilesOrigin)}
          />
        )}

        {stage === "dashboard" && (
          <DashboardPage
            user={auth.user}
            profile={flow.profile}
            consentGranted={Boolean(flow.consent?.granted)}
            onSetupProfile={handleSetupProfile}
            onEditProfile={handleEditProfileFromDashboard}
            onManageProfiles={handleManageProfiles}
            onStartExperience={handleStartExperienceFromDashboard}
            onGrantConsent={handleGrantConsentFromDashboard}
            onViewHistory={handleViewHistory}
            onExploreWhatIf={handleExploreWhatIf}
            onHome={handleGoHome}
            onLogout={handleLogout}
          />
        )}

        {stage === "history" && (
          <HistoryPage
            userId={flow.userId}
            onBack={() => setStage("dashboard")}
            onStartExperience={handleStartExperienceFromDashboard}
          />
        )}

        {stage === "what-if" && <WhatIfPage profile={flow.profile} onBack={() => setStage("dashboard")} />}

        {stage === "task-environment" && (
          <TaskEnvironmentPage
            userId={flow.userId}
            // Phase 5 section 24: AbilityProfile.label is only ever set by
            // seed_demo.py's demo personas (see docs/DASHBOARD.md's known
            // limitations) -- a real account's own profile never has one,
            // so this page would otherwise show a blank "Selected user: —"
            // for every authenticated visitor. Falling back to the
            // account's own name gives the same "using your profile"
            // indication the spec asks for, without touching
            // TaskEnvironmentPage.jsx itself.
            profileLabel={
              entryMode === "account" ? auth.user?.display_name || auth.user?.username : flow.profile?.label
            }
            onBackToSummary={() => setStage(entryMode === "account" ? "dashboard" : "summary")}
            onOpenKiosk={handleOpenKiosk}
          />
        )}

        {stage === "task" && <DemoPage userId={flow.userId} resetSignal={resetSignal} />}
        {stage === "analytics" && <AnalyticsPage key={resetSignal} />}
      </main>
    </div>
  );
}
