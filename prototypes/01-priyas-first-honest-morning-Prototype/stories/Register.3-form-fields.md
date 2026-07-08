# Story — Register § Section 3: Registration Form Fields

**View:** 01.1 Register · **Section:** 3 of 6 · **Est:** 15 min · **Mode:** fast

## Purpose
Capture minimal account data (email + password + confirm) with a clear primary CTA. No friction beyond essentials.

## Objects
| Object ID | Type | Label / Placeholder | Attrs |
|---|---|---|---|
| `register-form` | form container | — | space-md gap |
| `register-form-email` | text input | "Email address" / "you@example.com" | type=email, autocomplete=email, required |
| `register-form-password` | password input + show/hide | "Password" / "8+ characters" | type=password, autocomplete=new-password |
| `register-form-confirm-password` | password input | "Confirm password" / "Repeat your password" | type=password, autocomplete=new-password |
| `register-form-cta` | primary button | "Create my account" | full-width; spinner on loading |

## HTML (structure)
- `<form id="register-form">` with three `.field` blocks (label + input-wrap + `.error` span).
- Password fields use `.input-wrap` with a `.pw-toggle` button ("Show"/"Hide", aria-label).
- CTA: `.btn.btn--primary` with `<span class="btn-label">` + hidden `.spinner`.

## Acceptance
- Agent: all 5 objects present; labels are real `<label for>` (a11y); show/hide toggles input type; CTA full-width; no overflow.
- User: form feels short and unintimidating.

Note: validation + states = Section 4; submit/redirect = Section 6.
