# Round 3 — complete role matrix with host-environment and checkout combinations

Status: accepted within the declared local synthetic coverage; local Round 2 checkpoint be6695723e8738514829517c3fe9e4b86a3de17f, tree 9eb8b0b930f0bdd44a2428de301c4158dcac115b. Publication and exact-commit CI validation are pending.

## Full fresh pass

Re-read all executable entrypoints, all four routing/efficiency/evidence/benchmark references and manifests. Re-executed the complete matrix: ordinary/scoped/20-case/fallback research CLI, provider protocol/source/freshness fixtures, bounded and single-flight requests, native inventory/optional search/framing/cancellation, analyst evidence preservation/conflicts/strict JSON, output atomicity/recovery, doctor human/JSON/deep, portable installation and marketplace backup/restore/concurrency, bootstrap/update/proxy. Current aggregate is 97/97; doctor, all shell syntax, Python compilation and staged/worktree whitespace checks pass. New synthetic states below supplement rather than replace every previous role path.

## New user-facing findings

1. The proxy wrapper set only uppercase environment variables. An existing lowercase http_proxy/https_proxy/all_proxy could still select the previous route despite LEO_SEARCH_PROXY. Actual subprocess environment reproduction is round3-before.txt. The wrapper now supplies both cases consistently to the child, preserving NO_PROXY/no_proxy exclusions and leaving the calling process unchanged. Tests check configured-file selection, explicit override, no-selected-proxy preservation, spaces in arguments, exact child exit and missing-command usage.
2. Bootstrap/update treated `.git` as necessarily a directory, rejecting Git worktree checkouts with a gitfile. Both now require an existing `.git` plus Git's read-only rev-parse verification. Valid gitfiles proceed through the same ff-only path; invalid gitfiles stop before pull/install. Existing repository-origin checks and failed-pull preservation remain.
3. Invoking with_proxy.sh without a command previously returned success without work. It now reports a short usage line on stderr and exit 64.

Official curl environment contract: https://everything.curl.dev/usingcurl/proxies/env.html. It documents lowercase http_proxy and scheme-specific precedence; this audit does not claim an external proxy connection was tested.

## Evidence and limits

round3-tests.txt, round3-doctor.txt, test_five_round_operator_shell.py and round3-before.txt are current-round evidence. Fake git/install/provider/native executables run as real child processes under disposable HOME, so no actual plugin installation, network pull, credentials or user configuration changes occurred. GUI/motion/layout do not apply. Real provider availability, OAuth, account-bound sessions and semantic quality of Deep/Discovery/Capability Max remain outside verified scope; the 20-case runner only checks retrieval contracts. No zero-bug claim.
