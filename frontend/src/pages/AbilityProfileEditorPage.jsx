import { useState } from "react";
import JourneyIndicator from "../components/JourneyIndicator";
import { ABILITY_QUESTIONS, MODALITY_QUESTION } from "../constants/abilityProfile";
import "./ProfileFlow.css";

function QuestionGroup({ heading, question, options, value, onChange }) {
  const groupId = `q-${heading.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <fieldset className="profile-editor__group">
      <legend>
        <span className="profile-editor__heading">{heading}</span>
        <span className="profile-editor__question">{question}</span>
      </legend>
      <div className="profile-editor__options" role="radiogroup" aria-labelledby={groupId}>
        {options.map((opt) => (
          <label key={opt.value} className="profile-editor__option">
            <input
              type="radio"
              name={groupId}
              value={opt.value}
              checked={value === opt.value}
              onChange={() => onChange(opt.value)}
            />
            {opt.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

/**
 * "Your Ability Profile" editor (Phase 2 sections 4/8). Every field here
 * maps 1:1 to a controlled value in backend/abilities/constants.py — the
 * options rendered are literally that same enum via
 * frontend/src/constants/abilityProfile.js, so there is no way to submit
 * a value the backend wouldn't also recognise as valid.
 */
export default function AbilityProfileEditorPage({ profile, onSave, busy, error }) {
  const initialLevels = Object.fromEntries(
    ABILITY_QUESTIONS.map((q) => [q.key, profile?.dimensions?.[q.key]?.level ?? q.options[0].value])
  );
  const [levels, setLevels] = useState(initialLevels);
  const [modality, setModality] = useState(profile?.preferred_modality || "visual");

  const handleSave = async () => {
    const dimensions = Object.fromEntries(
      Object.entries(levels).map(([key, level]) => [key, { level }])
    );
    await onSave(dimensions, modality);
  };

  return (
    <div className="profile-flow">
      <JourneyIndicator currentStep="profile" />
      <div className="card profile-flow__wide">
        <h1>Your Ability Profile</h1>
        <p className="profile-flow__subtitle">
          Help AbilityOS understand how you prefer to interact with technology.
        </p>

        {ABILITY_QUESTIONS.map((q) => (
          <QuestionGroup
            key={q.key}
            heading={q.heading}
            question={q.question}
            options={q.options}
            value={levels[q.key]}
            onChange={(value) => setLevels((prev) => ({ ...prev, [q.key]: value }))}
          />
        ))}

        <QuestionGroup
          heading={MODALITY_QUESTION.heading}
          question={MODALITY_QUESTION.question}
          options={MODALITY_QUESTION.options}
          value={modality}
          onChange={setModality}
        />

        {error && <p className="dev-panel__ai-note">Unable to save your Ability Profile. Please try again.</p>}

        <div className="row profile-flow__actions">
          <button className="btn btn--primary" onClick={handleSave} disabled={busy}>
            {busy ? "Saving…" : "Save Profile"}
          </button>
        </div>
      </div>
    </div>
  );
}
