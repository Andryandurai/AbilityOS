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
}) {
  const [selections, setSelections] = useState({ destination: null, ticketType: null, quantity: 1 });
  const [stepIndex, setStepIndex] = useState(0);
  const [errors, setErrors] = useState(0);
  const [assistanceRequested, setAssistanceRequested] = useState(false);
  const [shakingControl, setShakingControl] = useState(null);
  const [announcement, setAnnouncement] = useState("");
  const [confirmingPurchase, setConfirmingPurchase] = useState(false);
  const [outcome, setOutcome] = useState(null);
  const startTimeRef = useRef(null);

  useEffect(() => {
    setSelections({ destination: null, ticketType: null, quantity: 1 });
    setStepIndex(0);
    setErrors(0);
    setAssistanceRequested(false);
    setOutcome(null);
    startTimeRef.current = null;
  }, [environment, baselineMode]);

  const dexterityLevel = profile?.dimensions?.dexterity?.level || "typical";
  const missChance = interactive && !appliedEffects.button_scale ? MISS_CHANCE_BY_DEXTERITY[dexterityLevel] || 0 : 0;

  const contrastUnresolved = hasBarrier(barriers, "low_contrast") && appliedEffects.contrast !== "high";
  const guided = Boolean(appliedEffects.flow === "guided" || appliedEffects.flow === "simplified" || appliedEffects.choice_limit);
  const audioUnmirrored = hasBarrier(barriers, "audio_only_alert") && !appliedEffects.banner_alert;
  const [bannerAlert, setBannerAlert] = useState(null);

  const buttonScale = appliedEffects.button_scale || 1;
  const spacingScale = appliedEffects.spacing_scale || 1;
  const textScale = appliedEffects.text_scale || 1;

  const steps = useMemo(
    () => [
      { id: "select_destination", name: "Where are you going?" },
      { id: "select_ticket_type", name: "Ticket type" },
      { id: "select_quantity", name: "Quantity" },
      { id: "confirm_purchase", name: "Confirm purchase" },
    ],
    []
  );

  useEffect(() => {
    if (!guided || !interactive) return;
    if (appliedEffects.voice_prompts || appliedEffects.tts) {
      speak(steps[stepIndex].name);
    }
  }, [stepIndex, guided, interactive]); // eslint-disable-line react-hooks/exhaustive-deps

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
      window.setTimeout(() => setShakingControl(null), 350);
      return;
    }
    if (appliedEffects.haptics) vibrate(50);
    onSuccess();
  };

  const selectDestination = (id) =>
    attemptTap(id, () => {
      setSelections((s) => ({ ...s, destination: id }));
      announce(`${DESTINATIONS.find((d) => d.id === id).label} selected.`);
      if (guided) setStepIndex(1);
    });

  const selectTicketType = (id) =>
    attemptTap(id, () => {
      setSelections((s) => ({ ...s, ticketType: id }));
      announce(`${TICKET_TYPES.find((t) => t.id === id).label} ticket selected.`);
      if (guided) setStepIndex(2);
    });

  const changeQuantity = (delta) =>
    attemptTap(delta > 0 ? "quantity_plus" : "quantity_minus", () => {
      setSelections((s) => ({ ...s, quantity: Math.max(1, Math.min(9, s.quantity + delta)) }));
    });

  const finalizePurchase = () => {
    const elapsedSeconds = startTimeRef.current
      ? Math.max(1, Math.round((performance.now() - startTimeRef.current) / 1000))
      : 1;
    const completed = Boolean(selections.destination && selections.ticketType);

    if (hasBarrier(barriers, "audio_only_alert")) {
      playTone(completed ? 660 : 220, 260);
      if (!audioUnmirrored) {
        setBannerAlert(completed ? "success" : "error");
        if (appliedEffects.haptics) vibrate(completed ? [80] : [120, 60, 120]);
        window.setTimeout(() => setBannerAlert(null), 2200);
      }
    }

    const result = {
      completed,
      errors,
      time_seconds: elapsedSeconds,
      assistance_requested: assistanceRequested,
      effort: Math.min(5, 1 + errors),
      confidence: completed ? Math.max(1, 5 - errors) : 2,
    };
    setOutcome(result);
    if (appliedEffects.voice_prompts || appliedEffects.tts) {
      speak(completed ? "Purchase complete." : "Purchase could not be completed.");
    }
    onComplete(result);
  };

  const attemptBuy = () =>
    attemptTap("buy_ticket", () => {
      if (appliedEffects.confirm_step) {
        setConfirmingPurchase(true);
        return;
      }
      finalizePurchase();
    });

  const requestAssistance = () => {
    setAssistanceRequested(true);
    announce("Staff assistance requested.");
    window.setTimeout(finalizePurchase, 50);
  };

  const canBuy = selections.destination && selections.ticketType;

  const kioskStyle = {
    "--button-scale": buttonScale,
    "--spacing-scale": spacingScale,
    "--text-scale": textScale,
  };

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

      <header className="kiosk__header">
        <span className="kiosk__brand">CITY TRANSIT</span>
        {guided && (
          <span className="kiosk__progress" aria-label={`Step ${stepIndex + 1} of ${steps.length}`}>
            Step {stepIndex + 1} of {steps.length}: {steps[stepIndex].name}
          </span>
        )}
      </header>

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
              <h3 id="dest-heading">Where are you going?</h3>
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

          {(!guided || stepIndex === 2) && (
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
                <button type="button" className="btn btn--ghost" onClick={() => setStepIndex(3)} style={{ marginTop: 12 }}>
                  Next
                </button>
              )}
            </section>
          )}

          {(!guided || stepIndex === 3) && (
            <section aria-labelledby="buy-heading" className="kiosk__section kiosk__section--buy">
              <h3 id="buy-heading" className="visually-hidden">
                Confirm purchase
              </h3>
              {confirmingPurchase ? (
                <div className="stack">
                  <p>Buy {selections.quantity} ticket(s)? This can't be undone.</p>
                  <div className="row">
                    <button className="btn btn--primary" onClick={finalizePurchase}>
                      Yes, buy
                    </button>
                    <button className="btn btn--ghost" onClick={() => setConfirmingPurchase(false)}>
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  type="button"
                  disabled={!interactive || !canBuy}
                  className={`kiosk__btn kiosk__btn--buy ${shakingControl === "buy_ticket" ? "kiosk__btn--shake" : ""}`}
                  onClick={attemptBuy}
                >
                  BUY TICKET
                </button>
              )}
            </section>
          )}
        </div>
      )}

      {interactive && !outcome && (
        <footer className="kiosk__footer">
          <button type="button" className="btn btn--ghost" onClick={requestAssistance}>
            Ask staff for help
          </button>
          <span className="kiosk__error-count" aria-live="polite">
            Errors so far: {errors}
          </span>
        </footer>
      )}
    </div>
  );
}
