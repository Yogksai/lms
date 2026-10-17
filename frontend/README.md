# MathWithMe frontend

React, TypeScript, Vite, React Router, TanStack Query, React Hook Form, Zod, and
CSS Modules. This implements the foundation, course content, and basic account
stages against the existing FastAPI API. Interface text is Russian, using the
provided screenshots as the visual reference. No fake progress, purchases,
workbooks, homework, ЕНТ tests, OAuth, or password-reset controls are included.

## Local development

Node 24 is used in Docker and CI; local Node must be at least 22.12.
From the repository root:

```sh
docker --context desktop-linux compose up --build -d --wait postgres redis migrate api
```

The root `.env` must contain a signing `SECRET_KEY` of at least 32 characters.
Resolve occupied ports before starting Compose. To populate demo courses:

```sh
docker --context desktop-linux compose exec api python -m bin.seed_courses
```

Then, from `frontend/`:

```sh
npm ci
npm run dev
```

Open http://127.0.0.1:5173. Vite proxies `/v1` to `http://127.0.0.1:8000`.
If the API uses another port, set `API_PROXY_TARGET` before starting Vite:

```sh
API_PROXY_TARGET=http://127.0.0.1:8001 npm run dev
```

This is server configuration, not a browser credential. No backend CORS changes
are needed for same-origin proxy requests. `npm run preview` previews static
assets only; use the dev proxy or the Compose frontend to test API integration.

## Docker

From the repository root, `make up` now includes the frontend. It serves on
http://127.0.0.1:3000 (override `FRONTEND_PORT` when necessary), with an Nginx
same-origin `/v1` proxy to the API. Direct navigation to nested routes is supported.
The runtime uses an unprivileged Nginx image; no Node development server is shipped.
Only local development is configured; HTTPS is required before public deployment.

## Architecture

Layers import only downward: `app → pages → widgets → features → entities → shared`.
Same-layer slices are independent, and each slice exposes its public `index.ts`.
`app` composes dependencies; entity API adapters parse backend DTOs with Zod.
Account/session orchestration is separated from components, and shared transport
depends on an authorization interface rather than a concrete session manager.
No UI imports are allowed from model code. `npm run lint` checks layer/slice imports.

Architecture and code style follow the principles in:

- https://feature-sliced.design/blog/frontend-clean-architecture
- https://feature-sliced.design/docs/reference/layers
- https://dev.to/serifcolakel/best-practices-for-writing-clean-react-code-with-examples-4b90
- https://www.turing.com/kb/writing-clean-react-code

These are design references, not verbatim templates: use typed functional components,
small focused files, external styles, and current router APIs. Domain/session code
is unit-testable without rendering components. Routing screens are lazy-loaded.

## Sessions

Tokens are kept only in memory. Reloading or closing the page loses the session
locally and requires login again; it does not revoke the server session. A new tab
also starts logged out. Persistent login would require a separately agreed backend
cookie flow. Browser storage never receives access or refresh tokens.

Authenticated requests use a Bearer access token. On `401`, one shared refresh
operation rotates the refresh token, followed by at most one retry of the original
request. Login/register/refresh/logout are never automatically retried. Late `401`
responses use the current token rather than rotating an already consumed token.
Failed refresh clears local identity and private queries; it does not retry an old
refresh token. Logout clears local identity immediately and attempts server revocation.
A network failure displays a warning that server revocation was not confirmed.
Late refresh/profile responses cannot restore a logged-out identity.

Backend checks remain authoritative: login does not unlock later course modules.
Successful authentication never bypasses publication or preview access rules.

## Checks

```sh
npm run lint
npm run format:check
npm run typecheck
npm test
npm run build
```

Unit tests use fake gateways/HTTP responses and do not need PostgreSQL or Docker.
CI runs these checks and builds the frontend container. Docker and live browser
integration checks remain manual; do not describe them as verified by unit tests.

## Manual verification

1. Seed the backend. Open `/courses`, search for Python, open a course, and inspect
   its modules. Search with no match should display an empty state.
2. Open a preview lesson. The video initially shows a black click-to-load panel.
   Clicking loads YouTube's privacy-enhanced embed. The real summary appears below;
   external video availability still depends on YouTube.
3. Open a later-module lesson: expect a locked notice, not a payment button. Open
   an unknown course/lesson: expect a not-found notice. Check invalid URLs as well.
4. Register an account, including invalid email, short password, Unicode password
   over 72 UTF-8 bytes, mismatched confirmation, and duplicate-email cases.
5. Login and inspect the header identity. Open `/profile`, edit the name, and verify
   the updated name in the header. Logout; `/profile` must redirect to `/login`.
6. Reload while logged in: expect to be logged out locally. Check browser storage
   to confirm that neither token was persisted.
7. For expiration/rotation testing, temporarily configure a short access lifetime
   in the root `.env`, recreate the API, login, wait for expiry, and open `/profile`.
   Inspect Network: one refresh followed by the authenticated retry. Restore the
   original lifetime and recreate the API afterward. Never retry the refresh request
   manually with its old token unless intentionally testing revocation.
8. Stop the API temporarily and check useful error/retry states and failed-logout
   messaging. Restore it afterward. Check desktop/mobile widths, keyboard focus,
   labeled fields, and direct navigation/reloads on nested routes.

TODO: add cookie-based persistent login only with the corresponding backend stage.
TODO: add enrollment, progress, homework, files, and payments when their APIs exist.
TODO: add live browser/end-to-end tests after manual integration verification.
