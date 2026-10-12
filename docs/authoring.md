# Teacher permissions and authoring

Stage 5 extends learner permissions with enrollment/access grants; see `enrollment.md`.
The current migration head is `0005`. The stage 4 migration itself remains `0004`.

Stage 4 includes backend authorization and React authoring screens. Migration
`0004` adds roles, teacher assignments, archive state, and course revisions. Existing
users become students; existing published courses keep their publication state.
No account is automatically promoted. Existing courses remain editable by admins
until teachers are assigned.

## Permissions and lifecycle

- Students use public course reads, preview lessons and full lessons with stage 5 grants. Authentication alone
  never grants authoring or later-module access.
- Teachers see/edit only assigned courses, including their full lesson bodies.
  Multiple assigned teachers collaborate with equal authoring rights. Teachers can
  create courses; their new draft is automatically assigned to themselves.
- Admins author all courses, assign/revoke teachers and manage account roles.
  Admin-created drafts have no automatic teacher assignment.
- Role/active status comes from PostgreSQL, not JWT role claims. Unassigned course
  access returns `404`; a student calling authoring/admin APIs receives `403`.
  Missing/invalid authentication receives `401`.
- Only drafts permit content/metadata edits, ordering and module/lesson deletion.
  Returning a published course to draft removes it from public reads immediately.
  This version has no separate published snapshot while editing a draft.
- Publishing requires at least one module and one valid lesson in every module.
  Lessons require a nonempty text summary and validated HTTPS YouTube URL.
- Archive hides the whole course but preserves its content and assignments.
  An archived course must return to draft before publication. There is no course
  hard-delete endpoint. Deleting a draft module also deletes its lessons; these
  child deletions are permanent and the UI requests confirmation.
- Assignments can change in any lifecycle state. Only active teachers can be newly
  assigned. Demoted/inactive teachers lose authoring rights even if an assignment
  remains recorded. If restored to active teacher, those recorded assignments apply
  again; revoke them explicitly if that is not intended.
- Admins cannot change their own role. Role changes/assignments/bootstrap serialize
  on a PostgreSQL transaction advisory lock. Role changes recheck the acting admin
  after acquiring that lock, preventing two concurrent demotions from removing all
  active admins. External SQL/account disabling is outside that guarantee.
- Requests already authorized when a role changes may finish. Course row locks
  serialize writes and assignment revocation. A writer waiting behind revocation
  rechecks the assignment before changing content.

## API

Every endpoint below requires a Bearer access token and uses `Cache-Control: no-store`
on successful responses. Request DTOs reject unknown fields. User DTOs never expose
password hashes. Admin user search is a literal case-insensitive email substring.
Both private list endpoints are paginated (`limit=1..100`, `offset>=0`).

All mutations on an existing course require `?revision=N`, taken from the latest
editor response. Successful mutations return the complete editor course with an
incremented revision. A stale revision, duplicate slug or editing a non-draft
returns `409`; reload and reconcile edits instead of automatically retrying.

| Endpoint | Purpose / body |
| --- | --- |
| `GET /v1/authoring/courses` | Assigned courses for teacher; all courses for admin |
| `POST /v1/authoring/courses` | Create draft: `slug`, `title`, `description` (`201`) |
| `GET /v1/authoring/courses/{course_id}` | Full modules, lessons, teachers, status, revision |
| `PUT /v1/authoring/courses/{course_id}` | Replace metadata: `slug`, `title`, `description` |
| `PUT /v1/authoring/courses/{course_id}/status` | `status`: `draft`, `published`, `archived` |
| `POST /v1/authoring/courses/{course_id}/modules` | Append module: `title`, `description` (`201`) |
| `PUT /v1/authoring/courses/{course_id}/modules/{module_id}` | Replace module metadata |
| `DELETE /v1/authoring/courses/{course_id}/modules/{module_id}` | Delete module and its lessons |
| `PUT /v1/authoring/courses/{course_id}/modules/order` | `ids`: complete ordered module ID list |
| `POST /v1/authoring/courses/{course_id}/modules/{module_id}/lessons` | Append lesson: `title`, `summary`, `video_url` (`201`) |
| `PUT /v1/authoring/courses/{course_id}/modules/{module_id}/lessons/{lesson_id}` | Replace lesson content |
| `DELETE /v1/authoring/courses/{course_id}/modules/{module_id}/lessons/{lesson_id}` | Delete lesson |
| `PUT /v1/authoring/courses/{course_id}/modules/{module_id}/lessons/order` | `ids`: complete ordered lesson ID list |
| `POST /v1/authoring/courses/{course_id}/teachers` | Admin only: `user_id` |
| `DELETE /v1/authoring/courses/{course_id}/teachers/{user_id}` | Admin only: revoke assignment |
| `GET /v1/admin/users?search=email` | Admin-only user lookup: IDs, public profiles, roles |
| `PUT /v1/admin/users/{user_id}/role` | Admin only: `role`: `student`, `teacher`, `admin` |

New modules/lessons append at the highest sibling position + 1. Reorder requires
the exact sibling set, rejects duplicates/foreign IDs, and renumbers densely from
1. Two flushes move positions to temporary positive slots before assigning their
final positions, avoiding immediate unique-constraint collisions. Authoring limits
new children to 1000 per parent. Module/lesson IDs must belong to their URL parents.
Use cases own transactions; repositories flush without committing.

## Manual verification

Docker, live PostgreSQL migration/constraint/concurrency checks, and browser checks
are intentionally manual. The unit suites use mocks and offline migration SQL;
they are not evidence that the live migration or PostgreSQL locks were executed.

1. From the repository root rebuild/start with `make up`. Check:

   ```sh
   docker --context desktop-linux compose exec api alembic current
   docker --context desktop-linux compose exec api alembic check
   ```

   Expect `0005` and no schema differences. Verify upgrade/downgrade only in a
   disposable database, not the main LMS database.
2. Register separate admin, teacher A, teacher B and student accounts through the
   normal UI/API. Bootstrap only the initial admin, using its real registered email:

   ```sh
   docker --context desktop-linux compose exec api python -m bin.bootstrap_admin admin@example.com
   ```

   Substitute the actual email. This refuses missing/inactive accounts and refuses
   to run while an active admin exists. Log out/in after promotion so the header
   updates. No known default admin credentials are supplied.
3. As admin, open `/admin/users`, find teacher A/B and set their roles to teacher.
   Check that changing the admin's own role is disabled and the API returns `409`.
   As a student, direct calls to admin/authoring endpoints must return `403`.
4. As teacher A, create a draft course at `/authoring/courses`. It must be assigned
   to A. Add two modules and two lessons per module. Use valid YouTube URLs and
   plain text summaries. Check validation, editing, saved-content preview and that
   strings such as `<script>text</script>` display as text, not executable markup.
5. As teacher B, list courses and request A's course directly: A's draft must not
   appear and its editor URL must return `404`. As admin, assign B to A's course by
   B's ID, verify access, revoke B and verify subsequent writes return `404`.
6. Swap module positions and lesson positions, then refresh and inspect public
   ordering after publishing. In `/docs`, send missing/duplicate/foreign IDs in
   reorder bodies: expect `422`. Mismatched module/lesson parents must return `404`.
7. Try publishing a course without modules or with an empty module: expect `422`.
   Complete it, publish and verify public course/preview reads. Content writes on
   a published course must return `409`. Return it to draft and verify public reads
   return `404`. Archive it: content remains in the editor but not public reads.
   Publishing directly from archive must return `409`; restore draft first.
8. Open the same draft in two independently logged-in tabs. Save in one, then save
   using the older revision in the other: expect `409`, no overwritten data and
   unsaved text retained in the form. “Обновить данные” explicitly discards those
   fields after confirmation. Repeat with simultaneous reorder/assignment writes
   to verify real PostgreSQL serialization.
9. Demote teacher A to student. Subsequent authoring API requests must return `403`,
   even using an unexpired access token. Revoke assignments explicitly when they
   should not apply after future re-promotion. For admin concurrency checks, create
   a second admin and send opposing demotion requests concurrently: one admin must
   remain, and the formerly authorized second actor must receive `403` after its
   authority is rechecked.
10. Delete a draft lesson/module after the UI confirmation; verify the child rows
    and public outline disappear. Check desktop/mobile layouts, keyboard operation,
    request errors, role guards, logout during a pending save and direct URLs.

Authoring uses explicit save buttons, not autosave. Refresh/closing warns for dirty
forms; save before internal navigation or browser back, which do not block edits
from being discarded. A page refresh still loses the in-memory login session.
No enrollment grants, quizzes, payments, rich-text HTML, uploads, or authoring audit
log are included in this stage.
