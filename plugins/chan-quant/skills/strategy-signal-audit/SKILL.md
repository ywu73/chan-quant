---
name: strategy-signal-audit
description: Explain Chan Quant draft signals, evidence, and time-stability boundaries without inventing Chan-theory rules or trading advice.
---

# Strategy signal audit

Use only when the user asks why a signal or candidate label exists, when it was formed, or whether future bars could rewrite it. Route through `inspect_instrument`.

Explain the backend-owned `SELECTED_DRAFT` rules using the returned reason codes and raw evidence. Keep `structure_at`, `confirmed_at`, and `executable_at` distinct and in order. Explain that `SELL` is a candidate exit warning for an existing long position, not a short signal.

Compare the returned event-study observations with the signal timing, but do not call sample-internal counts proof of strategy effectiveness. If the model is synthetic, say so explicitly. If fields are absent, say they are unavailable rather than reconstructing them in the Skill.

