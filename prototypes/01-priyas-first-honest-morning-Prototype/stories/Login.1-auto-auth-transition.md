# Story — V2 Login (01.2): Auto-Authentication Transition

**View:** 01.2 Login · single section · **Mode:** fast
**Spec:** `.../01.2-login/01.2-login.md`
**Output:** `01.2-login.html`

## Purpose
A transition beat, not a task. Confirm the account is created, reassure Priya she's in, auto-advance to Statement Upload. No credential entry.

## Objects
| Object ID | Type | Content |
|---|---|---|
| `autologin-confirmation` | centered block | vertically centered, space-lg gap |
| `autologin-confirmation-logo` | logo mark | ₹ placeholder |
| `autologin-confirmation-headline` | H2 (text-lg semibold) | "✓ Account created!" (aria-live=assertive) |
| `autologin-confirmation-submessage` | p (text-md) | "Let's upload your first statement." |
| `autologin-confirmation-progress` | spinner | role=progressbar, aria-label="Setting up your account" |

## States
- **in-progress** — spinner visible (~1.6s) — default on load.
- **success** — auto-redirect to `01.3-statement-upload.html`.
- **error-token-failure** — error card + "Try logging in" fallback link (demo: `?fail=1` query triggers it).

## Behavior
- On load: read `sessionStorage.demoAuth`; if missing, still proceed (demo tolerance).
- Optional warmth: if we have an email, keep generic per spec (personalization is an open question — leave generic).
- `setTimeout(redirect, 1600)` to `01.3-statement-upload.html`.
- Manual fallback link surfaces after 3s if redirect hasn't fired (safety).

## Acceptance
- Agent: headline "✓ Account created!"; progressbar role present; after ~1.6s navigates to 01.3; `?fail=1` shows error card + fallback link and does NOT auto-redirect.
- User: feels instant and reassuring, not a dead-end.
