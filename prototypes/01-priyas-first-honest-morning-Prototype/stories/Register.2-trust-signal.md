# Story — Register § Section 2: Trust Signal

**View:** 01.1 Register · **Section:** 2 of 6 · **Est:** 5 min · **Mode:** fast
**Output:** `01.1-register.html` (inject below header)

## Purpose
The honesty hook — addresses Priya's core fear (another overconfident, shame-inducing tool) immediately, before the form.

## Objects
| Object ID | Type | Content |
|---|---|---|
| `register-trust` | container | space-xs gap; space-xl below (before form) |
| `register-trust-headline` | H2 (text-lg, semibold) | "Your honest financial picture. No guessing. No shame." |
| `register-trust-subline` | p (text-sm, muted) | "We only tell you what we actually know. When we're uncertain, we say so." |

## HTML
```html
<section id="register-trust" class="register-trust">
  <h2 id="register-trust-headline" class="trust-headline">Your honest financial picture. No guessing. No shame.</h2>
  <p id="register-trust-subline" class="trust-subline">We only tell you what we actually know. When we're uncertain, we say so.</p>
</section>
```

## Acceptance
- Agent: both objects present; copy exact; centered; no overflow @375/1280.
- User: reads as reassuring, not salesy.
