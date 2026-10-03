# Round 1 — comprehensive CLI/provider/operator audit

Status: independently accepted in the declared synthetic CLI/protocol/operator scope. Exact published commit 1f72d02486e3d88a31b8ea9a93d25e590aee1fc8, CI run 37134616366 completed successfully. Baseline: remote accepted 8e631d49b30e19b449eaaf26e5fe3f44e20bee3d. Remote main/v1.4 is an ancestor three commits behind; uncommitted external working copies are excluded.

## Full matrix performed afresh

- Research user: real smoke CLI in default Fast, one selected case, complete 20-case retrieval benchmark, official-URL fallback; JSON stdout/file equality, UTF-8 paths, budget accounting, partial results, unknown case and invalid budget, provider failures and successful retry
- Provider integration: Exa tool-list/call, Context7 resolve/call, Jina source matching/text/JSON/SSE, malformed/wrong-ID/ambiguous/error response; actual subprocess fake executables prevent live network and paid usage
- Host operator: actual native-probe subprocess inventory and opt-in single search in disposable HOME; no model turns; missing/partial/interactive native RPC, timeout, framing, process cleanup; host config isolation
- Analyst/data: real JSONL stdin/stdout, canonical links, tracking fields, shared provenance, duplicate/conflicting claims, invalid batch emits no partial output
- Installer/operator: fresh existing suite includes six concurrent marketplace updates, repeated install, force conflicts, unique backup/restore, failure/retry, existing registration preservation; no real installation or host marketplace modified
- Resource/terminal UX: actual doctor shell fixtures normal/JSON/deep, version/help/exit statuses, redacted diagnostics, shell syntax and Python compilation; CLI has no GUI, layout/motion not applicable
- Interrupted/error/persistence: output replacing an existing report, failed atomic replace/fsync, blank and Unicode content, first write, invalid parent, symbolic links, full stdout recovery after destination failure; single-flight interruption/cancellation regression remains active

## Finding and fix

An operator requesting --output to an invalid destination lost the CLI's JSON response to an uncaught traceback after research had already consumed requests. Direct write_text could truncate a previous report if interrupted mid-write. smoke.py and codex_probe.py now share a staged UTF-8/fsync/atomic replace helper. Failure preserves the old destination, cleans its temporary file, prints complete results to stdout, emits a bounded actionable diagnostic, and exits 2. Symlink destinations fail explicitly instead of replacing a link or overwriting its target.

Files: scripts/report_output.py, scripts/smoke.py, scripts/codex_probe.py, tests/test_five_round_output_recovery.py, tests/test_five_round_cli_journeys.py.

## Verification and limits

Fresh aggregate output is adjacent in round1-tests.txt (87 tests), round1-doctor.txt. Python compileall, sh -n for all shell scripts, git diff --check pass. Provider bytes are deterministic synthetic fixtures, so this establishes integration contracts and terminal workflows, not current provider uptime, actual OAuth readiness, account-bound channels, semantic research quality, or GUI accessibility. The skill-level Deep, Discovery and Capability Max research policies are reviewed as instructions, not measured for answer quality by the retrieval benchmark. No zero-bug claim. Prior screenshots or prior green CI are not used as new-round evidence.

Fresh operator fixtures additionally execute bootstrap fresh/repeat/ff-only/conflict/origin failure, update failure stopping before install, and proxy file/env selection, quoted arguments and exact child exit propagation. Real git/network/plugin installation is replaced by local executable fixtures.
