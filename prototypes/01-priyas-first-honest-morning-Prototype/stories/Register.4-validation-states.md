# Story — Register § Section 4: Validation + Form States

**View:** 01.1 Register · **Section:** 4 of 6 · **Est:** 20 min · **Mode:** fast

## Purpose
Enforce all 7 validation rules with inline, non-shaming error messages; handle loading, email-taken, and network states.

## Validation Rules (spec)
| Field | Rule | Message |
|---|---|---|
| Email | required | "Please enter your email address" |
| Email | valid format | "That doesn't look like a valid email" |
| Email | not registered | "This email is already registered. Log in instead?" |
| Password | required | "Please create a password" |
| Password | min 8 | "Password must be at least 8 characters" |
| Confirm | required | "Please confirm your password" |
| Confirm | matches | "Passwords don't match" |

## States
- **typing** — validate on blur; clear error on input.
- **loading** — CTA spinner, inputs disabled.
- **error-validation** — inline `.error` under each field; `aria-describedby`; input `.has-error`.
- **error-email-taken** — email field shows registered error (triggered by demo email `taken@example.com`).
- **error-network** — `.toast` "Something went wrong. Please try again." (demo email `network@example.com` simulates).

## JS (inline)
- `validateField(name)`, `validateAll()`, `setError(id,msg)`, `clearError(id)`.
- Blur listeners on each input; input listener clears error.
- Email regex (RFC-ish). Confirm must equal password.

## Acceptance
- Agent: empty submit → 3 required errors; bad email → format error; short pw → min-8; mismatch → mismatch error; `taken@example.com` → email-taken; valid → no errors (submit handled in §6). aria-describedby present.
- User: errors feel factual/kind, not scolding.
