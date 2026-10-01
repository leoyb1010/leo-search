# Leo Search: two-round audit and repair

Date: 2026-10-01 UTC. Repository: `leoyb1010/leo-search` only.

## Scope and boundary

The GitHub baseline is main `0bd6ea016b233b4d957954ddbde33fb24cde036e` (published 1.4.0), tree `6062355d9d3473b19742ee322b5a99137f199d8d`. All 39 original blobs and the reconstructed tree were verified. The reported unpublished Studio 1.6 copy was not accessed or replaced. Repair branch: `codex/audit-leo-search-20261001`.

This is a manual source, adversarial and runtime regression audit. A dedicated managed security-scan runner was unavailable. There is no standalone browser UI in this repository: applicable user journeys are CLI output, install conflict/retry behavior, cancellation, evidence normalization and diagnostics. No live providers, account OAuth, actual host credentials/configuration, marketplace installation, production data or user devices were used. Test child processes, configurations and homes were synthetic and disposable.

## Round 1

Frozen local evidence commit: `62e822d1cdd12d2c50261bafcbd17de051af3f1f` (local audit snapshot, not an upstream parent). Baseline 18 Python tests and shell doctor fixtures passed. Reproductions then showed:

1. An interrupted single-flight owner left its Future unresolved and waiters hung. Cancellation now reaches all waiters; budgets require positive integer limits.
2. Evidence normalization accepted credential-bearing URLs, malformed ports/control characters/non-text content, and merged distinct trailing-slash or repeated-query resources. Input errors are redacted, invalid data is rejected, and source identity is preserved.
3. Portable installation reported preserved conflicts as success and reused collision-prone backup directories. Conflicts now return nonzero, duplicate targets are idempotent, and forced replacements have unique backups.
4. Native probe isolation missed inline/nested TOML tables. Real TOML parsing and quoted per-process overrides replace the regex, and the subprocess starts in a disposable directory. Binary RPC framing enforces incomplete-line deadlines, size/pagination caps and interactive-input refusal. Missing expected routes fail closed.
5. Doctor diagnostics treated matching words as valid protocol responses. JSON/SSE and OAuth metadata now undergo structural validation. Malformed test fixtures exposed by this stricter check were corrected rather than weakening acceptance.

Round-1 snapshot: 33 Python tests, shell fixtures, plugin manifest validation and whitespace checks passed.

## Round 2: independent adversarial review and repairs

Independent review reran the round-1 tests and found four remaining classes of issue:

1. Query decoding still merged `%FF` and `%FE`, and bare flags with empty values. Raw query segments/order/octet spelling are now preserved; only explicit tracking keys are removed.
2. Malformed native inventory entries raised uncaught KeyError/TypeError. Inventory validation produces bounded generic failures. Missing native executable returns a redacted JSON report with exit 2.
3. Smoke probes crashed the entire parallel report on malformed provider arrays/nulls and accepted mismatched JSON-RPC versions/IDs. Envelope, tool inventory and text content are validated; failures become unavailable individual cases. Responses are bounded.
4. TOML parsing introduced an undeclared Python minimum. Python 3.11+ is documented, with a clear stop before native server startup on older versions.

Frozen repair snapshot: `ede78c1f7607cc5693c8ef288bfcdd93c964ca42`. An independent reviewer examined the delta and reran all 38 Python tests, doctor shell fixtures and whitespace checks successfully. No additional confirmed blocker remained in that bounded review. The final branch also runs offline CI on Python 3.11, 3.12 and 3.13, shell syntax checks and compilation; it has read-only repository permissions and no deployment step.

## Verification and honest limits

| Check | Local result |
| --- | --- |
| Python unit/adversarial tests | 38 passed |
| Shell doctor fixtures | Passed |
| Plugin manifest validation | Passed |
| Shell syntax / Python compilation | Passed |
| Whitespace check | Passed |
| Secret-pattern scan of changed source/report | Passed before publication |
| Live provider connectivity/retrieval | Not run |
| Real native host/OAuth integration | Not run |
| Unpublished Studio 1.6 compatibility | Not reviewed |
| GitHub final-SHA CI | Linked separately after terminal result |

Network results in old benchmark files were not refreshed or represented as current. The native probe's host profile-layer merge behavior is not verified here; a speculative concern was not promoted to a confirmed vulnerability. No guarantee of zero bugs, universal source independence or complete provider correctness is made.

## Pull and rollback

Fetch and check out only `codex/audit-leo-search-20261001`; inspect its exact remote commit and CI before merging or installing. The branch is based on the existing GitHub baseline; main was not overwritten, merged or deployed. To roll back an eventual installation, restore the previous checkout and reinstall through the existing supported plugin workflow. Portable-installer user conflicts remain preserved unless an explicit force operation is requested. No database migration or production data change is included.
