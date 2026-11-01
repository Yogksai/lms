# Stage 6: quizzes and progress

## Rules

- One quiz per module; default: 10 random questions, 70% passing threshold, 600 seconds.
- Teachers can configure 1–100 questions, 1–100% passing score and 60–7200 seconds.
- Each question has exactly A/B/C/D (one correct choice), an explanation, and a lesson
  from the same module. The bank allows up to 1000 questions, including archived ones.
- Only admins and assigned teachers can read the bank. Writes require a draft course
  and the current quiz `revision` (initially `0`). Unassigned teachers cannot access it.
- Save a disabled quiz first, add questions, then enable it. Enabling requires enough
  active questions. Archiving a question removes it from future samples, not old attempts.
- Every attempt stores an immutable snapshot of selected questions, options, correct
  answers, explanations, lesson titles, passing threshold, quiz revision and deadline.
  Editing the bank/configuration does not change existing attempts or historical passes.
- The learner API never exposes correct answers/explanations before submission. A result
  contains only questions actually selected for that learner's own attempt.
- There are 5 new attempts per module/account/calendar day, reset at midnight
  `Asia/Almaty` (UTC timestamps are stored). Started/expired attempts consume the limit.
  Resuming an existing open attempt does not. Defaults are configurable in `.env`.
- Authenticated users may attempt the first preview module without enrollment. Other
  modules require current full access, admin rights or the course's teacher assignment.
  Permission is checked again for start/read/submit/lesson marking, never cached in Redis.
- One open attempt per account/module. PostgreSQL course-row locks serialize starting,
  grading, authoring and access mutations; a partial unique index provides a second guard.
- Answers must reference this attempt's questions. Omitted answers count as wrong.
  Passing compares the exact fraction, not a rounded percentage; the displayed integer
  score is rounded down. A submitted attempt cannot be changed. Repeating the same
  submission returns the result without grading or notifying twice.
- The server expires attempts when `now >= deadline`. GET/info/submit check deadlines;
  there is no periodic expiry worker. History may show an old open status until checked.
  Basic expiry returns an expired attempt (HTTP 200) without correct answers or grading.
- Answer drafts exist only in browser memory. No autosave, offline restoration, automatic
  submission, pause, per-question timing or accommodations in this stage. The countdown
  is advisory; changing the browser clock cannot extend the server deadline.

## Progress and review

Lesson completion is an explicit, reversible, idempotent marker, not evidence that a
video was watched. Reading progress and quiz progress are separate. A course completes
when every current module has an enabled quiz and a historical passing attempt.
Reading all lessons alone does not complete a course. Empty courses never complete.
If curriculum/modules change, progress is recalculated against the current curriculum.

Wrong/unanswered questions are grouped by their linked lesson, most mistakes first.
This is a simple review suggestion, not a diagnosis or an AI recommendation. Deleted
lessons retain snapshot titles/explanations but lose clickable review links. Deleted
modules retain attempt snapshots (course deletion/account deletion removes their data).
Reading history from a removed module requires current full course access.
An unavailable/unpublished course cannot be used for learner attempts or progress.

## APIs

All paths below are under `/v1`, require Bearer authentication, and return private
`Cache-Control: no-store` responses. Ownership comes from the authenticated account.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/authoring/courses/{c}/modules/{m}/quiz` | Bank/configuration, paginated |
| PUT | same + `?revision={r}` | Configure quiz |
| POST | same + `/questions?revision={r}` | Add question |
| PUT | same + `/questions/{q}?revision={r}` | Edit question |
| DELETE | same + `/questions/{q}?revision={r}` | Archive question |
| GET | `/courses/{c}/modules/{m}/quiz` | Rules, daily balance, open attempt |
| POST | `/courses/{c}/modules/{m}/attempts` | Start or resume own attempt |
| GET | same | Own attempt history, paginated |
| GET | `/courses/{c}/attempts/{uuid}` | Own attempt/result |
| POST | same + `/submit` | Submit `{"answers":{"question_id":"A"}}` |
| GET | `/courses/{c}/progress` | Own reading and quiz progress |
| PUT | `/courses/{c}/modules/{m}/lessons/{l}/completion` | `{"completed":true}` / false |
| GET | `/me/notifications` | Own inbox, paginated |
| POST | `/me/notifications/{id}/read` | Idempotent own read marker |

Pagination uses `limit` (1–100, default 20) and `offset` (default 0). Revision conflicts
return 409, invalid question/config/answers return 422, caps/burst limits return 429.
Disabled or undersized banks return 409 on start. Invalid ownership/hierarchy returns
404; locked non-preview content returns 403. Current disabled accounts receive 401.

## Why Redis and RabbitMQ

PostgreSQL is authoritative for permissions, daily limits, attempts, grades and progress.
Redis caches the **private server-side** question pool for 60 seconds, keyed by quiz id,
quiz revision and course revision. Lesson edits/order/deletion change the course revision.
Redis also applies an atomic 20-start-requests/60-second account burst limit. Redis failure
falls back to PostgreSQL; it does not remove the transactional daily cap. Do not expose
Redis or its cached correct answers publicly. It is disposable, not a result store.

Submission updates the grade and inserts a versioned `quiz.submitted` event into
`learning_outbox` in one transaction. The API does not contact RabbitMQ. Publisher
confirms and persistent messages prevent marking an event delivered before broker ACK.
A crash between publication and DB commit can replay an event: the inbox has a unique
`event_id`, and consumers commit before acknowledging. Delivery is at least once under
normal broker operation, not an exactly-once guarantee.

Consumer failures use a 5-second TTL retry queue, at most 5 retries, then `.dead`.
Malformed/oversized messages go directly to `.dead`. If retry publication fails, the
original message remains unacknowledged and is redelivered after reconnect. Outbox
publication failure uses persistent exponential backoff (up to 300 seconds).
Queue names default to `lms.learning.events`, `.retry`, `.dead`. This local setup uses
durable classic queues on one broker: it is **not** an HA deployment, and classic DLX
transfer is not lossless across all broker failures. Production needs quorum queues/
appropriate DLX policy, monitoring, backup and an explicit dead-letter recovery procedure.
Do not delete/recreate queues or volumes to resolve configuration mismatches.
Notification/outbox retention and dead-letter redrive are future operational work.

## Run

```sh
make up
make status
```

Migration `0006` adds quiz, question, attempt, lesson progress, outbox and inbox tables.
Existing courses are unchanged: they have no enabled quizzes until a teacher configures
them. No questions, accounts or grades are silently seeded. `migrate` should exit 0;
`api`, `frontend`, `postgres`, `redis`, `rabbitmq`, `event-publisher` and
`notification-worker` should remain running. Broker management is localhost:15672;
local defaults are `lms` / `lms-local`. Change deployment credentials; they are examples.

Host development (separate terminals; do not also run container API/workers):

```sh
docker --context desktop-linux compose up -d --wait postgres redis rabbitmq
uv sync --locked --python 3.14
uv run alembic upgrade head
uv run python -m bin.run
uv run python -m src.learning_events.worker publisher
uv run python -m src.learning_events.worker consumer
```

`.env` settings apply to host runs. Compose uses internal service hostnames and forwards
the relevant quiz/broker settings. Worker containers deliberately disable the inherited
HTTP healthcheck: they are not web servers. Restart policies restart failed processes;
`make logs` and broker metrics are needed to detect stuck delivery.

## Manual checks (not executed as part of this implementation)

1. Start with `make up`, confirm migration/worker status. Log in as an assigned teacher
   or admin. Open a course editor, return it to draft, and open a module's quiz editor.
2. Save a disabled quiz with 2 questions/70%/600 seconds. Add two active A–D questions
   linked to different lessons, with explanations. Enable it and publish the course.
3. Log in as a student. Open the preview module's test without enrollment. Start it;
   inspect the network response: no `correct_option`, `explanation` or result is exposed.
   Start again via Swagger: it must return the same attempt UUID, not consume another try.
4. Submit one wrong answer. Expect 50%, failed, explanation for only those 2 selected
   questions, and a review link for the missed lesson. Re-submit identical answers:
   same result, one outbox row. Change an answer after submission: expect 409.
5. Mark a lesson read, reload, and unmark it. Reading changes independently of test
   results. Pass both questions in a new attempt; module quiz progress must increase.
6. Create a larger bank and repeat starts/submissions; samples contain distinct active
   questions and no question outside that module. Finish/expire 5 attempts: the sixth
   new start must return 429. Existing open attempt must still resume. Verify the reset
   boundary against `reset_at`, not the browser's timezone.
7. Test a later module without a grant (403), then obtain teacher approval and try again.
   Revoke/expire access and retry read/submit/lesson marking (403). A second student must
   not read/submit the first student's UUID (404) or read their inbox/lesson markers.
8. Use an unassigned teacher/student account against bank/configuration endpoints.
   Verify denial. Send a different module's lesson id in a question (422). Open two
   editors and save from both: the stale revision gets 409 and the form stays intact.
9. Start an attempt, edit the bank/configuration in draft, republish. Its old questions,
   correct answers and deadline must remain unchanged. Remove a linked lesson: history
   still displays the snapshot but no longer links to the removed lesson.
10. Configure 60 seconds, start and wait past its deadline. Submit: status `expired`,
    no grade/explanations, attempt still counts for the day. This is a manual timing test.
11. In separate terminals start the same module twice for one account at the same time.
    Expect one open UUID and one consumed attempt. Submit it twice concurrently with
    the same answers: one grade/outbox event. Different simultaneous answers: one wins,
    the other gets 409. These require real PostgreSQL; mocks do not prove row-lock behavior.
12. Stop RabbitMQ with `docker --context desktop-linux compose stop rabbitmq`. Submit
    a test: the result must still appear immediately. Restart the broker and wait for
    backoff; expect one notification. Stop/start `notification-worker` around delivery
    and confirm no duplicate inbox rows. Inspect `.retry`/`.dead` in broker management.
13. Stop Redis after startup. Quiz reads/start/submit must still work using PostgreSQL
    (burst limiter/cache are degraded); restarting Redis must not lose results/progress.
    Never flush PostgreSQL or delete volumes to reset tests.
14. Check keyboard/radio navigation, narrow/mobile layouts, long question text, error
    retries and logging out during a pending submission. No old-account result should
    appear after another account logs in. Check the visible warning about losing unsaved
    answers on reload; there is no answer-draft persistence in this stage.

Automated local checks are unit/mocked HTTP tests, offline migration SQL generation,
Ruff/mypy, frontend typecheck/lint/FSD boundary checks, Vitest and production build.
They do not replace these Docker/DB/concurrency/broker/browser checks.
