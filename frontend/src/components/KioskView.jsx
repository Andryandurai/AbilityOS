import { useEffect, useMemo, useRef, useState } from "react";
import "./KioskView.css";

const DESTINATIONS = [
  { id: "dest_central_station", label: "Central Station" },
  { id: "dest_airport", label: "Airport" },
  { id: "dest_hospital", label: "Hospital" },
  { id: "dest_university", label: "University" },
];
const TICKET_TYPES = [
  { id: "ticket_single", label: "Single" },
  { id: "ticket_return", label: "Return" },
];

const MISS_CHANCE_BY_DEXTERITY = {
  typical: 0,
  "reduced-precision": 0.4,
  "single-tap-only": 0.6,
};
const COMFORTABLE_TARGET_PX = 88; // must match barriers/services/detection.py

function controlSize(environment, controlId) {
  const control = (environment?.data?.controls || []).find((c) => c.id === controlId);
  if (!control) return { width: 120, height: 40 };
  return { width: control.width, height: control.height };
}

function hasBarrier(barriers, type) {
  return (barriers || []).some((b) => b.barrier_type === type);
}

function speak(text) {
  try {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    window.speechSynthesis.speak(utterance);
  } catch {
    /* speech synthesis not available in this browser — non-fatal */
  }
}

function vibrate(pattern) {
  try {
    navigator.vibrate?.(pattern);
  } catch {
    /* vibration not available on this device — non-fatal */
  }
}

function playTone(frequency = 440, durationMs = 220) {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();
    const oscillator = ctx.createOscillator();
    const gain = ctx.createGain();
    oscillator.frequency.value = frequency;
    oscillator.connect(gain);
    gain.connect(ctx.destination);
    gain.gain.setValueAtTime(0.08, ctx.currentTime);
    oscillator.start();
    oscillator.stop(ctx.currentTime + durationMs / 1000);
    oscillator.onended = () => ctx.close();
  } catch {
    /* Web Audio not available — non-fatal */
  }
}

/**
 * The simulated public ticket kiosk (Part 12/15/17) — the primary demo
 * surface. Deliberately real, not decorative: unresolved barriers actually
 * make the interface harder to use (missed taps on undersized controls,
 * washed-out contrast, every choice on one screen, an audio-only alert with
 * no visual mirror), and applying an adaptation actually changes the
 * rendering and behaviour, not just a label saying it did.
 */
export default function KioskView({
  environment,
  barriers,
  appliedEffects,
  profile,
  interactive,
  baselineMode,
  onComplete,
  onAbandon,
  onEvent,
}) {
  // Phase 7 section 8: fires a structured, task-relevant event — never a
  // no-op if the caller didn't pass onEvent, since the standalone preview
  // (interactive=false) doesn't track a session at all.
  const fireEvent = (eventType, detail = {}) => onEvent?.(eventType, detail);
  const [selections, setSelections] = useState({ destination: null, ticketType: null, quantity: 1 });
  const [stepIndex, setStepIndex] = useState(0);
  const [errors, setErrors] = useState(0);
  const [assistanceRequested, setAssistanceRequested] = useState(false);
  const [shakingControl, setShakingControl] = useState(null);
  const [announcement, setAnnouncement] = useState("");
  const [confirmingPurchase, setConfirmingPurchase] = useState(false);
  const [outcome, setOutcome] = useState(null);
  const startTimeRef = useRef(null);
  // Slower Reaction Speed: a real countdown on the confirmation interaction,
  // not a static "04 seconds" label (section 16) -- remainingSeconds ticks
  // down via a real setInterval below, and confirmationExpired genuinely
  // disables BUY TICKET until the person retries.
  const [remainingSeconds, setRemainingSeconds] = useState(null);
  const [confirmationExpired, setConfirmationExpired] = useState(false);
  const [confirmRetryTick, setConfirmRetryTick] = useState(0);

  useEffect(() => {
    setSelections({ destination: null, ticketType: null, quantity: 1 });
    setStepIndex(0);
    setErrors(0);
    setAssistanceRequested(false);
    setOutcome(null);
    setRemainingSeconds(null);
    setConfirmationExpired(false);
    startTimeRef.current = null;
  }, [environment, baselineMode]);

  const dexterityLevel = profile?.dimensions?.dexterity?.level || "typical";
  const missChance = interactive && !appliedEffects.button_scale ? MISS_CHANCE_BY_DEXTERITY[dexterityLevel] || 0 : 0;

  const contrastUnresolved = hasBarrier(barriers, "low_contrast") && appliedEffects.contrast !== "high";
  // Fatigue / Reduced Stamina: "streamlined" is its own flow variant, not
  // just another label for "guided" -- it combines ticket type + quantity
  // onto one screen (fewer navigation transitions), while "guided" shows
  // every step one at a time. Both still gate on `guided` for the shared
  // step-header/back-button chrome below.
  const streamlined = appliedEffects.flow === "streamlined";
  const guided = Boolean(
    appliedEffects.flow === "guided" ||
      appliedEffects.flow === "simplified" ||
      streamlined ||
      appliedEffects.choice_limit
  );
  const audioUnmirrored = hasBarrier(barriers, "audio_only_alert") && !appliedEffects.banner_alert;
  // Limited Mobility + Reach: an unresolved controls_out_of_reach barrier
  // visibly pushes the primary action out toward the edge of the kiosk
  // (representing it sitting outside the person's comfortable interaction
  // zone); reachable_layout pulls it back into a labeled "within reach"
  // zone — a real layout change, not just a banner claiming one happened.
  const reachUnresolved = hasBarrier(barriers, "controls_out_of_reach") && !appliedEffects.reachable_layout;
  const reachResolved = hasBarrier(barriers, "controls_out_of_reach") && Boolean(appliedEffects.reachable_layout);
  // Speech Difficulty: an unresolved voice_only_input barrier shows the
  // kiosk's real voice prompt above the touch destination grid (touch
  // still works underneath — this profile isn't blocked, just nudged
  // toward speech); touch_text_mode removes that prompt and confirms
  // touch/text is the path, both real rendering changes.
  const voiceUnresolved = hasBarrier(barriers, "voice_only_input") && !appliedEffects.touch_text_mode;
  const voiceResolved = hasBarrier(barriers, "voice_only_input") && Boolean(appliedEffects.touch_text_mode);
  const [bannerAlert, setBannerAlert] = useState(null);

  const buttonScale = appliedEffects.button_scale || 1;
  const spacingScale = appliedEffects.spacing_scale || 1;
  const textScale = appliedEffects.text_scale || 1;

  // The 4 logical selections (destination, ticket type, quantity, confirm)
  // are unchanged either way -- `streamlined` only reduces how many
  // separate navigation screens they're spread across, by putting ticket
  // type and quantity on the same screen instead of requiring a "Next" tap
  // between them.
  const steps = useMemo(
    () =>
      streamlined
        ? [
            { id: "select_destination", name: "Where are you going?" },
            { id: "select_ticket_and_quantity", name: "Ticket type & quantity" },
            { id: "confirm_purchase", name: "Confirm purchase" },
          ]
        : [
            { id: "select_destination", name: "Where are you going?" },
            { id: "select_ticket_type", name: "Ticket type" },
            { id: "select_quantity", name: "Quantity" },
            { id: "confirm_purchase", name: "Confirm purchase" },
          ],
    [streamlined]
  );

  useEffect(() => {
    if (!guided || !interactive) return;
    if (appliedEffects.voice_prompts || appliedEffects.tts) {
      speak(steps[stepIndex].name);
    }
  }, [stepIndex, guided, interactive]); // eslint-disable-line react-hooks/exhaustive-deps

  // Slower Reaction Speed: the confirmation step's real response window --
  // the environment's own configured fact (kiosk_standard.confirmation_
  // timeout_seconds), extended only when increase_interaction_timeout was
  // actually applied. Never hardcoded/faked in the frontend.
  const confirmStepIndex = streamlined ? 2 : 3;
  const showingConfirmStep = !guided || stepIndex === confirmStepIndex;
  const standardTimeoutSeconds = environment?.data?.confirmation_timeout_seconds ?? null;
  const isExtendedTimeout = Boolean(appliedEffects.extended_timeout_seconds);
  const effectiveTimeoutSeconds = appliedEffects.extended_timeout_seconds || standardTimeoutSeconds;

  const registerStart = () => {
    if (startTimeRef.current === null) startTimeRef.current = performance.now();
  };

  const announce = (text) => setAnnouncement(text);

  const attemptTap = (controlId, onSuccess) => {
    if (!interactive) return;
    registerStart();
    const size = controlSize(environment, controlId);
    const smallest = Math.min(size.width, size.height) * buttonScale;
    const isSmall = smallest < COMFORTABLE_TARGET_PX;

    if (isSmall && Math.random() < missChance) {
      setErrors((e) => e + 1);
      setShakingControl(controlId);
      announce("Tap missed — the target was too small. Try again.");
      fireEvent("validation_error", { controlId, metadata: { reason: "target_too_small" } });
      window.setTimeout(() => setShakingControl(null), 350);
      return;
    }
    if (appliedEffects.haptics) vibrate(50);
    onSuccess();
  };

  const selectDestination = (id) =>
    attemptTap(id, () => {
      const isReselection = selections.destination !== null && selections.destination !== id;
      setSelections((s) => ({ ...s, destination: id }));
      announce(`${DESTINATIONS.find((d) => d.id === id).label} selected.`);
      fireEvent(isReselection ? "control_reselected" : "control_selected", {
        step: "select_destination",
        controlId: id,
      });
      if (guided) setStepIndex(1);
    });

  const selectTicketType = (id) =>
    attemptTap(id, () => {
      const isReselection = selections.ticketType !== null && selections.ticketType !== id;
      setSelections((s) => ({ ...s, ticketType: id }));
      announce(`${TICKET_TYPES.find((t) => t.id === id).label} ticket selected.`);
      fireEvent(isReselection ? "control_reselected" : "control_selected", {
        step: "select_ticket_type",
        controlId: id,
      });
      // Streamlined: quantity lives on this same screen, so picking a
      // ticket type doesn't navigate anywhere -- that's the reduced
      // navigation-transition burden this flow is for.
      if (guided && !streamlined) setStepIndex(2);
    });

  const changeQuantity = (delta) =>
    attemptTap(delta > 0 ? "quantity_plus" : "quantity_minus", () => {
      setSelections((s) => ({ ...s, quantity: Math.max(1, Math.min(9, s.quantity + delta)) }));
    });

  // Reached only via BUY TICKET, which stays disabled until both a
  // destination and a ticket type are selected — so a completion the
  // person actually reaches here is always a genuine success. An
  // incomplete/abandoned attempt is a distinct path (handleLeaveTask
  // below), not something this function ever reports.
  const finalizePurchase = () => {
    const elapsedSeconds = startTimeRef.current
      ? Math.max(1, Math.round((performance.now() - startTimeRef.current) / 1000))
      : 1;

    if (hasBarrier(barriers, "audio_only_alert")) {
      playTone(660, 260);
      if (!audioUnmirrored) {
        setBannerAlert("success");
        if (appliedEffects.haptics) vibrate([80]);
        window.setTimeout(() => setBannerAlert(null), 2200);
      }
    }

    const result = {
      completed: true,
      errors,
      time_seconds: elapsedSeconds,
      assistance_requested: assistanceRequested,
      effort: Math.min(5, 1 + errors),
      confidence: Math.max(1, 5 - errors),
    };
    setOutcome(result);
    fireEvent("task_completed");
    if (appliedEffects.voice_prompts || appliedEffects.tts) {
      speak("Purchase complete.");
    }
    onComplete(result);
  };

  const attemptBuy = () =>
    attemptTap("buy_ticket", () => {
      if (appliedEffects.confirm_step) {
        setConfirmingPurchase(true);
        fireEvent("confirmation_opened", { step: "confirm_purchase" });
        return;
      }
      finalizePurchase();
    });

  const confirmPurchase = () => {
    fireEvent("confirmation_completed", { step: "confirm_purchase" });
    finalizePurchase();
  };

  // Phase 7 section 31/47: records the request and lets the person keep
  // going — it no longer ends the task on its own (that used to conflate
  // "I need a hand" with "I'm giving up").
  const requestAssistance = () => {
    setAssistanceRequested(true);
    announce("Staff assistance requested.");
    fireEvent("assistance_requested");
  };

  // Phase 7 section 30/46: the one path to an incomplete/abandoned
  // outcome — distinct from finalizePurchase, which (now that BUY TICKET
  // requires both selections) always represents a genuine completion.
  const handleLeaveTask = () => {
    const elapsedSeconds = startTimeRef.current
      ? Math.max(1, Math.round((performance.now() - startTimeRef.current) / 1000))
      : 0;
    const result = {
      completed: false,
      errors,
      time_seconds: elapsedSeconds,
      assistance_requested: assistanceRequested,
      effort: Math.min(5, 1 + errors),
      confidence: 2,
    };
    setOutcome(result);
    onAbandon?.(result);
  };

  const handleBack = () => {
    fireEvent("back_navigation", { step: steps[stepIndex]?.id });
    setStepIndex((i) => Math.max(0, i - 1));
  };

  const canBuy = selections.destination && selections.ticketType;
  const readyToConfirm = interactive && Boolean(canBuy) && !outcome && showingConfirmStep;

  useEffect(() => {
    if (!readyToConfirm || !effectiveTimeoutSeconds) {
      setRemainingSeconds(null);
      return undefined;
    }
    setConfirmationExpired(false);
    setRemainingSeconds(effectiveTimeoutSeconds);
    const interval = window.setInterval(() => {
      setRemainingSeconds((s) => (s !== null ? Math.max(0, s - 1) : s));
    }, 1000);
    return () => window.clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [readyToConfirm, effectiveTimeoutSeconds, confirmRetryTick]);

  useEffect(() => {
    if (remainingSeconds === 0 && !confirmationExpired) {
      setConfirmationExpired(true);
      fireEvent("interaction_timeout", { step: "confirm_purchase" });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [remainingSeconds]);

  const retryConfirmation = () => {
    setConfirmationExpired(false);
    setConfirmRetryTick((t) => t + 1);
  };

  const kioskStyle = {
    "--button-scale": buttonScale,
    "--spacing-scale": spacingScale,
    "--text-scale": textScale,
  };

  // Phase 6 section 25: a respectful, functional-language indicator — never
  // medical/diagnostic terminology — shown only when the backend actually
  // applied something (never a frontend guess).
  const hasActiveAdaptation = interactive && Object.keys(appliedEffects || {}).length > 0;

  return (
    <div
      className={`kiosk ${contrastUnresolved ? "kiosk--low-contrast" : "kiosk--high-contrast"} ${
        !interactive ? "kiosk--disabled" : ""
      }`}
      style={kioskStyle}
    >
      <div className="visually-hidden" role="status" aria-live="polite">
        {announcement}
      </div>

      {bannerAlert && (
        <div className={`kiosk__banner kiosk__banner--${bannerAlert}`} role="alert">
          {bannerAlert === "success" ? "Purchase successful." : "Something needs your attention."}
        </div>
      )}

      {hasActiveAdaptation && (
        <div className="kiosk__adapted-indicator" role="status">
          ✓ Interface personalized for easier interaction
        </div>
      )}

      <header className="kiosk__header">
        <span className="kiosk__brand">CITY TRANSIT</span>
        {guided && (
          <span className="kiosk__progress" aria-label={`Step ${stepIndex + 1} of ${steps.length}`}>
            Step {stepIndex + 1} of {steps.length}: {steps[stepIndex].name}
          </span>
        )}
      </header>

      {guided && !outcome && stepIndex > 0 && (
        <button type="button" className="btn btn--ghost kiosk__back" onClick={handleBack} disabled={!interactive}>
          ← Back
        </button>
      )}

      {outcome ? (
        <div className="kiosk__result">
          <h3>{outcome.completed ? "Ticket purchased" : "Purchase not completed"}</h3>
          <p>
            {selections.quantity}× {TICKET_TYPES.find((t) => t.id === selections.ticketType)?.label || "?"} ticket to{" "}
            {DESTINATIONS.find((d) => d.id === selections.destination)?.label || "an unselected destination"}
          </p>
        </div>
      ) : (
        <div className="kiosk__body">
          {(!guided || stepIndex === 0) && (
            <section aria-labelledby="dest-heading" className="kiosk__section">
              <h3 id="dest-heading">{voiceResolved ? "Choose a destination:" : "Where are you going?"}</h3>
              {voiceUnresolved && (
                <p className="kiosk__voice-note" role="status">
                  🎤 This kiosk suggests speaking your destination.
                </p>
              )}
              {voiceResolved && (
                <p className="kiosk__voice-note kiosk__voice-note--ok" role="status">
                  ✓ Touch and text selection available — no speech required.
                </p>
              )}
              <div className="kiosk__grid">
                {DESTINATIONS.map((d) => (
                  <button
                    key={d.id}
                    type="button"
                    disabled={!interactive}
                    aria-pressed={selections.destination === d.id}
                    className={`kiosk__btn ${shakingControl === d.id ? "kiosk__btn--shake" : ""} ${
                      selections.destination === d.id ? "kiosk__btn--selected" : ""
                    }`}
                    onClick={() => selectDestination(d.id)}
                  >
                    {d.label}
                  </button>
                ))}
              </div>
            </section>
          )}

          {(!guided || stepIndex === 1) && (
            <section aria-labelledby="ticket-heading" className="kiosk__section">
              <h3 id="ticket-heading">Ticket Type</h3>
              {streamlined && <p className="kiosk__streamline-hint">Choose a ticket type and quantity below, then confirm.</p>}
              <div className="kiosk__grid">
                {TICKET_TYPES.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    disabled={!interactive}
                    aria-pressed={selections.ticketType === t.id}
                    className={`kiosk__btn ${shakingControl === t.id ? "kiosk__btn--shake" : ""} ${
                      selections.ticketType === t.id ? "kiosk__btn--selected" : ""
                    }`}
                    onClick={() => selectTicketType(t.id)}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </section>
          )}

          {(!guided || stepIndex === (streamlined ? 1 : 2)) && (
            <section aria-labelledby="qty-heading" className="kiosk__section">
              <h3 id="qty-heading">Quantity</h3>
              <div className="kiosk__quantity">
                <button
                  type="button"
                  disabled={!interactive}
                  className={`kiosk__btn kiosk__btn--square ${shakingControl === "quantity_minus" ? "kiosk__btn--shake" : ""}`}
                  onClick={() => changeQuantity(-1)}
                  aria-label="Decrease quantity"
                >
                  −
                </button>
                <span className="kiosk__quantity-value" aria-live="polite">
                  {selections.quantity}
                </span>
                <button
                  type="button"
                  disabled={!interactive}
                  className={`kiosk__btn kiosk__btn--square ${shakingControl === "quantity_plus" ? "kiosk__btn--shake" : ""}`}
                  onClick={() => changeQuantity(1)}
                  aria-label="Increase quantity"
                >
                  +
                </button>
              </div>
              {guided && (
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => setStepIndex(streamlined ? 2 : 3)}
                  style={{ marginTop: 12 }}
                >
                  Next
                </button>
              )}
            </section>
          )}

          {(!guided || stepIndex === (streamlined ? 2 : 3)) && (
            <section
              aria-labelledby="buy-heading"
              className={`kiosk__section kiosk__section--buy ${
                reachUnresolved ? "kiosk__section--out-of-reach" : ""
              } ${reachResolved ? "kiosk__section--in-reach" : ""}`}
            >
              <h3 id="buy-heading" className="visually-hidden">
                Confirm purchase
              </h3>
              {reachUnresolved && (
                <p className="kiosk__reach-note" role="status">
                  ⚠ This control is outside the comfortable interaction area.
                </p>
              )}
              {reachResolved && (
                <p className="kiosk__reach-note kiosk__reach-note--ok" role="status">
                  ✓ Positioned within the comfortable interaction area.
                </p>
              )}
              {confirmingPurchase ? (
                <div className="stack">
                  <p>Buy {selections.quantity} ticket(s)? This can't be undone.</p>
                  <div className="row">
                    <button className="btn btn--primary" onClick={confirmPurchase}>
                      Yes, buy
                    </button>
                    <button className="btn btn--ghost" onClick={() => setConfirmingPurchase(false)}>
                      Cancel
                    </button>
                  </div>
                </div>
              ) : confirmationExpired ? (
                <div className="stack">
                  <p className="kiosk__timeout-message" role="alert">
                    ⏱ Time expired. Please try again.
                  </p>
                  <button type="button" className="btn btn--ghost" onClick={retryConfirmation}>
                    Try Again
                  </button>
                </div>
              ) : (
                <>
                  {canBuy && (
                    <p>Your ticket is ready.</p>
                  )}
                  {canBuy && effectiveTimeoutSeconds != null && (
                    <p
                      className={`kiosk__countdown ${isExtendedTimeout ? "kiosk__countdown--extended" : ""}`}
                      role="status"
                      aria-live="polite"
                    >
                      {isExtendedTimeout ? "Take your time to review." : `Please confirm within ${effectiveTimeoutSeconds} seconds.`}
                      {remainingSeconds != null && (
                        <span className="kiosk__countdown-value">
                          {" "}
                          {String(remainingSeconds).padStart(2, "0")} seconds
                        </span>
                      )}
                    </p>
                  )}
                  <button
                    type="button"
                    disabled={!interactive || !canBuy}
                    className={`kiosk__btn kiosk__btn--buy ${shakingControl === "buy_ticket" ? "kiosk__btn--shake" : ""}`}
                    onClick={attemptBuy}
                  >
                    BUY TICKET
                  </button>
                </>
              )}
            </section>
          )}
        </div>
      )}

      {interactive && !outcome && (
        <footer className="kiosk__footer">
          <div className="row">
            <button type="button" className="btn btn--ghost" onClick={requestAssistance} disabled={assistanceRequested}>
              {assistanceRequested ? "Help requested ✓" : "Ask staff for help"}
            </button>
            <button type="button" className="btn btn--ghost kiosk__leave" onClick={handleLeaveTask}>
              Leave without finishing
            </button>
          </div>
          <span className="kiosk__error-count" aria-live="polite">
            Errors so far: {errors}
          </span>
        </footer>
      )}
    </div>
  );
}
