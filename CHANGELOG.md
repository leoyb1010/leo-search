# Changelog

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
