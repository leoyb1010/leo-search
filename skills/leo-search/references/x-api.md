# X official API v2

Use for requested public X discussions, original posts, author timelines or historical context. This route reads public data only. A post proves what its author said, not that the statement is true; engagement is not representativeness.

The local helper reads `X_BEARER_TOKEN`, `TWITTER_BEARER_TOKEN`, or private `~/.config/leo-search/x-bearer-token`. It does not read browser cookies. The key/token belongs outside plugin source and reports. Configure the app credential separately; missing access is explicit, never silently replaced by scraping.

```sh
python3 <plugin-root>/scripts/x_api.py search '(retrieval OR RAG) lang:en -is:retweet' --limit 10
python3 <plugin-root>/scripts/x_api.py search 'from:NASA' --archive --start 2025-01-01T00:00:00Z --end 2025-01-03T00:00:00Z --limit 10
python3 <plugin-root>/scripts/x_api.py post POST_ID_OR_URL
python3 <plugin-root>/scripts/x_api.py user NASA
python3 <plugin-root>/scripts/x_api.py timeline NASA --limit 10
```

Recent search covers the last seven days; `--archive` uses the account's full-archive access. Check the actual response before claiming availability. Narrow with author, language, phrases and dates. Use `conversation_id:ID` to inspect relevant replies, but do not claim a complete thread from a capped search.

Default: one page of 10 posts, with explicit `--pages` (1–3), `--limit` (10–100) and `--max-requests` (1–6). Do not turn an ordinary question into a large account crawl. The output records requests, returned posts, next-page availability, rate-limit headers and partial failures. Exact monetary charges come from the X Developer Console; don't invent dollar cost from response count. No retries on auth/quota failures and no hidden pagination.

Keep original URLs, authors, timestamps, conversation references and returned long-post text. Missing/deleted/protected posts remain missing; do not fill them from guesses. Search engine snippets can help discover a post, but use this API or another actually accessible original for quotation and context.

Integrate social research with other source classes: announcement authors for first-hand statements, independent field experience for use, documentation or experiments for technical claims. A set of popular posts is not a population survey. Separate recurring observations, isolated anecdotes, disagreement and unanswered questions.

Official contracts checked 2026-09-20: [introduction](https://docs.x.com/x-api/introduction), [search](https://docs.x.com/x-api/posts/search/introduction), [authentication](https://docs.x.com/fundamentals/authentication/oauth-2-0/bearer-tokens), [pricing](https://docs.x.com/x-api/getting-started/pricing). Account capability and prices must be rechecked when relevant.
