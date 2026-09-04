# Changelog

## [1.4.0] - 2026-09-05

- Distinguish connectivity, OAuth metadata, visible tools and actual retrieval; JSON health output includes resource checks.
- Add opt-in native MCP probe and a bounded public smoke/20-question benchmark without model calls.
- Add per-run single-flight response reuse, hard request budgets and selected-case fallback testing.
- Group copied content and shared upstream sources while preserving links, claims and contradictory support annotations.
- Preserve Jina cache warnings across text/JSON/SSE formats and exclude code-example URLs from citation checks.
- Document evidence-driven stopping, Chinese/discovery coverage and authenticated fallback boundaries.


## [1.3.0] - 2026-08-29

### Added

- Fast, Deep, Discovery and Capability Max research modes.
- Machine-readable `doctor.sh --json` output.
- Evidence-ledger URL normalization, content hashing and exact duplicate removal.
- Progressive references for research modes, evidence handling and rolling benchmarks.

### Changed

- Treat four concurrent queries as a per-wave limit so Deep/Discovery can continue when evidence gaps remain.
- Balance claim precision with labeled discovery recall instead of suppressing useful leads.

## [1.2.1] - 2026-08-28

### Fixed

- Retry Jina health checks through the configured macOS loopback HTTPS proxy when fake-IP DNS makes direct access fail.
- Avoid duplicate `000000` status rendering when curl reports a connection failure.

## [1.2.0] - 2026-08-28

### Added

- TinyFish OAuth MCP route for free live web/news/paper search and browser-rendered public URL extraction.
- TinyFish OAuth discovery validation in the read-only doctor and regression suite.

### Security

- Restrict the personal Codex installation to TinyFish `search` and `fetch_content`; paid browser automation, Vault and saved profiles stay disabled.
- Keep dynamic rendering remote so ordinary Leo Search requests create no local browser process.

## [1.1.0] - 2026-08-17

### Added

- Real MCP initialization checks for Exa and Context7.
- RSS, Bilibili and authenticated GitHub capability reporting.
- Regression tests and ShellCheck validation for plugin scripts.

### Fixed

- Fail health checks on HTTP errors and invalid MCP responses.
- Reject Context7 snippets that drift from a requested library version.
- Make account-bound routing and OpenCLI cleanup requirements explicit.
