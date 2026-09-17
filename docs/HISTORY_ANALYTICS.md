# Feedback, History & Analytics Integration (Phase 6)

> **Scope note:** builds on Phase 5's session pipeline. Nothing about how
> `InteractionSession`, `Barrier`, `AdaptationResult`, or `Feedback` rows
> are *created* changed in this phase — Phase 6 only reads them back, for
> the authenticated user who owns them.

## 1. Purpose

Make a real user's own completed AbilityOS sessions visible to them: what
happened, what was detected, what was applied, and whether they gave
feedback — without ever exposing another user's data, and without
recomputing anything from data that has since changed.

## 2. History architecture

```
Authenticated User
       ↓
GET /api/users/{id}/sessions/   (Phase 6, new — list, shaped for cards)
       ↓
HistoryPage.jsx renders cards
       ↓
"View Details" → GET /api/interactions/{id}/summary/   (Phase 1/7, unmodified — full detail)
       ↓
SessionDetail (inline, expandable — no new route/page)
```

No new model. Both endpoints read `InteractionSession` and its existing
related rows (`Barrier` via `barriers`, `AdaptationResult` via
`adaptation_results`, `Feedback` via `feedback`) — the same relations
`api.services.orchestrator.InteractionOrchestrator.summary()` already
used for the developer/explanation panel since Phase 7.

## 3. Session ownership

`GET /api/users/{id}/sessions/` (`api.views.UserSessionsView`) is
`IsAuthenticated` and calls the existing
`users.services.ownership.assert_owner(request, user_id, ...)` before
touching the database — identical to every other `/api/users/{id}/...`
endpoint since Phase 1. The queryset itself is always
`InteractionSession.objects.filter(user=user)`, never `.all()`.

Session *detail* reuses `GET /api/interactions/{id}/summary/`
(`InteractionSummaryView`), unmodified since Phase 1/8 — it already
resolves the session by id and calls `assert_owner(request,
session.user_id, ...)`. Nothing new was needed here; Phase 6 only added a
frontend consumer (`HistoryPage.jsx`'s expandable detail) for an endpoint
that was already fully ownership-enforced.

## 4. Analytics ownership — a deliberate architectural decision

**`GET /api/analytics/sessions/` was NOT modified.** It stays `AllowAny`
and globally unfiltered, exactly as before this phase. This needs
explaining, because the Phase 0 audit (and this phase's own brief) named
it as the endpoint needing "user filtering."

Inspection (this phase's own section 1 mandate: "use the actual
repository as the source of truth, not an assumed architecture") found
that endpoint's actual, sole consumer is `AnalyticsPage.jsx` — Phase 7's
"AbilityOS Outcome Analytics" page, reached from the Header's "Analytics"
nav button. Every other card on that page (`total_interactions`,
`completion_rate`, adaptation effectiveness, barrier outcomes,
before/after) is an intentionally **global, cross-user aggregate** — the
demo's own "look how much AbilityOS helps, in aggregate" story, built to
work for an anonymous visitor with no login at all. Teaching just the
"Recent sessions" table on that same page to suddenly go
authenticated-user-only would have made `AnalyticsPage` internally
inconsistent (mostly-global stats next to a personal-only table) for the
one group of visitors — authenticated account holders — for whom it now
matters most, while adding no real security value: nothing this project
built or exercises ever routed a personal-history need through that
endpoint's shape (`task_name`/`experience_mode`/`status`/`ease_rating` —
no barrier or adaptation detail at all).

Instead, Phase 6 added a **new**, separately-owned endpoint
(`GET /api/users/{id}/sessions/`, §3) purpose-built for personal history,
following the exact `/api/users/{id}/...` convention Phase 3 already
established for owned resources (`profile-suggestions/`,
`profile-selections/`). `GET /api/analytics/sessions/` keeps serving
`AnalyticsPage.jsx` unchanged for every caller, anonymous or
authenticated — verified by
`GlobalAnalyticsRegressionTests.test_analytics_sessions_endpoint_stays_global_even_when_authenticated`
(`backend/api/test_history_analytics.py`), which exists specifically to
catch a future accidental regression of this decision.

## 5. Feedback ownership

Unchanged — `InteractionFeedbackView` already required
`assert_owner(request, session.user_id, ...)` (Phase 1/8). History only
*displays* what's already there (`feedback_submitted` boolean and
`ease_rating` in the list; the full `Feedback` row — ease, helpfulness,
optional comment — in the expanded detail, sourced from the same
`summary()` payload). No feedback create/update path was added or changed
in this phase.

## 6. API endpoints

| Endpoint | Method | Auth | Purpose | Status |
|---|---|---|---|---|
| `/api/users/{id}/sessions/` | GET | `IsAuthenticated` + owner-or-staff | History list, newest first | **New (Phase 6)** |
| `/api/interactions/{id}/summary/` | GET | owner-or-staff (anonymous-safe) | Session detail (History's "View Details") | Unmodified (Phase 1/7) |
| `/api/analytics/sessions/` | GET | `AllowAny`, global | `AnalyticsPage.jsx`'s demo-wide table | **Unmodified — deliberately** (§4) |

## 7. History data source

Every field on a history card is read directly, never invented or
recomputed:

- `task_name` — `session.task.name`
- `environment_name` — `session.environment.name` (or `null` if the
  session never reached environment analysis)
- `status` — `InteractionSession.status` (the real state machine value:
  `started`/`analyzed`/`adapted`/`in_progress`/`completed`/`abandoned`/`failed`
  — `HistoryPage.jsx`'s `STATUS_LABELS` only relabels these for display,
  never introduces a new value)
- `barriers_detected` — count of that session's own `Barrier` rows
- `adaptations_applied` — count of that session's own `AdaptationResult`
  rows with `applied=True`
- `feedback_submitted` / `ease_rating` — presence and content of the
  session's `Feedback` row (`hasattr(session, "feedback")`, the same
  pattern `analytics/views.py::sessions()` already used)

## 8. Profile snapshot behaviour

Unchanged from Phase 5 — `InteractionSession.ability_profile_snapshot` is
written once, at `InteractionOrchestrator.start()`, and never touched
again. `SessionDetail` (`HistoryPage.jsx`) renders
`summary.ability_profile_snapshot` through the existing
`summarizeProfile()` formatter — the exact same "AbilityOS Understands"
language used everywhere else in the app — **never** the user's current
`AbilityProfile`. Proved directly, not just asserted, by
`ProfileSnapshotHistoryTests.test_session_summary_keeps_the_original_snapshot_after_profile_changes`:
a session started with `vision: large-text-needed`, the user's live
profile is then changed to `vision: typical`, and the session's own
summary still reports `large-text-needed`.

> Historical results are read from stored session data and are not
> recomputed using the user's current AbilityProfile.

## 9. Sorting / filtering

Newest-first, via `InteractionSession.objects.filter(user=user)...order_by("-created_at")`
— backend ordering, not a frontend sort (section 15). No filter UI was
added (all-time/recent/completed/incomplete): the current scale (a
hackathon prototype, one task, a handful of sessions per account) doesn't
need one yet, and inventing filter state for data this small would be
scope beyond "history + analytics integration." `MAX_RESULTS = 50` caps
the list defensively (documented limitation, §14) rather than building a
pagination framework (section 16).

## 10. Empty / loading / error states

- **Loading:** `HistoryPage.jsx` shows "Loading your interaction
  history…" (never "No sessions found" while the request is in flight —
  a dedicated `phase` state machine, same pattern as `DashboardPage.jsx`/
  `SuggestedProfilesPage.jsx`, makes this the default rather than
  something to remember to guard).
- **Empty:** "No AbilityOS sessions yet." + "Start an experience to see
  your interactions here." + a **Start Experience** button
  (`onStartExperience`, reusing `handleStartExperienceFromDashboard`) —
  not treated as an error.
- **Error:** a distinct message for an expired/invalid session (401/403)
  vs. any other failure (network/500), with **Retry**, mirroring
  `DashboardPage.jsx`'s existing error block. Detail-fetch errors are
  scoped to just that one expanded card, not the whole page.

## 11. Security model

The single rule: **ownership is enforced server-side, on every read.**
`assert_owner()` is the one shared mechanism (Phase 1), applied
identically to the list endpoint and (already) the detail endpoint. A
query-parameter or URL manipulation cannot bypass it — the view never
reads an identity from anywhere but the URL's own `user_id`/`session_id`
argument plus `request.user`; there is no code path that trusts a
frontend-asserted identity. Verified directly:

- `HistoryOwnershipTests` — two real accounts, Alice and Bob: Alice's
  history contains only her own session; Bob's contains only his; Alice
  cannot list Bob's history via his URL (403); a `?user_id=<bob>` query
  parameter on *Alice's own* URL does nothing (the view never reads it);
  Alice cannot retrieve, modify, or submit feedback for Bob's session
  (403 in all three cases).
- `UserHistoryListTests.test_history_reflects_actual_session_count_not_all_sessions_in_db`
  — guards specifically against an unfiltered queryset slipping in.

Live (Playwright): User B, with zero sessions of their own, sees the
empty state and never sees User A's completed ticket-purchase session
anywhere on the page.

## 12. Demo compatibility

No demo-facing behaviour changed. `AnalyticsPage.jsx` / `MetricsPanel`-
adjacent global endpoints are untouched (§4). `Header.jsx`'s new
"Dashboard"/"History" buttons are rendered only when `onGoToDashboard`/
`onViewHistory` props are passed, and `App.jsx` only passes them for
`entryMode === "account"` — for the demo path these are `undefined`, so
`Header`'s JSX renders exactly the three buttons it always has
(verified live: nav text is unchanged, byte-for-byte, in demo mode).
The full 9-persona demo flow (Explore → Select → Consent → manual editor
→ Summary → Task & Environment → "Back to Profile Summary") was re-run
live end-to-end with zero console errors.

## 13. Known limitations

- No pagination — `MAX_RESULTS = 50` on the history list is a simple,
  documented cap appropriate for this project's current scale (section
  16's explicit guidance), not a scalability solution. A real production
  deployment with years of session history per user would need real
  pagination.
- No date-range/status filter UI on History, for the same
  current-scale reason (section 14).
- `GET /api/analytics/sessions/` remains global/unfiltered even for an
  authenticated caller — a deliberate choice (§4), not an oversight, but
  worth stating plainly: an authenticated account viewing `AnalyticsPage`
  still sees the same cross-user demo table every anonymous visitor sees,
  not a personalized one. `HistoryPage.jsx` is the personalized surface.
- Session detail's barrier/adaptation lists show what happened, not why
  in full technical depth (rationale, score breakdown, candidates
  considered) — that richer detail already exists in the same
  `GET /api/interactions/{id}/summary/` payload and could be surfaced
  later; History's own detail view deliberately keeps to the spec's own
  example shape (task / barriers / adaptations / outcome / feedback) to
  avoid re-exposing the full developer/explanation panel a second time.

## 14. Phase boundary

Phase 6 is complete. No Phase 7 functionality was implemented.
