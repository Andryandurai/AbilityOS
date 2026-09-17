import { useEffect, useState } from "react";
import * as api from "../services/api";
import { summarizeProfile } from "../constants/abilityProfile";
import "./ProfileFlow.css";
import "./QuestionnairePage.css";

/**
 * Phase 2 (Onboarding, Consent & Questionnaire) — a structured, one-
 * question-at-a-time front door onto the existing Ability Profile. Every
 * answer is saved via the real API as it's chosen (POST .../response/);
 * the generated profile is only ever written to the person's real
 * AbilityProfile after they explicitly confirm it on the review screen
 * (POST .../confirm/) -- see docs/QUESTIONNAIRE.md for why completing and
 * confirming are two separate steps.
 *
 * This is a front door, not a second intelligence system: the backend
 * (questionnaire.services.questionnaire_service) does the one-question-
 * key-maps-to-one-dimension mapping and every validation; this component
 * only renders whatever it returns and never invents a dimension value
 * itself.
 */
export default function QuestionnairePage({ onComplete, onCancel }) {
  const [phase, setPhase] = useState("loading"); // loading | intro | questions | review | error
  const [questions, setQuestions] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({}); // { [questionId]: selected_value }
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [generatedDimensions, setGeneratedDimensions] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [questionnaire, session] = await Promise.all([api.getQuestionnaire(), api.startQuestionnaire()]);
        if (cancelled) return;
        setQuestions(questionnaire.questions);
        setSessionId(session.session_id);
        setPhase("intro");
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
          setPhase("error");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const currentQuestion = questions[currentIndex];
  const isLastQuestion = currentIndex === questions.length - 1;

  const handleSelect = async (value) => {
    setAnswers((prev) => ({ ...prev, [currentQuestion.id]: value }));
    setSaving(true);
    setError(null);
    try {
      await api.saveQuestionnaireResponse(sessionId, currentQuestion.id, value);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleBack = () => setCurrentIndex((i) => Math.max(0, i - 1));

  const handleNext = async () => {
    if (!isLastQuestion) {
      setCurrentIndex((i) => i + 1);
      return;
    }
    setGenerating(true);
    setError(null);
    try {
      const result = await api.completeQuestionnaire(sessionId);
      setGeneratedDimensions(result.dimensions);
      setPhase("review");
    } catch (err) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleAnswerAgain = () => {
    setPhase("questions");
    setCurrentIndex(0);
    setGeneratedDimensions(null);
  };

  const handleConfirm = async () => {
    setConfirming(true);
    setError(null);
    try {
      await api.confirmQuestionnaire(sessionId);
      onComplete();
    } catch (err) {
      setError(err.message);
    } finally {
      setConfirming(false);
    }
  };

  if (phase === "loading") {
    return (
      <div className="profile-flow">
        <div className="card profile-flow__narrow">Loading the questionnaire…</div>
      </div>
    );
  }

  if (phase === "error") {
    return (
      <div className="profile-flow">
        <div className="card profile-flow__narrow" role="alert">
          <p>Unable to load the questionnaire.</p>
          <p className="questionnaire__error">{error}</p>
        </div>
      </div>
    );
  }

  if (phase === "intro") {
    return (
      <div className="profile-flow">
        <div className="card profile-flow__narrow">
          <h1>Let's understand how technology works best for you</h1>
          <p>
            These questions focus on everyday interaction preferences — vision, hearing, touch, reach, speech,
            attention, fatigue and response time.
          </p>
          <p>
            This is not a medical assessment. Your answers help AbilityOS personalize digital interactions to how
            you actually prefer to interact.
          </p>
          <p className="profile-flow__note">{questions.length} short questions — you can go back and change an answer at any time.</p>
          <button type="button" className="btn btn--primary profile-flow__cta" onClick={() => setPhase("questions")}>
            Begin
          </button>
          {onCancel && (
            <button type="button" className="btn btn--ghost profile-flow__cta" onClick={onCancel} style={{ marginTop: 8 }}>
              Not now
            </button>
          )}
        </div>
      </div>
    );
  }

  if (phase === "review") {
    const previewProfile = { dimensions: generatedDimensions, preferred_modality: "visual" };
    const entries = summarizeProfile(previewProfile);
    return (
      <div className="profile-flow">
        <div className="card profile-flow__wide">
          <h1>Here's what AbilityOS understands</h1>
          <p className="profile-flow__subtitle">
            Nothing has been saved yet. Review your answers below, then confirm to save this as your Ability
            Profile.
          </p>

          {entries.length === 0 ? (
            <p>No specific adaptations needed — your answers were typical across the board.</p>
          ) : (
            <ul className="questionnaire__review-list">
              {entries.map((entry) => (
                <li key={entry.text}>
                  <span aria-hidden="true">{entry.emoji}</span> {entry.text}
                </li>
              ))}
            </ul>
          )}

          {error && <p className="questionnaire__error">{error}</p>}

          <div className="row profile-flow__actions">
            <button type="button" className="btn btn--ghost" onClick={handleAnswerAgain} disabled={confirming}>
              Answer Again
            </button>
            <button type="button" className="btn btn--primary" onClick={handleConfirm} disabled={confirming}>
              {confirming ? "Saving…" : "Confirm & Save My Profile"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // phase === "questions"
  const groupId = `questionnaire-q-${currentQuestion.id}`;
  return (
    <div className="profile-flow">
      <div className="card profile-flow__wide">
        <p className="questionnaire__progress-label">
          Question {currentIndex + 1} of {questions.length}
        </p>
        <div
          className="questionnaire__progress-dots"
          role="img"
          aria-label={`Question ${currentIndex + 1} of ${questions.length}`}
        >
          {questions.map((q, i) => (
            <span
              key={q.id}
              className={`questionnaire__dot ${i < currentIndex ? "questionnaire__dot--done" : ""} ${
                i === currentIndex ? "questionnaire__dot--current" : ""
              }`}
              aria-hidden="true"
            />
          ))}
        </div>

        <fieldset className="profile-editor__group" style={{ borderTop: "none", paddingTop: 0 }}>
          <legend>
            <span className="profile-editor__question" style={{ fontSize: "1.3rem", fontWeight: 600 }}>
              {currentQuestion.question_text}
            </span>
          </legend>
          <div className="profile-editor__options" role="radiogroup" aria-labelledby={groupId}>
            {currentQuestion.options.map((opt) => {
              const selected = answers[currentQuestion.id] === opt.value;
              return (
                <label
                  key={opt.value}
                  className={`profile-editor__option ${selected ? "questionnaire__option--selected" : ""}`}
                >
                  <input
                    type="radio"
                    name={groupId}
                    value={opt.value}
                    checked={selected}
                    onChange={() => handleSelect(opt.value)}
                  />
                  {opt.label}
                </label>
              );
            })}
          </div>
        </fieldset>

        {error && (
          <p className="questionnaire__error" role="alert">
            {error}
          </p>
        )}

        <div className="questionnaire__nav">
          <button type="button" className="btn btn--ghost" onClick={handleBack} disabled={currentIndex === 0}>
            ← Back
          </button>
          <button
            type="button"
            className="btn btn--primary"
            onClick={handleNext}
            disabled={!answers[currentQuestion.id] || saving || generating}
          >
            {generating ? "Generating…" : isLastQuestion ? "Generate My Profile" : "Next →"}
          </button>
        </div>
      </div>
    </div>
  );
}
