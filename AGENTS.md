# AGENTS.md

## Scope

These instructions apply to the entire `chan-quant` repository.

## Product boundaries

- Treat the application as a research and audit tool until the user explicitly expands the scope.
- Do not connect a broker, place orders, publish signals, or use live credentials without explicit authorization.
- Do not present mock data, local checks, event studies, or backtests as evidence of live trading performance.
- Keep unknown strategy formulas explicit. Never invent buy-line, sell-line, channel, resonance, divergence, or Chan-theory rules and label them as confirmed.

## Time correctness

- Every structural event must distinguish `structure_at`, `confirmed_at`, and `executable_at`.
- Confirmed historical signals must pass prefix-stability tests and must not be silently rewritten by future bars.
- Charts may locate a structure on its pivot bar, but trade simulation must use the first actually executable bar.

## Architecture

- The Python backend owns indicators, structural state, signals, event studies, and strategy conclusions.
- The frontend owns formatting, layout, chart rendering, and interaction only.
- Keep strategy outputs explainable through reason codes, rule versions, parameter versions, and raw evidence.
- Keep market data and secrets out of Git.

## Git workflow

- Inspect branch and worktree state before modifying files.
- Make implementation changes on a dedicated task branch, not directly on `main`.
- Do not push, create pull requests, publish releases, merge to `main`, or delete branches without explicit authorization.

