# Strong search with an explicit call budget

Optimize useful evidence per call, not the smallest possible answer. Every external call must answer a named question or close a named evidence gap. Read local files and already supplied sources first.

## Plan and stop

For Fast, normally start with one well-formed query or direct source read. Plan up to four remote operations (a Context7 resolve and query count separately), but stop earlier when the requested answer is supported. Do not spend the allowance just because it exists. A second independent source is valuable for contested, promotional or high-impact claims; it is not mandatory for a simple fact established by its authoritative source.

For Deep/Discovery, name missing evidence before each wave and use at most four concurrent calls. Start with a working ceiling of 12 operations; extend only when the user's task remains materially incomplete and record the expected information gain. User-specified budgets are hard limits. A budget boundary returns supported findings, explicit unknowns and useful labeled leads, never invented completeness.

Stop when the claim set is adequately supported, important contradictions resolved or disclosed, and another query is unlikely to change the answer. If two rounds yield only duplicates, change source class/language/terminology once for a specific gap rather than repeating the same query.

## Reuse and choose routes

- Maintain an in-task ledger keyed by normalized query, filters, source/provider and relevant date/version. Reuse resolved library IDs and full text already fetched. Never reuse account-scoped data across users, accounts or tasks.
- Start with 3–5 strong results. Expand recall when the question needs breadth; more hits are not automatically better.
- Read full text only when snippets cannot support the claim, details conflict, or the user requests it. Batch supported URL fetches rather than issuing one call per page.
- For a known repository/version/document, use its direct official API/page instead of searching for its name again.
- Health checks run at setup, on failure or when capability is uncertain, not before every lookup. Do not run doctor and smoke and a benchmark for each user question.
- Reuse tool schemas within the session. Do not list tools for every query.
- An authentication failure, invalid request, unavailable tool or exhausted quota is not helped by identical retries. Change route or report the exact boundary. Retry a transient network failure once only.
- Treat Jina/provider cache warnings as freshness evidence. Request a fresh source when the date matters; do not relabel cached text as live.
- Source grouping identifies duplicates and shared upstream reporting. Multiple domains in the same group do not count as independent confirmation.

## Preserve power

Chinese questions may need Chinese terminology and local sources; technical claims need primary/versioned documentation. Discovery may broaden language, adjacent terms and source types while clearly labeling hypotheses. Capability Max can use an already authorized account connector when the user needs that source. Efficiency must not silently drop these requirements.

For substantial research, report the important coverage gaps and, when actually tracked, calls used, reused results and stopping reason. Never invent a token/cost estimate from call count.

The bundled smoke runner enforces a hard request budget, coalesces identical in-flight requests and reuses responses in memory for one run only. This implementation validates the mechanism; skill-driven tool usage still follows the policy above and must keep its own evidence ledger.
