# Sources

The routes to search. Select every route whose trigger matches a signal in the need, and give each selected route a ledger state: searched, excluded with a reason, or unavailable with a diagnosis. "Always" routes are selected for every software need. The first two rows are covered by steps 0 and 4: record them as searched with what you checked, and don't count them toward a quick pass's two searched routes.

| Route | Trigger | Good for | Tactics |
|---|---|---|---|
| The stack itself | Always | Features the repo's existing tools, platform or dependencies already have | Read the manifests and tool configs; check the pinned versions' docs and changelogs for the need |
| Earlier notes and decisions | Always | Recommendations already made, and candidates already dismissed | Look in the repo's notes directory, `docs/decisions/` or ADRs; search for the topic's terms |
| GitHub repository search | Always | Tools, libraries and applications in any language | `gh search repos "<terms>" --sort updated`, or the API's `search/repositories?q=<terms>+pushed:>YYYY-MM-DD`. Use 2-3 word queries: every word must match the name or description, so longer phrases return almost nothing. Vary the wording; read topics and tags on good hits |
| GitLab and Codeberg search | Always | Projects hosted outside GitHub, common for self-hosted, European and some Linux-ecosystem software | GitLab: `https://gitlab.com/api/v4/projects?search=<terms>&order_by=last_activity_at`, and `&topic=<tag>` for topics. Codeberg: `https://codeberg.org/api/v1/repos/search?q=<terms>&sort=updated`. Both work without authentication for public projects |
| GitHub topics | Always | Clusters of related projects | `topic:<tag>` searches, using tags found on serious candidates |
| GitHub code search | Snowball, when authenticated | Awesome lists and READMEs that mention a candidate; projects that depend on it | `gh search code "<candidate name>" --filename README.md`; dependents of a library |
| npm | Always, as prior art even for non-JS needs | CLI tools and libraries, often the first to exist | `https://registry.npmjs.org/-/v1/search?text=<terms>` |
| PyPI | Always | Python libraries, plus applications, services and tools of every kind that happen to be written in Python | Web search `site:pypi.org <terms>`; `https://pypi.org/pypi/<name>/json` for a known name |
| crates.io | Always | Rust libraries, plus applications, services and tools of every kind that happen to be written in Rust | `https://crates.io/api/v1/crates?q=<terms>` |
| Language registries | Another named language (Go, Java, Ruby, .NET and others) | Libraries in that language | pkg.go.dev, Maven Central, RubyGems, NuGet search |
| Cross-language equivalents | A strong candidate exists in another language | The same tool in the target language | Search "<candidate> for <language>", "<candidate> port"; packagepal.dev-style equivalence lists |
| Awesome lists | Always | Curated lists on the topic, and lists that mention candidates | Search "awesome <topic>"; GitHub code search for lists naming a serious candidate. A candidate's own "alternatives" or "comparison" docs page is often the best curated list in a niche |
| alternativeto.net | An end-user tool or app | "Alternatives to X" for a known candidate | `alternativeto.net/software/<name>/`, which often returns 404 or blocks automated reads; fall back to web search "alternatives to <candidate>" |
| General web search | Always | Comparisons, blog posts, "X vs Y", issue threads | Several phrasings of the need; the vocabulary candidates use |
| Hosted services | A hosted service or SaaS would fit | Commercial and hosted options | Vendor docs and pricing; limitations from these are docs only |
| Skill directories | Agent skill or plugin | Published agent skills | skills.sh's JSON search, `https://skills.sh/api/search?q=<terms>` (unversioned; its install counts show only popularity); other directories via web search |
| Claude Code plugin marketplaces | Agent skill or plugin | Plugins and the skills they bundle | Anthropic's plugin directory (`claude.com/plugins`); GitHub code search for `.claude-plugin/marketplace.json` files naming the topic |
| MCP Registry | MCP server | Published MCP servers | `https://registry.modelcontextprotocol.io/v0/servers?search=<term>`, one word per query: multi-word phrases return nothing |
| Anthropic's skills repo | Agent skill | Reference skills | `github.com/anthropics/skills`, read in place |
| Awesome lists for agent skills | Agent skill, plugin or MCP server | Curated skills, plugins and servers | Search "awesome claude skills", "awesome agent skills", "awesome mcp servers" |
| GitHub topics for agent skills | Agent skill, plugin or MCP server | Skills published outside catalogs | `topic:agent-skills`, `topic:claude-skills`, `topic:mcp-server` with the need's terms |

Catalogs are used through their websites or APIs only. Never install a catalog's own finder skill or CLI to search it.

## When a route fails

Retry once. If it still fails, diagnose why (authentication, rate limit, network, no such tool) and record the route as unavailable with that diagnosis. An unavailable route blocks only a **build** verdict.
