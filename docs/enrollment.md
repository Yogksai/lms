# Enrollment and access — stage 5

The backend and React screens support enrollment, free previews, access requests,
assigned-teacher approval, expiring grants and revocation. Migration `0005` adds
`enrollments`, `access_requests` and `access_grants`; existing courses/users are not
automatically enrolled or granted learner access. Payments remain a later stage.

## Rules

Enrollment is a saved relationship between an active account and a published course.
It adds the course to My courses but does not unlock later modules. Active accounts
of any role can learn; a teacher has automatic full access only to assigned courses.

Every course/module/lesson read retains publication and parent/child checks. An
authenticated session with no active learner access gets `403` for a later-module
lesson. Missing/mismatched/unpublished content returns `404`. The first module,
determined by lowest current position, is free even to guests. Public outline DTOs
retain `is_preview` as a free-preview flag; personalized full access comes from the
separate private access endpoint, not a client-provided query parameter.

For a published course, full access can come from independent reasons:

- Current active admin role.
- Current teacher role plus a course assignment.
- Active enrollment plus an unrevoked, unexpired request-approval grant.
- Active enrollment plus an unrevoked, unexpired independent admin grant.

Any remaining reason suffices. Revoking an approval does not revoke an admin grant,
and a role/assignment change does not remove a previously issued learner grant.
Teachers may revoke approval grants only for their assigned courses; only admins
can issue or revoke admin-source grants. Admins can manage all courses.

Approval/admin grants default to **90 days**, selectable from **1–365 days**. This
is an explicit project default, not an externally mandated duration or payment
policy. Duration starts at the grant instant, in UTC, using 24-hour days. Equality
with `expires_at` already means expired. Future payment grants need a separate
source and their own rules; no paid access or payment buttons are fabricated now.

Grant expiry is checked on every protected read. There is no expiry worker and
no cached Redis permission. Expired records remain history. An approver's later
demotion does not retroactively invalidate an already issued grant.

## Request and enrollment lifecycle

1. Enroll in a published course. Repeating enrollment is idempotent.
2. Request full access with an optional message of at most 2000 characters. The
   student cannot choose source, approver, status, recipient or duration.
3. One pending request per course/account is enforced by a partial unique index.
   Repeating a pending request returns the existing state; it does not duplicate
   or modify the original message.
4. An assigned teacher/admin approves with a duration or rejects with an optional
   decision note of at most 1000 characters. Approval requires a published course,
   active recipient and active enrollment. Grant creation and request decision
   share one transaction. A second decision gets `409`.
5. Students can cancel only their own pending request. A rejected/cancelled request
   or expired/revoked access can be followed by a new request. Already active full
   access prevents a new request, except that an existing pending request remains
   pending if an independent admin grant was issued afterward.
6. Leaving cancels pending requests and revokes all learner grants for that course
   atomically. History remains; repeating leave is idempotent for an existing course.
   Re-enrollment does not restore old grants. Staff-role access is independent of
   enrollment and is not removed by leaving.

Course row locks serialize enrollment, requests, decisions, revocation, assignment
changes and course-authoring writes. Authority is checked against current database
roles/assignments after the access-management write lock is acquired. A queued
approval following cancellation/leave sees the new state rather than granting
stale access. Requests already authorized before expiry/revocation may finish.

## API

All endpoints below require a Bearer token. Private responses use `no-store` and
`Vary: Authorization`. Lesson reads optionally accept Bearer authentication; a
missing header allows guest preview, but an invalid supplied header/token receives
`401`, not a silent guest fallback. Student identity always comes from the session.
Input DTOs reject extra fields. Paginated endpoints support `limit=1..100`, `offset>=0`.

| Endpoint | Behavior/body |
| --- | --- |
| `GET /v1/me/courses` | Active enrollments, course metadata, publication availability |
| `GET /v1/courses/{id}/access` | Own enrollment, effective full access/reasons/expiry, latest request, latest 50 grants |
| `POST /v1/courses/{id}/enrollment` | Idempotent enroll; returns access state |
| `DELETE /v1/courses/{id}/enrollment` | Leave, cancel pending requests and revoke learner grants (`204`) |
| `POST /v1/courses/{id}/access-requests` | Optional `message`; returns access state |
| `DELETE /v1/courses/{id}/access-requests/{request_id}` | Cancel own pending request; returns access state |
| `GET /v1/access/courses/{id}/requests` | Teacher/admin queue; `status=pending` default, or approved/rejected/cancelled/all |
| `PUT /v1/access/courses/{id}/requests/{request_id}` | `decision`: approve/reject; `duration_days` default 90; optional `note`; returns `204` |
| `GET /v1/access/courses/{id}/grants` | Teacher/admin ledger; `active_only=true` default; false includes history |
| `POST /v1/access/courses/{id}/grants` | Admin only: `user_id`, `duration_days`; independent grant (`201`) |
| `DELETE /v1/access/courses/{id}/grants/{grant_id}` | Scoped source-aware revocation, idempotent (`204`) |

The access endpoint reports only the caller's request/grants. Effective grant access
is calculated over all qualifying records, not limited to the latest 50 history rows.
`expires_at` is the latest qualifying grant expiry, or null for role-based/no full
access. `reasons` lists full-access reasons, not the separately free first module.

An enrolled course that becomes draft/archived remains in My courses with
`available=false`, but learner content stays blocked. Grants retain their original
expiry while unavailable; publishing again does not extend them. The private
enrollment list may show its current course metadata, but never draft lesson bodies.

The grant ledger's `active` means unrevoked/unexpired with active user/enrollment;
publication must still be checked before reading content. Requests/grants from a
different course get `404`, even if the acting teacher manages both courses.

## Frontend and verification limits

My courses is at `/my-courses`. A course page offers enrollment/request/cancel,
decision notes, effective expiry, grant history and leaving. Closed lesson pages
offer the same flow. The authoring course's **Заявки и доступ** link opens teacher
management at `/access/courses/{id}`. Admin-only controls issue independent grants.

Protected lesson queries use account-specific private keys, reset after access
mutations, and clear on logout. They revalidate on mount/focus and every 30 seconds
while open; local expiry labels update each second. Already downloaded material
cannot be reclaimed; other tabs/devices update at their next revalidation. YouTube
URLs are not DRM-protected—authorization protects API disclosure, not playback of
an already known public YouTube URL. Tokens remain in memory, so use independent
tabs/logins to test simultaneous student/teacher sessions.

Only unit tests, offline migration SQL, static checks and the frontend build were
run for this stage. Docker, live PostgreSQL migration/locking/constraint tests,
browser layout checks and live API integration are intentionally left manual.

## Manual test sequence

1. From the repository root run `make up`, then:

   ```sh
   docker --context desktop-linux compose exec api alembic current
   docker --context desktop-linux compose exec api alembic check
   ```

   Expect head `0005` and no schema differences. Seed demo courses if needed using
   `python -m bin.seed_courses` inside the API container. See `authoring.md` for
   first-admin bootstrap and teacher assignment. Test downgrade/upgrade only in a
   disposable database; no live database migration was performed by this change.
2. Prepare a published course with two modules, two teachers (A assigned to this
   course, B not assigned), an admin, and two students. Use separate tabs/login
   sessions; save real course/module/lesson IDs instead of assuming numeric values.
3. Logged out: first-module lesson is `200`, later lesson `403`, foreign hierarchy
   `404`. Supplying an invalid Bearer token or Basic header must give `401`.
4. As student S, enroll. Repeat enrollment: only one active row. It appears in My
   courses, but a later lesson still gives `403`. A client `full_access=true` query
   parameter must not unlock it.
5. Send a request, repeat it, and inspect the pending queue: one pending request.
   Attempts to submit `source`, `user_id` or `duration_days` in the request DTO get
   `422`. A second student cannot cancel or read S's request history.
6. Teacher B cannot list/approve/revoke access for this course (`404`); a student
   calling management endpoints receives `403` for an existing course. Teacher A
   approves S's request with 30 days. Check the stored grant, approving user/time,
   request status, displayed expiry and later-module lesson `200`. Approval of a
   different course's request ID must be `404`.
7. Reload/refresh the student access panel or wait for its revalidation. Test a
   rejection with a note, cancellation, and resubmission after either. Re-deciding
   an approved request must be `409` and must not create another approval grant.
8. Admin issues an independent admin grant for S. Revoke only the teacher approval:
   S must keep full access from the admin grant. Teacher A cannot revoke that admin
   grant (`403`). Admin revokes the final grant: later lessons become `403`; preview
   stays `200`. Test expiry separately rather than assuming revocation tests expiry.
9. For a fast expiry test, use only a disposable/local test database and a known
   test grant ID. Move its timestamps so the expiry is past but still later than
   creation, preserving the database constraint. Example, replacing the ID:

   ```sql
   UPDATE access_grants
   SET created_at = now() - interval '2 days',
       expires_at = now() - interval '1 minute'
   WHERE id = 123;
   ```

   Ensure no other full-access reason remains. The next lesson request must be
   `403`, the access state false, and history visible. This SQL is a manual fixture
   change, not an application endpoint. Never use an arbitrary ID in production.
10. Leave with a pending request and grants: they must cancel/revoke. Re-enroll:
    preview only, old grants not restored. Leaving again is harmless. Staff access
    still works for an assigned teacher/admin because it has an independent reason.
11. Archive/return the course to draft while S has an active grant. Public content
    must be `404`; My courses shows unavailable. New enroll/request/approval is
    blocked. Publish again: an unexpired, unrevoked grant works without renewal.
12. Remove teacher assignment/demote teacher while the queue is open: the next
    management request must fail. Disable S using the existing local test mechanism:
    authentication must fail regardless of grants. No disabling UI is added here.
13. On a disposable database, send approval/approval, approval/cancellation and
    approval/leave concurrently. Verify one terminal decision, no partial grant,
    and no access left after leaving. These test real PostgreSQL row locks and are
    not covered by mock transaction tests.
14. Check keyboard/mobile layout, validation, pending/error states, pagination,
    request-history filters and logout during a delayed save. After logout, no
    previous student's protected lesson body should remain in the next identity's
    cache. Stop/restart the API to check error handling without creating fake grants.

TODO: add request/enrollment rate limits and notification delivery before deployment.
TODO: implement payment-issued access separately with explicit refund/expiry rules.
