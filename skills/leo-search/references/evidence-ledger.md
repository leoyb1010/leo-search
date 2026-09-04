# Evidence ledger

For multi-source or Deep research, normalize evidence before composing the answer. `../../../scripts/evidence_ledger.py` accepts JSONL records and emits normalized, deduplicated JSONL.

Minimum input:

```json
{"url":"https://example.com/story","title":"Source title","content":"optional extracted text"}
```

Important fields to retain or add when known:

- `published_at`: source publication time;
- `event_at`: when the reported event occurred;
- `retrieved_at`: when the source was fetched;
- `version`: exact software/product version;
- `language` and `publisher`;
- `upstream_source`: original report, paper, repository, filing or announcement;
- `claim_ids`: claims supported or contradicted;
- `support`: `supports`, `contradicts`, `context` or `unknown`.

Two URLs are not independent evidence when they copy the same upstream item. Canonical URL and content hash remove exact duplicates; the researcher must still identify syndication, mirrors and shared upstream sources.

Compose from the ledger, not raw snippets. Separate facts, inference, candidate hypotheses, contradictions and unavailable evidence.
