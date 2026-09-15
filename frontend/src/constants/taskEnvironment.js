/**
 * Phase 3 shared shapes and demo metadata.
 *
 * The project is plain JavaScript, not TypeScript (an established Phase 1
 * decision — see docs/SETUP.md) — introducing a TypeScript toolchain mid-
 * project would be exactly the "replace working infrastructure
 * unnecessarily" this phase's own instructions warn against. These JSDoc
 * typedefs give the same documentation/autocomplete value without that
 * churn; every field name matches the backend's TaskDescriptor/
 * EnvironmentDescriptor response exactly.
 *
 * @typedef {Object} TaskControl
 * @property {string} id
 * @property {string} type
 * @property {string} label
 * @property {string} interaction_type
 *
 * @typedef {Object} TaskStep
 * @property {string} id
 * @property {number} order
 * @property {string} name
 * @property {string} description
 * @property {boolean} required
 * @property {TaskControl[]} controls
 *
 * @typedef {Object} TaskDescriptor
 * @property {string} task_id
 * @property {string} name
 * @property {string} description
 * @property {TaskStep[]} steps
 * @property {TaskControl[]} controls
 * @property {number|null} time_limit_seconds
 *
 * @typedef {Object} ScreenDescriptor
 * @property {number} width
 * @property {number} height
 * @property {number} [dpi]
 *
 * @typedef {Object} EnvironmentControl
 * @property {string} id
 * @property {number} [x]
 * @property {number} [y]
 * @property {number} width
 * @property {number} height
 * @property {string} label
 * @property {string} type
 *
 * @typedef {Object} ContrastDescriptor
 * @property {string} level
 * @property {string} [background]
 * @property {string} [foreground]
 *
 * @typedef {Object} EnvironmentDescriptor
 * @property {string} environment_id
 * @property {string} environment_type
 * @property {ScreenDescriptor} screen
 * @property {EnvironmentControl[]} controls
 * @property {ContrastDescriptor|number} contrast
 * @property {string} noise_level
 * @property {string} [lighting]
 *
 * @typedef {Object} BarrierEvidence
 * @property {unknown} [controls]
 * @property {unknown} [threshold]
 * @property {number} [contrast_ratio]
 * @property {number} [choice_count]
 * @property {unknown} [alerts]
 * @property {string} [ability_value]
 *
 * @typedef {Object} Barrier
 * @property {string} barrier_type
 * @property {string} ability_dimension
 * @property {number} severity
 * @property {number} confidence
 * @property {string} title
 * @property {string} description
 * @property {BarrierEvidence} evidence
 *
 * @typedef {Object} BarrierDetectionResponse
 * @property {number} user_id
 * @property {string} task_id
 * @property {string} environment_id
 * @property {Barrier[]} barriers
 *
 * @typedef {Object} AdaptationCandidate
 * @property {string} adaptation_id
 * @property {number} score
 *
 * @typedef {Object} ApprovedAdaptation
 * @property {string} adaptation_id
 * @property {string} name
 * @property {number} score
 * @property {string[]} barrier_types
 * @property {string} reason
 * @property {"ai"|"deterministic_fallback"} source
 * @property {boolean} validated
 * @property {boolean} requires_confirmation
 * @property {string|null} ai_error
 *
 * @typedef {Object} AdaptationRecommendationResponse
 * @property {Barrier[]} barriers
 * @property {AdaptationCandidate[]} candidates
 * @property {ApprovedAdaptation|null} selected_adaptation
 * @property {string} [reason]
 */

export const DEMO_TASK = {
  taskId: "purchase_ticket",
  title: "Purchase a Ticket",
  description: "Complete a ticket purchase using a public kiosk.",
};

export const DEMO_ENVIRONMENT = {
  environmentId: "ticket_kiosk_default",
  title: "Ticket Kiosk — Default",
  description: "Simulated public ticket kiosk used for the AbilityOS hackathon demonstration.",
};

/** Normalizes `contrast` — the backend returns an object ({level,
 * background, foreground}) for this phase's own fixture, but a plain
 * number for the pre-existing kiosk_standard fixture the real barrier
 * engine reads. Display code should go through this rather than assuming
 * either shape. */
export function contrastLabel(contrast) {
  if (contrast == null) return "unknown";
  if (typeof contrast === "number") return contrast.toFixed(2);
  return contrast.level || "unknown";
}
