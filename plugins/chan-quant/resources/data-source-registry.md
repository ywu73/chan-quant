# Data source routing

The source of truth is [`docs/data-source-registry.json`](../../../../docs/data-source-registry.json). The plugin must preserve the backend's source IDs and limitations, especially `sina-undocumented-*`, user-supplied CSV, and auditable snapshot. Remote failures are not permission to fall back silently.

