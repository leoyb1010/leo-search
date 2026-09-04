# Release checks and recovery

- Preserve dirty work before modification. Baseline `v1.3.0` records the formerly uncommitted installed version.
- Run `python3 -B -m unittest discover -s tests -v`, `sh tests/doctor_test.sh`, and `git diff --check`.
- Run bounded smoke/native probes only when routes changed; retain failures and actual fallback evidence. Never equate initialization with retrieval or retrieval with semantic accuracy.
- Update changelog/base version, validate plugin and skill, apply the installed plugin-creator cachebuster helper and reinstall using `codex plugin add leo-search@personal` on the existing local marketplace.
- Verify cache contents and read back actual tool visibility after installation. New conversations load updated skills/tools.
- Commit reviewed files and push main plus the selected version tag. No credentials, private user data, node_modules or shell logs.
- For rollback, inspect a separate checkout of a retained tag and reinstall its known-good source only when rollback is requested. Never reset a dirty checkout.
