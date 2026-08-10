# Deployment assets

This directory contains the Caddy gateway configuration and authenticated smoke
checks for the single-host private staging profile.

- `Caddyfile` serves the production frontend, applies private Basic Auth and
  security headers, falls back to the SPA entry point, and proxies only the
  documented API and runtime endpoints.
- `smoke-test.sh` verifies authentication, SPA deep links, health/version
  contracts, and the default force-refresh rejection.

The operator workflow, environment contract, data mounts, upgrades and explicit
non-goals are documented in [`../docs/deployment.md`](../docs/deployment.md).
