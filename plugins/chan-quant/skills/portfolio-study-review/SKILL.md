---
name: portfolio-study-review
description: Review hypothetical single-instrument portfolio-study outcomes and assumptions returned by Chan Quant.
---

# Portfolio study review

Use when the user asks why a hypothetical study accepted or rejected a signal, or asks about fees, slippage, limits, and execution timing. Route through `inspect_instrument` and use only the backend result.

Describe each decision, status, and reason code. Preserve the policy label `HYPOTHETICAL_RESEARCH_ASSUMPTIONS`, fixed 10% limit assumptions, lot size, fees, tax, slippage, and no-execution cases. Explain that the study is single-instrument and long-only; `SELL` does not mean opening a short.

Never present the equity curve, return, drawdown, win rate, or exposure as live or achievable performance. State when ETF, index, ST, 20%/30%, IPO, corporate-action, order-book, or real-fill rules are outside the contract.

