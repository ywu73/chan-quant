---
name: market-breadth-review
description: Explain observed Shanghai/Shenzhen A-share market breadth with coverage and remote-source limitations.
---

# Market breadth review

Use for questions about advancing, declining, unchanged, unavailable counts, or market temperature. Call `inspect_market_breadth`; default `refresh` is false. Tell the user that `refresh=true` rereads the remote universe and may fail without falling back to an old snapshot.

Check session date, observation time, status, universe size, coverage, resolution ratio, and issues before describing bins. If status is `FAILED` or coverage is insufficient, do not interpret the distribution. Disclose the observed, non-auditable nature of the remote result and undocumented provider source.

Do not translate market breadth into a user-specific buy, sell, hold, or position instruction.

