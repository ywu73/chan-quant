---
name: market-comparison
description: Compare two to eight A-share instruments or versioned observation groups while preserving coverage and quote failures.
---

# Market comparison

Accept 2–8 distinct canonical symbols for a one-off comparison. For names, resolve candidates first. For a built-in industry or theme group, read `resources/comparison-presets.json` and disclose its version, member evidence, and that it is not an official index or official weighted portfolio.

Call `compare_instruments`. Explain the requested and common windows, local trading-date alignment, null missing dates, normalized returns, drawdown, coverage, adjustment warnings, per-symbol failures, and independent Quotes separately. Do not forward-fill, convert currencies, or silently remove partial successes.

If the backend result is `PARTIAL` or `FAILED`, preserve that status in the answer. A comparison is not a portfolio allocation or trade recommendation.

