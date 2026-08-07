---
name: instrument-research
description: Route single-instrument Chan Quant research requests through instrument resolution and the daily dashboard plus independent quote tools.
---

# Instrument research

Use for a named A-share or ETF when the user wants a neutral research snapshot. This is a read-only research workflow, not investment advice.

1. Call `resolve_instruments` for names, six-digit codes, or non-canonical input. If there is more than one candidate, ask the user to choose an exchange; do not guess.
2. Call `inspect_instrument` with the canonical `NNNNNN.SH` or `NNNNNN.SZ` symbol and optional ISO `as_of`.
3. Summarize the daily model first, then cite strategy version, data mode/source, adjustment declaration, timing fields, evidence, event study, portfolio-study assumptions, and warnings.
4. Show the independent Quote in a separate section with its own `quote_at` and `received_at`. Never use it to recompute daily signals.
5. Offer the returned Dashboard URL for chart inspection.

Stop or state the limitation when the tool returns `REJECTED`, `UNAVAILABLE`, an ambiguous candidate set, a failed quality report, or a mock/synthetic result. Do not turn `CANDIDATE_BUY` or `CANDIDATE_EXIT` into an action instruction.

