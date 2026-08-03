## Summary

- Describe the change in 2–4 concise bullets.

## Motivation


## Changes


## Data and licensing

- [ ] No real market data, credentials, cookies, authorization files, or private paths are included
- [ ] Third-party code, documents, and data sources are identified with their license or usage boundary
- [ ] Undocumented remote endpoints are still labeled as undocumented and fail closed

## Time correctness

- [ ] `structure_at`, `confirmed_at`, and `executable_at` remain distinct where applicable
- [ ] Confirmed historical signals remain prefix-stable
- [ ] The frontend does not reimplement backend-owned research calculations

## Testing

- [ ] Ran `cd backend && uv run ruff check .`
- [ ] Ran `cd backend && uv run pytest -q`
- [ ] Ran `cd frontend && npm test`
- [ ] Ran `cd frontend && npm run build`
- [ ] Tests use mocks, fixtures, or synthetic data and do not access live market endpoints

## Screenshots / recordings

- Not applicable, or attach sanitized evidence for UI changes.

## Risks
