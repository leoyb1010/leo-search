# Input and output compatibility

The supported host scope stays Python 3.11+, macOS or Linux. No GUI, daemon, account setup or automatic provider-auth change was added.

- Ordinary valid JSON, Chinese/emoji text, finite floating-point values (including ±1e308 and negative zero), integers, distinct nested objects, JSONL ordering and existing report schemas remain compatible
- Provider/imported JSON now rejects duplicate object fields, including escaped equivalent keys; keep one unambiguous value per field
- NaN/Infinity literals and finite-grammar numbers that overflow to infinity (such as 1e400) are rejected; use null or a representable finite value
- Unpaired Unicode surrogate escapes are rejected; replace them with valid Unicode text
- JSON nested deeper than 64 levels is rejected; flatten unnecessary metadata nesting
- Invalid ledger input exits 2 before emitting a partial batch. Invalid marketplace input exits 1 and preserves the source file. Invalid provider replies are reported as unavailable, not successful retrieval
- Report-file publication is atomic and UTF-8. On destination failure, complete JSON remains on stdout with exit 2. Use a writable regular path or retain stdout; do not repeat research solely to recover its output. Symlink report destinations are rejected
- Explicit proxy selection sets uppercase and lowercase proxy variables only in the child command. Existing no-proxy exclusions remain. With no selected proxy, inherited variables remain as supplied
- Verified Git worktree gitfiles are accepted by bootstrap/update; updates remain ff-only and failed checks/pulls never proceed to installation
- Interactive process-group Ctrl-C/HUP/TERM cancellation of doctor --json returns 130/129/143 respectively, cleans the temporary report, and does not print a misleading partial JSON/traceback

No live provider/OAuth/account-bound session or actual plugin installation was exercised by these offline tests. Research-mode semantic quality is not inferred from protocol contracts or the twenty-case retrieval fixture benchmark.
