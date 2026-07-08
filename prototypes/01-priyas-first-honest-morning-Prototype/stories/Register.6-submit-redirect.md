# Story — Register § Section 6: Submit Flow + Auto-Auth Redirect

**View:** 01.1 Register · **Section:** 6 of 6 · **Est:** 10 min · **Mode:** fast

## Purpose
On valid submit: mock `POST /auth/register`, set a demo auth flag, then forward to 01.2 Login (auto-authentication transition).

## Behavior
- `onSubmit` → `validateAll()`; if invalid, stop.
- Set loading state (spinner, disable inputs).
- Mock async register (~700ms):
  - email `taken@example.com` → email-taken error, clear loading.
  - email `network@example.com` → network toast, clear loading.
  - else → success: `sessionStorage.setItem('demoAuth', JSON.stringify({email, ts})`; redirect `window.location.href = '01.2-login.html'`.
- Success has no visible state (immediate redirect) per spec.

## Auth note
Spec calls for httpOnly cookie; prototype simulates with sessionStorage demo flag only (no real backend).

## Acceptance
- Agent: valid submit sets `demoAuth` and navigates to `01.2-login.html`; taken/network paths show correct errors and do NOT navigate; loading spinner appears during request.
- User: submitting feels instant and lands on the next step.
