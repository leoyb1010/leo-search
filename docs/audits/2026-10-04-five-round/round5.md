# Round 5 — full final audit with real cancellation and compatibility review

Status: accepted within the declared local synthetic coverage; publication and exact final-commit CI are pending. Starting checkpoint 370f6e5, accepted Round 4 tree c5e47b3f24c962c52de4c6a7ba4ed05a98dbd537. Later-round publication and exact final-commit multi-Python CI remain pending.

## Complete fresh matrix

Re-audited all entrypoints and command exit/output contracts, task budgets and request reuse, provider/source/protocol validation, native process framing and cleanup, evidence identity/merging/conflict preservation, marketplace and portable backups/recovery, bootstrap/update with a real local worktree, child proxy environment, and report files. Read the final changes together with the routing/benchmark policy and packaging manifests. Re-executed all prior ordinary, role-specific, abnormal/repeated/retry/persistence paths plus the new real signal scenarios. Full aggregate: 102/102, doctor human/JSON/deep fixtures, Python compileall, every shell sh -n, staged/worktree whitespace checks pass. The final input-contract changes and recovery steps are listed in compatibility.md.

## New interrupted-user finding

The JSON doctor installed one signal trap that removed its temporary file but did not exit. A real process-group Ctrl-C while a fake provider slept returned exit 1 and a FileNotFoundError traceback instead of cancellation: the later formatter tried to open the deleted file. Separate HUP/INT/TERM exit traps now retain a single EXIT cleanup. Tests start the actual shell CLI in an owned process group, wait for the sleeping provider fixture, signal that group, verify the standard 129/130/143 exit, no stdout/traceback, no extra provider call and no leftover temporary report. Normal successful/failed diagnostic reports are still tested independently.

Current evidence: round5-before.txt, test_five_round_cancellation.py, round5-tests.txt, round5-doctor.txt. No real network provider or actual user installation was involved. All functional source changes are now frozen for final review and eventual exact-commit CI.

## Limits

These five rounds independently repeated a complete declared synthetic CLI/provider-contract/operator matrix and added new failure/state combinations each time. They do not establish all external provider availability, valid OAuth on a real host, account-bound channels, advanced research semantic quality or GUI accessibility. The product has no GUI/motion/layout surface. Do not treat this report as an absolute zero-bug guarantee.
