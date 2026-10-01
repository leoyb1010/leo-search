# Leo Search: two additional role-simulation rounds

Request received 2026-10-01 23:03 UTC. Baseline: `2bd95036172314fb932e963ab879c5e360a46a47`, branch `codex/audit-leo-search-20261001`. These are new tests and repairs after the previous two-round audit. All 46 baseline blobs were reconstructed and verified against Git object hashes; executable modes were preserved. Published 1.4 lineage only; unpublished Studio 1.6 was neither accessed nor substituted.

## Real roles and trust boundaries

This repository has a CLI/plugin, not a browser application or product login/tenant system.

| Actual role/boundary | Normal journey | Negative/recovery journey |
| --- | --- | --- |
| Local operator installing the canonical skill | Select target, preserve existing data, repeat installation | Conflicting directory, forced replacement failure, six concurrent installers |
| Native host controller | Isolated config → initialize → inventory → ephemeral thread → one requested search → cleanup | Malformed handoff/result, boolean ID, rejected OAuth with cached tool inventory |
| Remote provider | JSON/SSE RPC, reader JSON or text, plain or Markdown citations | Missing provenance, mismatched resource, credential-bearing citation, lookalike domain |
| Researcher/evidence consumer | Bounded report with actual source links and explicit verification state | No invented source, no false retrieval success, no private payload in failure reports |

No actual account roles, tenants, permissions or browser screens are invented. Existing budget/cancellation, duplicate provenance, source identity, conflicting evidence, installer conflict and host-isolation regressions remain in the full suite.

## Round 1: normal role journeys and broken handoffs

`tests/test_role_round1.py` drives the actual native CLI `main()` with disposable host configuration and synthetic RPC/process responses, and the actual provider `probe()` with synthetic provider replies. Happy-path host flow checks exactly one tool call and process cleanup. No host credentials or provider network calls are used.

1. **Host/provider contract failure (medium reliability).** Missing or malformed `thread/start` and tool responses raised unhandled KeyError/TypeError/AttributeError rather than a usable diagnostic. Reproduction includes null/missing thread IDs, null arrays and non-text payloads. Explicit shape checks now stop before issuing a provider call for invalid thread handoffs and return bounded redacted reports for malformed provider results.
2. **Response identity confusion (low correctness).** Python boolean `true` compared equal to numeric request ID 1. The doctor and smoke validators accepted that invalid response identity. Numeric request matching now excludes booleans; native framing received the same guard and is challenged again in Round 2.
3. **Unreliable provenance at the provider→researcher handoff (medium correctness/privacy).** Reader JSON without a source URL inherited the requested URL; a different page with matching topic text could pass as the requested extraction; credential-bearing source URLs could enter a report. Reader JSON now requires actual source metadata, source URLs use the established credential-rejecting canonicalizer, and known-URL extraction reports `source_matches_requested` explicitly.

Before repair: the 7 new tests had 5 failed assertions and 9 failing subcases/errors; one normal host journey already passed. After repair: 7/7 pass; 45/45 aggregate Python tests pass. Original failing logs and repaired logs have SHA-256 digests in the companion evidence manifest.

## Round 2: adversarial challenge of repaired and adjacent paths

`tests/test_role_round2.py` uses an independently constructed adversarial matrix: actual pipe-backed RPC framing, native CLI orchestration, failure-injected filesystem writes, and six concurrent real installer subprocesses.

1. **Revoked session with cached tool visibility (medium reliability/privacy boundary).** A native `invalid_grant` diagnostic did not make the cached TinyFish route unavailable; `--search` still attempted a thread/tool handoff. Rejected OAuth now marks the route unavailable and returns before any thread or provider call. Test proves `tool_calls == 0` and only initialize/inventory calls occurred.
2. **Provider source impersonation (medium correctness).** The native retrieval check only searched for the domain substring. A lookalike hostname, bare domain mention, or credential-bearing URL could falsely verify retrieval. Native citations now parse and validate actual URL authorities. Exact official-host plain URLs and Markdown citations remain supported. This is a retrieval-contract check, not proof that provider content is accurate.
3. **Installer interruption and concurrency (medium recoverability).** Forced replacement moved the original before link creation; link-creation failure left the target missing. Links are now staged first, cooperating installers take an advisory lock, and a failed publish restores the original. Tests verify failure before moving data, failure after backup, idempotent concurrent completion, and exactly one preserved original backup. Existing non-forced conflicts remain intact.

Before repair, the original 5 Round-2 tests produced 3 failed assertions and 2 errors (including native malformed handoff continuation and link failure). The 6-process race was additionally exercised; concurrency success on one run is not by itself evidence of prior failure. After repair, 7 Round-2 tests pass, including Markdown compatibility and post-backup restoration added as review checks. Round-2 suite: **52/52 pass**. Independent review then added 8 provenance cases; final full suite: **60/60 pass**.

## Commands and verification

```
python3 -B -m unittest discover -s tests -p test_role_round1.py -v
python3 -B -m unittest discover -s tests -p test_role_round2.py -v
python3 -B -m unittest discover -s tests -v
sh tests/doctor_test.sh
python3 -B -m compileall -q scripts tests
for script in scripts/*.sh tests/*.sh; do sh -n "$script"; done
git diff --check
```

Independent review reproduced two remaining page-body provenance bypasses (forged source headers and SSE examples inside Markdown). Both are closed: only the classified outer response metadata can establish the source. Eight new review cases cover these spoofs, JSON/SSE/text compatibility, conflicting metadata and legitimate redirect gaps. The independent reviewer re-read the final delta, reran all **60/60 tests**, and passed whitespace checks with no further blocking finding in the reviewed changes.

Final local Python suite, shell doctor fixtures, Python compilation, shell syntax and whitespace checks pass. GitHub `Verify` runs the same offline contracts on Python 3.11, 3.12 and 3.13; exact final-SHA run links are supplied with the delivery record after publication.

## Compatibility, risks and checks not run

- A legitimate reader redirect to a different URL is now reported as an unverified requested-resource match. Its returned source is retained; it is not silently relabeled. This deliberately conservative benchmark result is not a provider availability failure.
- Native plain/Markdown citations are supported. Other future provider formats may require explicit adapters. Live provider output, actual OAuth refresh and real Codex host integration were not run; no claim of live readiness is made.
- Portable installs support documented Mac/Linux hosts via `fcntl`. Advisory locking coordinates this installer only. A SIGKILL/power loss in the directory-backup→publish window cannot run rollback; the unique backup remains for recovery. No crash-atomic multi-directory transaction is claimed.
- No browser UI exists here, so browser screenshots, responsive layouts and visual accessibility are not applicable. CLI error output and recovery are tested.
- No main changes, merges, deployment, marketplace install, database migration, production access, user Mac access or paid provider tests occurred. The separate managed security-scan service was not available; this report covers manual engineering review and executed synthetic tests.
- No guarantee of zero bugs or complete provider correctness is made. Rollback is a normal revert of the role-audit commit on the audit branch; preserved installer backups must not be deleted as part of rollback.
