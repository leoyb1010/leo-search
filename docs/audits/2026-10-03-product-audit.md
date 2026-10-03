# Leo Search: two-round product audit, 2026-10-03

Base: a73d3eb9ce886cce3565b5418fab3a33a96083d1. Target: existing codex/audit-leo-search-20261001 branch. No production profile, provider credentials, live paid requests, installation on user devices, merge or deployment.

## Round 1: product contracts and lifecycle

Inspected CLI install, doctor, protocol initialization, native probe, smoke, evidence provenance, request budgeting, failure recovery and shell entry points. This repository has no standalone GUI, so a button inventory or browser screenshot would misrepresent its product surface.

- Installer backups previously used second-resolution filenames, allowing repeated updates to overwrite an earlier recovery point. The extracted marketplace updater now uses unique backups and atomic replacement; preserves unrelated plugins and metadata; validates malformed shapes before mutation; converges duplicate Leo entries; and serializes cooperating Leo installer processes.
- Doctor controller diagnostics printed raw process arguments, potentially exposing unrelated values in a pasted support report. Diagnostics now retain process identity/resource columns and redact arguments.
- SSE transports using CR-only endings or an initial BOM were not consistently accepted. Shared wire normalization now handles LF, CRLF, CR and an initial BOM.
- Multiple replies with the same RPC ID could mask a prior error by selecting the last response. Initialization and smoke require exactly one matching response, while allowing unrelated notifications. Reader transport normalization preserves authoritative outer source provenance.

## Round 2: independent challenge and regression

A separate reviewer reran seven marketplace lifecycle tests and six protocol tests and inspected the changes. Real temporary files and six concurrent subprocesses verify unique backups, unrelated-entry preservation, malformed-input nonmutation, failed atomic publication recovery, idempotent retry, and mocked Codex shell install failure/retry. Transport tests exercise all line endings, BOM, ambiguous reply IDs, unrelated notifications, CLI exit status, and forged content provenance.

Final local verification: Python 3 unit discovery 73/73 passed; shell doctor matrix passed; git diff --check passed. The existing GitHub Actions Python 3.11/3.12/3.13 matrix additionally runs compilation and shell syntax checks. Terminal hosted results must be tied to the final published SHA before declaring CI acceptance.

## Coverage limits and compatibility

Existing 60 regression tests are retained; 13 new product regressions were added. All network/provider responses are synthetic and offline. Live provider/OAuth availability, external model result quality, native client integration and real personal profiles were not exercised. Locking covers cooperating installers, not unrelated editors. Unix fcntl is used consistently with the existing POSIX shell/macOS/Linux install workflow; no native Windows support is claimed. Atomic replacement protects original contents but does not establish a complete system-wide installation transaction. No dependency, schema, model default or provider endpoint changed.
