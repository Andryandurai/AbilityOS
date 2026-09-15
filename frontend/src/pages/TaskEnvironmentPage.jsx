import { useState } from "react";
import AdaptationDecisionPanel from "../components/AdaptationDecisionPanel";
import BarrierCard from "../components/BarrierCard";
import * as api from "../services/api";
import { contrastLabel, DEMO_ENVIRONMENT, DEMO_TASK } from "../constants/taskEnvironment";
import "./TaskEnvironmentPage.css";

/**
 * Phase 3 (Task/Environment Understanding) -> Phase 4 (Barrier Detection)
 * -> Phase 5 (Adaptation + AI Decision Engine), all on one screen. Phase 5
 * only ever *returns* an ApprovedAdaptation here — nothing on this page
 * (or anywhere else) actually changes the kiosk yet. That's Phase 6.
 */
export default function TaskEnvironmentPage({ userId, profileLabel, onBackToSummary, onOpenKiosk }) {
  const [task, setTask] = useState(null);
  const [taskError, setTaskError] = useState(null);
  const [taskLoading, setTaskLoading] = useState(false);

  const [environment, setEnvironment] = useState(null);
  const [environmentError, setEnvironmentError] = useState(null);
  const [environmentLoading, setEnvironmentLoading] = useState(false);

  const [barriers, setBarriers] = useState(null);
  const [barriersError, setBarriersError] = useState(null);
  const [barriersLoading, setBarriersLoading] = useState(false);

  const [recommendation, setRecommendation] = useState(null);
  const [recommendationError, setRecommendationError] = useState(null);
  const [recommendationLoading, setRecommendationLoading] = useState(false);

  const handleAnalyzeTask = async () => {
    setTaskLoading(true);
    setTaskError(null);
    try {
      const descriptor = await api.analyzeTask(DEMO_TASK.taskId);
      setTask(descriptor);
    } catch {
      setTaskError("Unable to analyze this task. Please try again.");
    } finally {
      setTaskLoading(false);
    }
  };

  const handleAnalyzeEnvironment = async () => {
    setEnvironmentLoading(true);
    setEnvironmentError(null);
    try {
      const descriptor = await api.analyzeEnvironmentFixture(DEMO_ENVIRONMENT.environmentId);
      setEnvironment(descriptor);
    } catch {
      setEnvironmentError("Unable to analyze this environment. Please try again.");
    } finally {
      setEnvironmentLoading(false);
    }
  };

  const handleDetectBarriers = async () => {
    setBarriersLoading(true);
    setBarriersError(null);
    setRecommendation(null);
    try {
      const response = await api.detectBarriersStandalone(userId, DEMO_TASK.taskId, DEMO_ENVIRONMENT.environmentId);
      setBarriers(response.barriers);
    } catch (err) {
      if (err.status === 403) {
        setBarriersError("Consent is required before AbilityOS can analyze this profile.");
      } else {
        setBarriersError("Unable to run barrier detection. Please try again.");
      }
    } finally {
      setBarriersLoading(false);
    }
  };

  const handleRecommendAdaptation = async () => {
    setRecommendationLoading(true);
    setRecommendationError(null);
    try {
      const response = await api.recommendAdaptationStandalone(userId, DEMO_TASK.taskId, DEMO_ENVIRONMENT.environmentId);
      setRecommendation(response);
    } catch (err) {
      if (err.status === 403) {
        setRecommendationError("Consent is required before AbilityOS can recommend an adaptation.");
      } else {
        setRecommendationError("Unable to recommend an adaptation. Please try again.");
      }
    } finally {
      setRecommendationLoading(false);
    }
  };

  return (
    <div className="task-env">
      <div className="card">
        <h1>Task &amp; Environment</h1>
        <p className="task-env__selected-user">
          Selected user: <strong>{profileLabel || "—"}</strong>
        </p>
      </div>

      <div className="card">
        <h2>Task</h2>
        <div className="task-env__selector">
          <div>
            <strong>{DEMO_TASK.title}</strong>
            <p className="task-env__description">{DEMO_TASK.description}</p>
          </div>
          <button className="btn btn--primary" onClick={handleAnalyzeTask} disabled={taskLoading}>
            {taskLoading ? "Analyzing…" : "Analyze Task"}
          </button>
        </div>
        {taskError && (
          <p className="task-env__error" role="alert">
            {taskError}
          </p>
        )}

        {task && (
          <div className="task-env__descriptor">
            <h3>Task Descriptor</h3>
            <p>
              <strong>{task.name}</strong> — {task.description}
            </p>

            <h4>Steps</h4>
            <ol className="task-env__steps">
              {task.steps.map((step) => (
                <li key={step.id}>
                  <strong>{step.name}</strong>
                  {step.description && <span> — {step.description}</span>}
                </li>
              ))}
            </ol>

            <h4>Controls</h4>
            <ul className="task-env__controls">
              {task.controls.map((control) => (
                <li key={control.id}>
                  {control.label} — {control.type} — {control.interaction_type}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="card">
        <h2>Environment</h2>
        <div className="task-env__selector">
          <div>
            <strong>{DEMO_ENVIRONMENT.title}</strong>
            <p className="task-env__description">{DEMO_ENVIRONMENT.description}</p>
          </div>
          <button
            className="btn btn--primary"
            onClick={handleAnalyzeEnvironment}
            disabled={environmentLoading || !task}
            title={!task ? "Analyze the task first" : undefined}
          >
            {environmentLoading ? "Analyzing…" : "Analyze Environment"}
          </button>
        </div>
        {environmentError && (
          <p className="task-env__error" role="alert">
            {environmentError}
          </p>
        )}

        {environment && (
          <div className="task-env__descriptor">
            <h3>Environment Descriptor</h3>
            <p>
              Screen: {environment.screen.width} × {environment.screen.height}
              {environment.screen.dpi ? ` (${environment.screen.dpi} dpi)` : ""}
            </p>

            <h4>Controls</h4>
            <ul className="task-env__controls">
              {environment.controls.map((control) => (
                <li key={control.id}>
                  {control.label} — {control.width} × {control.height}px
                </li>
              ))}
            </ul>

            <dl className="task-env__facts">
              <div>
                <dt>Contrast</dt>
                <dd>{contrastLabel(environment.contrast)}</dd>
              </div>
              <div>
                <dt>Noise</dt>
                <dd>{environment.noise_level}</dd>
              </div>
              <div>
                <dt>Lighting</dt>
                <dd>{environment.lighting || "unknown"}</dd>
              </div>
            </dl>
          </div>
        )}
      </div>

      {task && environment && (
        <div className="card task-env__next">
          <h2>Barrier Analysis</h2>
          <p className="task-env__description">
            Selected Ability Profile: <strong>{profileLabel || "—"}</strong>
          </p>
          <button className="btn btn--primary" onClick={handleDetectBarriers} disabled={barriersLoading}>
            {barriersLoading ? "Detecting…" : "Detect Barriers"}
          </button>
          {barriersError && (
            <p className="task-env__error" role="alert">
              {barriersError}
            </p>
          )}

          {barriers && (
            <div className="task-env__descriptor">
              <h3>Detected Barriers</h3>
              {barriers.length === 0 ? (
                <p>No mismatch detected for this profile with this task and environment.</p>
              ) : (
                <>
                  {barriers.map((barrier) => (
                    <BarrierCard key={barrier.barrier_type} barrier={barrier} />
                  ))}

                  <button
                    className="btn btn--accent task-env__recommend"
                    onClick={handleRecommendAdaptation}
                    disabled={recommendationLoading}
                  >
                    {recommendationLoading ? "Deciding…" : "Recommend Adaptation"}
                  </button>
                  {recommendationError && (
                    <p className="task-env__error" role="alert">
                      {recommendationError}
                    </p>
                  )}
                  {recommendation && (
                    <AdaptationDecisionPanel recommendation={recommendation} onOpenKiosk={onOpenKiosk} />
                  )}
                </>
              )}
            </div>
          )}

          <button className="btn btn--ghost task-env__back" onClick={onBackToSummary}>
            Back to Profile Summary
          </button>
        </div>
      )}
    </div>
  );
}
