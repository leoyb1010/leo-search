# Round 2 — full CLI matrix with adversarial imported/provider data

Status: accepted within the declared local synthetic coverage; publication and exact-commit CI validation are pending. Starting code is Round 1 exact remote commit 1f72d02486e3d88a31b8ea9a93d25e590aee1fc8 (its fresh Python 3.11/3.12/3.13 CI passed).

## Complete re-audit

Reviewed all scripts, plugin/MCP manifests and routing skill again. Re-executed the full user/provider/analyst/operator matrix, including real process default/scoped/20-case/fallback retrieval contracts, per-run budgets and reused calls, native inventory versus one-search status, protocol framing/cancellation, doctor human/JSON/deep diagnostics, evidence canonicalization and conflicting claim provenance, bootstrap/update/proxy shell entrypoints, portable install conflict/restore, marketplace repeated/concurrent updates, and interrupted output recovery. No GUI exists; terminal formatting, Unicode, stdout/stderr and exit behavior are the applicable presentation surface. Fresh results: round2-tests.txt 92/92, round2-doctor.txt; compileall, every shell sh -n and diff whitespace checks passed.

## New seams, reproduction, and fix

Unlike Round 1's output destination interruption, this pass varied the incoming bytes and data shape across provider, analyst and installer roles. With a valid first evidence row followed by malformed metadata, the old CLI could emit a nonstandard JSON NaN/Infinity, raise a Unicode encoding exception for an unpaired surrogate, or carry an excessively nested structure to downstream consumers. An imported marketplace and Reader/protocol payload need the same boundary, not per-command crash handling.

The shared protocol parser now rejects non-finite numbers, invalid Unicode scalar strings and nesting deeper than 64, including unknown metadata keys. It normalizes decoder recursion into a bounded ValueError. Doctor validation returns false, retrieval probes return unavailable without losing other cases, the evidence ledger rejects the whole input batch before stdout, native RPC fails cleanly, and marketplace leaves original bytes and backups untouched. Ordinary Chinese/emoji strings, SSE frames, persisted report formats and successful provider/native fixture workflows remain covered.

Reproducer before/after is test_five_round_wire_recovery.py plus round2-before.txt and the complete current aggregate. The report-output implementation from Round 1 is included in regression. No user HOME, real Codex, installed plugin, live provider or production records were touched.

## Limits

Synthetic executable/provider results establish bounded transport and CLI workflow behavior, not live availability, OAuth readiness, semantic answer accuracy or account-bound channels. The 20-case retrieval benchmark is not execution of skill-level Deep/Discovery/Capability Max research quality. Existing browser cleanup and source/version/authorization rules were reviewed as policy text, not proven against an external authenticated session. No absolute zero-bug claim.

Independent review additionally exposed exponent-overflow JSON (1e400/-1e400), which parse_constant does not catch. The iterative validator now checks float finiteness too. New boundary regressions cover ±1e308, negative zero, integers, ordinary Unicode, 64/65 nesting, and actual initialize/OAuth/Reader/native-RPC/marketplace/ledger input contracts.
