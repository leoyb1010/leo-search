# Round 4 — full product matrix with ambiguous state and provenance

Status: accepted in the declared local synthetic scope. Starting checkpoint 389fad2, accepted Round 3 tree f7600d7fcf06b31bb2f7a11f48004342f386bbc7. Publication and remote CI remain pending for these later local rounds.

## Full fresh audit

Revisited CLI entrypoints, installer recovery, provider and native message identity, evidence merging, source/version/freshness routing policy, budget/error/cancellation handling, report persistence and manifest references. Re-executed the entire prior matrix, including all role journeys and adverse cases from Rounds 1–3. Current aggregate: 101/101 tests, doctor fixtures, all shell sh -n, Python compileall and both whitespace checks. This pass also tests a genuine local Git worktree's gitfile and real rev-parse; only pull and installation are stubbed, with exact ff-only calls verified.

## New seam and fix

Ambiguous duplicate JSON fields were accepted with silent last-value-wins behavior. The actual old marketplace CLI discarded an unrelated plugin registration when a second plugins key overrode the first; a backup existed, but the active marketplace still lost that entry. A duplicate response ID likewise let a mismatched identity be overwritten into a matching one. Evidence URLs and provider provenance suffered the same ambiguity.

The common decoder now rejects duplicate fields, including escaped equivalent keys and nested objects, before any side effect. Identical keys in separate objects remain valid. The evidence CLI returns exit 2 and no partial stdout; marketplace keeps original bytes without a new backup; initialize/Reader/native contracts fail closed. Existing strict Unicode/finite/depth checks and every healthy pipeline remain in regression.

Current evidence: round4-before.txt, test_five_round_ambiguous_data.py, round4-tests.txt, round4-doctor.txt. Only disposable, local, synthetic data was used.

## Limits

Terminal output, diagnostics, file paths, rollback and process behavior are the product presentation tested here. There is no GUI or motion surface. Live provider uptime, OAuth readiness, actual account-bound research, advanced-mode semantic research quality and real plugin installation are not claimed. The 20-case subprocess benchmark verifies retrieval contracts, not answer accuracy. No zero-bug claim.
