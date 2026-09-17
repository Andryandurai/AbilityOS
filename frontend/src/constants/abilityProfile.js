/**
 * Shared Ability Profile vocabulary and copy (Phase 2 section 38).
 *
 * This is the one place that knows both the controlled backend values
 * (which must match backend/abilities/constants.py exactly) and the
 * plain-language question/option/summary copy the UI shows for them —
 * every profile-related screen imports from here instead of re-deriving
 * its own mapping, so "reduced-precision" is translated to "Precise
 * tapping can be difficult" in exactly one place.
 */

// Mirrors backend/abilities/constants.py MODALITY_VALUES. Keep in sync.
export const MODALITY_VALUES = ["visual", "voice", "haptic", "mixed"];

/**
 * One entry per editable dimension (Phase 2 section 8's "Vision / Touch &
 * Hand Control / Information Load / Interaction" style, extended to all
 * ten fields the spec says must be editable). `key` must match a backend
 * dimension key exactly, except `preferred_modality` which is a top-level
 * AbilityProfile field, not a `dimensions` entry.
 */
export const ABILITY_QUESTIONS = [
  {
    key: "vision",
    heading: "Vision",
    question: "How comfortable are you reading small text?",
    options: [
      { value: "typical", label: "Comfortable" },
      { value: "low-contrast-sensitive", label: "I prefer higher contrast" },
      { value: "large-text-needed", label: "I need larger text" },
    ],
  },
  {
    key: "hearing",
    heading: "Hearing",
    question: "How well do audio alerts and sounds work for you?",
    options: [
      { value: "typical", label: "Audio works well for me" },
      { value: "partial", label: "I sometimes miss audio alerts" },
      { value: "relies-on-visual", label: "I rely on visual alerts instead" },
    ],
  },
  {
    key: "dexterity",
    heading: "Touch & Hand Control",
    question: "How precise is touch interaction for you?",
    options: [
      { value: "typical", label: "Normal precision" },
      { value: "reduced-precision", label: "Precise tapping can be difficult" },
      { value: "single-tap-only", label: "I prefer single-tap interactions" },
    ],
  },
  {
    key: "reach",
    heading: "Reach",
    question: "How easily can you reach controls in front of you?",
    options: [
      { value: "full", label: "I can reach everything comfortably" },
      { value: "limited-upper", label: "My upper reach is limited" },
      { value: "seated", label: "I'm usually seated" },
    ],
  },
  {
    key: "mobility",
    heading: "Mobility",
    question: "How easily can you move between steps of a task?",
    options: [
      { value: "typical", label: "I move around easily" },
      { value: "limited", label: "My movement is limited" },
      { value: "stationary", label: "I prefer to stay in one place" },
    ],
  },
  {
    key: "speech",
    heading: "Speech",
    question: "How reliably can you use voice commands?",
    options: [
      { value: "typical", label: "Comfortable using my voice" },
      { value: "limited", label: "Speaking clearly can be difficult" },
      { value: "unavailable", label: "Voice isn't an option for me" },
    ],
  },
  {
    key: "cognition",
    heading: "Information Load",
    question: "How do you prefer choices to be presented?",
    options: [
      { value: "typical", label: "I am comfortable with many choices" },
      { value: "prefers-fewer-choices", label: "I prefer fewer choices" },
      { value: "needs-step-by-step", label: "I prefer one step at a time" },
    ],
  },
  {
    key: "fatigue",
    heading: "Energy",
    question: "How is your energy right now?",
    options: [
      { value: "fresh", label: "Fresh" },
      { value: "moderate", label: "Somewhat tired" },
      { value: "high", label: "Very tired" },
    ],
  },
  {
    key: "reaction_speed",
    heading: "Reaction Speed",
    question: "How quickly can you respond to on-screen prompts?",
    options: [
      { value: "typical", label: "Typical speed" },
      { value: "slower", label: "A bit slower" },
      { value: "needs-extended-time", label: "I need extra time" },
    ],
  },
  {
    key: "interaction_sensitivity",
    heading: "Interaction Style",
    question: "How do you prefer controls to behave?",
    options: [
      { value: "typical", label: "Typical interaction works for me" },
      { value: "high", label: "I prefer stable, well-separated, deliberate interactions" },
    ],
  },
];

export const MODALITY_QUESTION = {
  key: "preferred_modality",
  heading: "Interaction",
  question: "How do you prefer to interact?",
  options: [
    { value: "visual", label: "Visual" },
    { value: "voice", label: "Voice" },
    { value: "haptic", label: "Haptic" },
    { value: "mixed", label: "Mixed" },
  ],
};

/**
 * "What AbilityOS understands" copy (Phase 2 sections 9/37/38). Only
 * non-"no barrier" levels get an entry — a `typical`/baseline dimension
 * has nothing worth telling the person about.
 */
const SUMMARY_COPY = {
  vision: {
    "low-contrast-sensitive": { emoji: "👁", text: "Higher contrast makes text easier to read." },
    "large-text-needed": { emoji: "👁", text: "Larger text helps you read comfortably." },
  },
  hearing: {
    partial: { emoji: "🔊", text: "Visual feedback alongside audio helps." },
    "relies-on-visual": { emoji: "🔊", text: "Visual feedback is preferred over audio." },
  },
  dexterity: {
    "reduced-precision": { emoji: "✋", text: "Precise tapping can be difficult." },
    "single-tap-only": { emoji: "✋", text: "Single-tap interactions work best." },
  },
  reach: {
    "limited-upper": { emoji: "🙌", text: "Reaching toward distant controls can be difficult." },
    seated: { emoji: "🙌", text: "Seated interaction works best for you." },
  },
  mobility: {
    limited: { emoji: "🚶", text: "Important controls should stay within a comfortable interaction area." },
    stationary: { emoji: "🚶", text: "You prefer to complete tasks from one spot." },
  },
  speech: {
    limited: { emoji: "🗣", text: "Non-voice input methods work best." },
    unavailable: { emoji: "🗣", text: "Voice input isn't used." },
  },
  cognition: {
    "prefers-fewer-choices": { emoji: "🧠", text: "Fewer choices help you process information." },
    "needs-step-by-step": { emoji: "🧠", text: "One step at a time works best for you." },
  },
  fatigue: {
    moderate: { emoji: "🔋", text: "A lighter interaction helps when energy is moderate." },
    high: { emoji: "🔋", text: "A simpler interaction helps when energy is low." },
  },
  reaction_speed: {
    slower: { emoji: "⏱", text: "A little extra time helps." },
    "needs-extended-time": { emoji: "⏱", text: "Extended time before actions time out helps." },
  },
  interaction_sensitivity: {
    high: { emoji: "🎚", text: "Stable, clearly separated, deliberate interactions work best for you." },
  },
};

const MODALITY_COPY = {
  visual: { emoji: "🎯", text: "Visual interaction is preferred." },
  voice: { emoji: "🎯", text: "Voice interaction is preferred." },
  haptic: { emoji: "🎯", text: "Haptic feedback is preferred." },
  mixed: { emoji: "🎯", text: "A mix of visual and haptic feedback is preferred." },
};

/**
 * Turns a raw AbilityProfile (as returned by GET .../ability-profile/) into
 * the "AbilityOS understands" list of {emoji, text} cards — the single
 * transformation every summary/card view in the app uses (Phase 2 section
 * 38: "do not duplicate business logic unnecessarily").
 */
export function summarizeProfile(profile) {
  if (!profile) return [];
  const entries = [];
  for (const [key, dim] of Object.entries(profile.dimensions || {})) {
    const copy = SUMMARY_COPY[key]?.[dim.level];
    if (copy) entries.push(copy);
  }
  const modalityCopy = MODALITY_COPY[profile.preferred_modality];
  if (modalityCopy) entries.push(modalityCopy);
  return entries;
}

/** Short bullet-point version for the demo-user selector cards. */
export function summarizeProfileAsBullets(profile) {
  return summarizeProfile(profile).map((entry) => entry.text);
}

/**
 * Phase 4 (Personalized Dashboard) section 12: whether any dimension has
 * moved away from its baseline level -- i.e. whether the person has
 * actually set up their profile yet. Deliberately ignores
 * preferred_modality: unlike a dimension's baseline level, a fresh
 * AbilityProfile's default modality ("visual") already has its own
 * SUMMARY_COPY entry, so summarizeProfile() alone is never empty and can't
 * be used to detect "never set up."
 */
export function hasCustomizedDimensions(profile) {
  if (!profile) return false;
  return Object.entries(profile.dimensions || {}).some(([key, dim]) => Boolean(SUMMARY_COPY[key]?.[dim.level]));
}

export function questionForKey(key) {
  return ABILITY_QUESTIONS.find((q) => q.key === key);
}
