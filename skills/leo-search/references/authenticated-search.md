# Exa and Tavily, one small interface

Use native tools when they already meet the need. On this installation, `scripts/search.py` reads `EXA_API_KEY` / `TAVILY_API_KEY` or private `~/.config/leo-search/<provider>-api-key` files. The key never belongs in a query, repository, report, command argument or plugin cache. Missing credentials return an explicit unavailable provider; no automatic login or installation.

```sh
# A quick, bounded lookup. auto uses Exa first and Tavily only on failure/empty output.
python3 <plugin-root>/scripts/search.py search 'the required evidence' --mode fast --limit 3
# Broaden an important comparison with two providers in parallel, at most two API requests.
python3 <plugin-root>/scripts/search.py search 'the comparison and constraints' --provider both --mode auto --limit 5
# A dated research branch; use the actual requested dates and relevant source domains.
python3 <plugin-root>/scripts/search.py search 'research methods and limitations' --provider exa --mode deep --category publication --after 2025-01-01 --include arxiv.org
# Read several known sources in one provider request.
python3 <plugin-root>/scripts/search.py read URL1 URL2 --provider auto --text-characters 8000
```

Use `--output` to retain a substantial research result and inspect selected fields instead of repeatedly returning full bodies to context. `--include` and `--exclude` may repeat; `--after`/`--before` are YYYY-MM-DD. Output preserves the provider response status, result dates, provenance, content truncation and actual returned usage. Do not estimate API price from call count. Provider rankings are not comparable and two engines returning one page are one source.

## Choose effort, then inspect evidence

- `fast`: narrow facts or source discovery. Avoid optional synthesis and large text payloads when titles/snippets suffice.
- `auto`: ordinary comparisons and mixed queries. Read the few passages that drive the answer.
- `deep`: a difficult branch needing query expansion or stronger recall. Exa uses its deep search; Tavily uses advanced search. Provider synthesis never replaces reading methods, scope and contrary evidence.

`--provider both` is for a named coverage gap or important comparison, not every user question. A fallback is bounded by `--max-requests` (default 2). Authentication/quota failures are reported once, not retried. The helper preserves partial results and per-provider failures; `ok` is retrieval status, not accuracy certification.

`--fresh` requests fresh extraction from Exa. Tavily cannot promise equivalent freshness through this interface; the report states that limitation. Original page dates and actual content remain the authority. `publication` is an Exa source category; Tavily searches general sources with the same domain/date constraints, so use explicit scholarly domains where needed.

For plain public HTML/JSON/RSS, the zero-account `fetch_sources.py` often saves time and provider credits. Use provider extraction for dynamic or difficult pages and an existing PDF reader for full paper figures/tables. Keep account-bound sources on their already authorized tools.

API contracts verified 2026-09-20 against [Exa Search](https://exa.ai/docs/reference/search), [Exa Contents](https://exa.ai/docs/reference/get-contents), [Tavily Search](https://docs.tavily.com/documentation/api-reference/endpoint/search) and [Tavily Extract](https://docs.tavily.com/documentation/api-reference/endpoint/extract). No vendor SDK is required.

Provider text is bounded. `content_truncated=true` marks a reached/cropped limit; `null` means the provider did not prove completeness. Search excerpts are never automatically the whole document. Read the relevant original method/table/section before making a detailed technical or research claim.
