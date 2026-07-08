# Story — Register § Section 5: Existing-User Link + Legal Footnote

**View:** 01.1 Register · **Section:** 5 of 6 · **Est:** 10 min · **Mode:** fast

## Objects
| Object ID | Type | Content |
|---|---|---|
| `register-existing-user` | container | centered |
| `register-existing-user-link` | inline link | "Already have an account? **Log in**" → placeholder (returning-user login out of scope) |
| `register-legal` | container | centered, muted |
| `register-legal-text` | caption (text-xs) | "By creating an account you agree to our [Terms of Service] and [Privacy Policy]. We never sell your data." |

## Behavior
- Login link → `#` placeholder (alert/console: "Returning-user login is out of scenario scope").
- T&C / Privacy links → open in-page modal (`.modal-overlay`/`.modal`), NOT new tab (preserves mobile context). DPDP: no pre-ticked consent.

## Acceptance
- Agent: both objects present; legal links open modal; login link is a stub; no overflow.
- User: legal is present but non-intrusive.
