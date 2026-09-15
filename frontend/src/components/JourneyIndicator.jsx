import "./JourneyIndicator.css";

const STEPS = [
  { key: "select-user", label: "Select" },
  { key: "consent", label: "Consent" },
  { key: "profile", label: "Profile" },
  { key: "summary", label: "Summary" },
];

/** Lightweight orientation cue for the profile-setup journey (Phase 2
 * section 19). Purely presentational — it reflects `currentStep`, it
 * doesn't drive navigation. */
export default function JourneyIndicator({ currentStep }) {
  const currentIndex = STEPS.findIndex((s) => s.key === currentStep);

  return (
    <ol className="journey" aria-label="Profile setup progress">
      {STEPS.map((step, index) => {
        const state = index < currentIndex ? "done" : index === currentIndex ? "current" : "upcoming";
        return (
          <li key={step.key} className={`journey__step journey__step--${state}`} aria-current={state === "current" ? "step" : undefined}>
            <span className="journey__number">{index + 1}</span>
            <span className="journey__label">{step.label}</span>
          </li>
        );
      })}
    </ol>
  );
}
