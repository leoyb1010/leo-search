# Leo Search

Leo Search is a Codex plugin for current web and technical research without creating local browser automation processes. It bundles remote MCP routes and a routing skill:

- Exa for current web search and clean URL extraction
- TinyFish for free live web/news/paper search and browser-rendered public URL extraction
- Context7 for current library documentation
- Jina Reader, GitHub CLI, RSS, `yt-dlp` and Agent Reach-compatible CLIs as browser-free fallbacks
- Existing Chrome only for an explicitly requested logged-in task; tabs opened for the task must be closed

It does not install Playwright, Patchright, Puppeteer, Selenium, Crawl4AI or a heartbeat/daemon. TinyFish renders dynamic public pages remotely and therefore creates no local browser process. Its paid browser automation tool is intentionally excluded from Leo Search's local Codex tool policy. If an explicitly requested logged-in task uses the existing OpenCLI bridge, the skill closes its task tabs and stops that bridge afterward.

## Install on another Mac or Linux device

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/leoyb1010/leo-search/main/scripts/bootstrap.sh)"
```

The installer clones to `~/plugins/leo-search`, preserves other personal Marketplace entries, installs `leo-search@personal`, and runs a read-only resource check. Start a new Codex task after installation so the new skill and MCP tools are loaded.

No API key is required for the default routes. TinyFish uses one-time OAuth and requires a TinyFish account; Search and Fetch are free. Authenticate from Codex's MCP server settings when prompted. Service-side limits may apply, and credentials remain outside this repository.

## Verify

```bash
~/plugins/leo-search/scripts/doctor.sh
~/plugins/leo-search/scripts/doctor.sh --deep
```

`--deep` also runs Agent Reach's own channel doctor when Agent Reach is installed. Neither mode opens a browser.

The normal check performs real MCP `initialize` requests for Exa and Context7, validates TinyFish's OAuth metadata and Jina over HTTP, reports RSS and installed CLI capabilities, and checks for browser-process buildup. TinyFish authentication itself is verified from Codex after OAuth. The deep check also verifies GitHub authentication.

For the personal installation, keep TinyFish restricted to the two free read-only tools:

```toml
[plugins."leo-search@personal".mcp_servers."leo-search-tinyfish"]
enabled = true
default_tools_approval_mode = "approve"
enabled_tools = ["search", "fetch_content"]
```

Run the local regression and lint checks before publishing changes:

```bash
./tests/doctor_test.sh
shellcheck scripts/*.sh tests/*.sh
```

## Optional account-bound channels

Install the optional Agent Reach-compatible tools without importing cookies:

```bash
agent-reach install --env local --channels all
```

OpenCLI still requires the user to install and enable its Chrome extension. Twitter, Xueqiu and other logged-in sources require an explicit cookie import or an already authenticated browser session. Never import cookies implicitly, and stop the OpenCLI daemon after each account-bound task:

```bash
opencli daemon stop
```

## Update

```bash
~/plugins/leo-search/scripts/update.sh
```

## Architecture

```mermaid
flowchart LR
  U["Research request"] --> R["Leo Search routing skill"]
  R --> E["Exa remote MCP"]
  R --> T["TinyFish Search / Fetch remote MCP"]
  R --> C["Context7 remote MCP"]
  R --> H["HTTP and local CLI fallbacks"]
  H --> J["Jina Reader"]
  H --> G["GitHub / RSS / yt-dlp"]
  R -. "explicit logged-in task only" .-> X["Existing Chrome instance"]
  E --> A["Cited answer"]
  T --> A
  C --> A
  J --> A
  G --> A
  X --> A
```

## Privacy and resource boundaries

Queries and fetched URLs sent to remote MCP services are processed by those providers. Do not include secrets, credentials, private source code or private URLs in search/fetch requests. TinyFish in Leo Search is limited to public Search and Fetch; paid automation, Vault and saved browser profiles remain outside this plugin. Ordinary research must remain on HTTP/MCP/CLI routes. If an account-bound task truly needs the existing Chrome session, request that explicitly and verify tab/process cleanup afterward.

## License

MIT
