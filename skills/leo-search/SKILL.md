---
name: leo-search
description: Browser-free current web and technical research using Exa, Context7, Jina, GitHub CLI, RSS and already-installed Agent Reach-compatible CLIs. Use for any request to search, research, look up, verify current information, read a URL, inspect a GitHub project or compare sources when the user wants strong search without background Chrome, Playwright, Crawl4AI or headless-browser process buildup.
---

# Leo Search

Use the lightest route that can answer accurately. Keep all ordinary searching browser-free.

## Non-negotiable safety policy

1. Use remote MCP, HTTP and CLI first.
2. Never invoke Chrome, an in-app browser, Computer Use, Playwright, Patchright, Puppeteer, Selenium, Crawl4AI or browser-use for an ordinary search.
3. Never install a browser automation dependency, start a search daemon or create a heartbeat service.
4. Only use an already-open Chrome session for a logged-in social task when the user explicitly asks for that account-bound task. Reuse the current instance, open the minimum tabs, close every tab opened for the task, and confirm no new headless process remains.
5. Limit parallel remote queries to four, retry a failed route at most twice, and fall back to another non-browser route.

## Route requests

| Need | Primary route | Fallback |
| --- | --- | --- |
| Current web, news, products, people or companies | `leo-search-exa` web search | Built-in HTTP web search |
| Full text for known public URLs | Exa fetch, batching URLs | `curl https://r.jina.ai/http(s)://...` |
| Current library or framework documentation | `leo-search-context7`; resolve library ID before querying docs | Official documentation over HTTP |
| GitHub repositories, stars, releases, commits, issues or code | `gh api`, `gh repo view`, or GitHub MCP | GitHub REST API over HTTP |
| RSS/Atom | `curl` plus an installed feed parser | Direct feed HTTP |
| YouTube/Bilibili public metadata or subtitles | Installed `yt-dlp` or Agent Reach CLI | Public HTTP metadata |
| Logged-in social content | Existing OpenCLI/current Chrome only after explicit user request | Report the login boundary |

For GitHub recommendations that must be high-star, fetch the current `stargazers_count`, latest release or commit date, license and archived status. Never infer stars from search snippets.

## Research workflow

1. Clarify the evidence target from the request without asking unnecessary questions.
2. Check local or project sources first when the request concerns an installed tool or repository.
3. Search current primary sources. For technical questions, prefer official docs, repositories and papers.
4. Cross-check important claims with a second independent source when one source could be stale or promotional.
5. State uncertainty or an unavailable/account-bound source instead of silently opening a browser.
6. Cite direct URLs near supported claims and distinguish source facts from inference.
7. If any route might have delegated to a browser-capable CLI, run `../../scripts/doctor.sh` afterward and report the resource check.

## Local capability checks

Run `../../scripts/doctor.sh` for a read-only health report. Pass `--deep` only when diagnosing installed Agent Reach channels; it remains browser-free. A warning about an unavailable optional CLI is not a failure when the remote MCP routes work.
