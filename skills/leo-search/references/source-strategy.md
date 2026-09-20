# Match the question to the source, not the search brand

Use this for broad research, a failing route or a comparison requiring different kinds of evidence. A simple supplied URL does not need the whole strategy.

## Reach and speed

| Need | Efficient evidence path | Typical trap |
|---|---|---|
| Known official page or exact version | Read that page directly; use Context7 to discover an unknown API/page | Resolving and searching again for a URL already supplied |
| Repository release, license, issue or commit | Existing authorized `gh api` or GitHub connector; public HTTP when no such route exists | Repeating anonymous rate-limited requests despite a working CLI |
| Institutional news or product changes | Official news index/feed, then item pages; search for discovery and missing viewpoints | Treating an indexer's date or cached homepage as today's publication record |
| Papers | arXiv record/Atom for preprint history, publisher/venue/DOI for publication, paper body for methods | Abstract alone as evidence of evaluation quality; preprint year as conference year |
| RSS/Atom | Read the feed once, preserving published versus updated and linking individual entries | Regenerating feed-parsing code or querying each headline separately |
| Market/product comparison | Vendor facts + independent field experience + explicit user criteria | Comparing unlike tiers, regions or dates; counting reseller copies as independent reviews |
| Chinese/local subject | Chinese terminology and local primary sources, then alternate terms/languages for coverage gaps | Translating an English-only search and presenting it as local research |
| Public platform discussion, video or subtitles | Relevant installed Agent Reach route or authorized connector; extract what was actually accessible | Metadata as proof of watching a video, snippets as proof of reading a whole thread |

For a batch of known public sources, `python3 <plugin-root>/scripts/fetch_sources.py URL... --output sources.json` reads HTML, JSON and RSS/Atom with up to four workers, redirect-aware request accounting, in-run duplicate reuse, source dates and explicit truncation. It starts with direct public HTTP and can try the existing child proxy once on a transport failure. It does not change settings. Use the host's Exa fetch/browser/PDF tool for dynamic pages, PDFs or thin extraction; a `status=ok` record proves retrieval, not truth. Keep private/account pages on their authorized connector.

Use API fields and feed entries when they answer the question; don't fetch the entire site. Batch the few necessary full-text reads. Search for documents by the facts they should contain, include the time/region/version constraint and the needed exclusions, and use the available tool schema (including an objective when required).

## Research depth

Build a small coverage map only for a multi-part question: criterion → claim → best source → gap. The important step is identifying what could change the user's decision.

For consequential comparisons, include:

1. **Mechanism:** what actually causes the claimed result, supported by implementation or methods.
2. **Comparison basis:** the same task, version, cost unit, population or region.
3. **Counterevidence:** the strongest relevant limitation, failure case or alternative explanation.
4. **Decision:** what follows for this user's constraints, what is inference, and what evidence would change it.

Widen search when an important branch is empty, not merely because another engine exists. Change terminology, language or source class for that branch. Follow citations to original research or announcements rather than gathering more summaries of the same item. Label plausible Discovery leads separately so useful recall is not lost to a false binary of proven/omit.

## Recovery without repeated dead ends

Remember unavailable/quota-limited providers for the current task and route around them. A 401/403/429 is not solved by sending the same query again. Record the scope of the failure; do not call the entire topic inaccessible when only one provider failed. Resolve explicit dates from original pages and keep a cached-source warning until a fresh source is actually obtained.

If a public official endpoint has a certificate or rendering failure, seek another official publication/feed or an available fetch route. Do not silently disable certificate verification or describe stale content as live. Native tool calls and shell HTTP have different capabilities; retain the successful path rather than repeatedly rediscovering it.

Stop when the requested decisions are supported and material conflicts are resolved or disclosed. Report missing source classes that could change the conclusion. One authoritative source is enough for a narrow established fact; breadth and independence matter more for contested or comparative claims.
