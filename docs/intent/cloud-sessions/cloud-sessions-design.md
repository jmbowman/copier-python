---
parent: high-level-design
prefix: SESSION
---

# Cloud sessions

## Context and Design Philosophy

A cloud session (Claude Code started on a repository, such as at claude.ai/code) begins from a fresh clone with no mise, no pinned tools and no installed skills, so the template's skill links point nowhere and `mise run check` can't run. The template renders a SessionStart hook that gives such a session the same tools and skills a local `mise run setup` would, from the same pins and lock files. Local sessions are left alone: their developers run `setup` themselves and keep their own mise.

The hook's rule is that a session always starts, and the agent always learns what's missing: any failure becomes a notice in the agent's context, never a blocked session.

## Registration

`.claude/settings.json` is repo-owned. The template renders it once, listed in `_skip_if_exists`, with one SessionStart hook and no matcher, so the hook runs on every session source (startup, resume, clear, compact and fork):

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.config/copier-python/session-start.sh"
          }
        ]
      }
    ]
  }
}
```

A repo adds its own permissions and hooks to this file. A repo that already has one adds the template's entry by hand when it onboards ([baseline files](../baseline-files/baseline-files-design.md)).

## The hook

`.config/copier-python/session-start.sh` is template-owned and executable. It:
1. exits 0 at once, with no output, unless `CLAUDE_CODE_REMOTE` is `true`;
2. installs mise at the version in its `MISE_VERSION` line into `~/.local/bin`, unless the first word of `~/.local/bin/mise --version` already equals that version (written without a `v`). Every later step calls that binary by its absolute path, whatever else is on `PATH`. It downloads `mise-v<version>-linux-x64.tar.gz` and its `SHASUMS256.txt` from mise's GitHub release `v<version>`, and verifies the archive before unpacking it. A failed download, a checksum mismatch, or a checksum file with no line for the archive is a failure of this step;
3. enters the project directory (an unset or missing `CLAUDE_PROJECT_DIR` is a failure) and runs `mise trust` there, which covers the template's fragment in `.config/mise/conf.d/`;
4. runs `mise install apm`, then `mise run skills` with `MISE_TASK_RUN_AUTO_INSTALL=false`, then `mise install` for the remaining tools. The skills need only `apm`, so they go first, and a failure in an unrelated tool still leaves the session its skills. `mise run` normally installs every missing tool before running a task, and stops if one fails; the variable turns that off;
5. appends a `PATH` line to `CLAUDE_ENV_FILE`, unless the file already holds that exact line, so later commands can call `ruff` or `lidc` directly. The line prepends `~/.local/bin` and the directories `mise bin-paths` lists. After a version change the new line is appended after the old one, and since it runs later its directories come first. An unset `CLAUDE_ENV_FILE` is a failure;
6. prints one JSON object to stdout, `{"hookSpecificOutput": {"hookEventName": "SessionStart", "reloadSkills": true}}`, and exits 0.

Claude Code discovers skills before SessionStart hooks finish, so without `reloadSkills` the skills the hook installs could be missing at the first prompt; with it, Claude Code re-scans the skill directories once the hooks complete (from Claude Code 2.1.152; verified in a cloud session on agentic_development). Claude's first response waits for SessionStart hooks, so the tools and skills exist before the agent's first turn. Stdout carries only the JSON object; every command the script runs sends its output to stderr.

On any failure, the script runs no later step. It prints the same object with an `additionalContext` field naming the step that failed (such as "installing mise", a mise command, or the missing `CLAUDE_PROJECT_DIR` or `CLAUDE_ENV_FILE`), what is missing, and mise's absolute path (so the agent can still reach mise when the `PATH` step never ran), and exits 0. Claude Code adds a SessionStart hook's output to Claude's context only when the hook exits 0; after a non-zero exit only the user sees a notice, and the session goes ahead either way. The notice therefore reaches the agent that would otherwise hit the missing tools, and the agent tells the user. The object still asks for a re-scan, because a failure after the skills step leaves them installed. An `EXIT` trap prints the object, with a notice, and exits 0, even when the script stops outside its defined steps; a flag set by the normal print keeps the trap from printing a second object. The script runs under `bash` with `set -uo pipefail`, downloads with `curl -fsSL`, verifies with `sha256sum`, and escapes the notice for JSON with `sed`, as agentic_development's own hook does.

Each session event reinstalls the skills, because `skills` removes the installed directory first. From APM's cache that costs about a second, and it keeps the installed skills exactly what the lock file records.

A fresh container pays about 30 seconds; a reused one about a second, since each step skips what's already installed. Claude Code's default 600-second timeout for a command hook leaves ample room, so the registration sets none. The cloud environment's network policy must allow GitHub (releases and git), PyPI and any other host the repo's own pinned tools come from.

## The hook's mise version

`MISE_VERSION` equals the `version:` input of the `jdx/mise-action` step in this repo's own CI workflow. This repo's `.github/renovate.json` adds a regex manager that reads `MISE_VERSION=` in `template/.config/copier-python/session-start.sh` as the `jdx/mise` dependency with datasource `github-release-attachments`, the one Renovate's github-actions manager reports for that `version:` input. Updates of one dependency with the same datasource and version share a branch, so a mise release bumps both in one PR. If they ever split, a test fails both PRs rather than letting one merge.

A consumer's cloud sessions therefore run the mise that was current when its template release was tagged, while its CI runs the mise in the check workflow it pins. The two can differ by the gap between the consumer's template and workflow updates. Both are at or above the fragment's `min_version`, so the checks behave the same; a different mise can rewrite `mise.lock` in small ways, which leaves an uncommitted change in the session.

## Testing

pytest tests in `tests/` cover, in a rendered consumer:
- the registration in `.claude/settings.json`, and that `_skip_if_exists` lists it;
- the hook outside a cloud session: it exits 0 and prints nothing;
- the hook in a cloud session, with a stub `mise` in a temporary home directory: it prints exactly one JSON object with `reloadSkills` true and exits 0; when the stub fails a step, the object's `additionalContext` names that step, and no later step runs;
- that the rendered script is executable.

In this repo, they cover `MISE_VERSION` equal to the CI workflow's mise-action `version:` and at or above the fragment's `min_version`, and the regex manager in this repo's Renovate config: its file pattern matches the hook, its match string captures `MISE_VERSION`, and it names `jdx/mise` with datasource `github-release-attachments`, the dependency agentic_development verified Renovate's github-actions manager reports for mise-action's `version:` input. This repo doesn't pin the Renovate CLI, so the tests read the config as FILES-008's do, rather than running Renovate's extraction.

A real cloud session is checked by hand: a session on a consumer branch carrying the hook lists the template's skills at its first turn, and `mise run check` passes in it.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| Cloud setup | A template-owned SessionStart hook | The cloud environment's setup script | The hook is reviewed, versioned and updated with the template; a setup script is cached but lives outside the repo, in each user's environment settings |
| Registration ownership | Repo-owned `.claude/settings.json`, rendered once | Template-owned `settings.json` | Repos keep their own permissions and hooks there, and Claude Code can't include a second settings file. **Cost:** a change to the registration reaches existing consumers only by hand |
| The hook's mise version | Its own `MISE_VERSION`, kept equal to this repo's CI mise by a shared Renovate dependency and a test | Reading the version from the consumer's pinned check workflow at session start; the version in the check workflow at `agentic_development_ref` | No network fetch or YAML parsing in the hook, and no reliance on the shape of the repo-owned CI stub; one Renovate PR per mise release. A version tied to `agentic_development_ref` would need two independent bumps to land together. **Cost:** a consumer's cloud sessions and CI can run different mise releases |
| Hook sources | No matcher: every source | `startup` only | A resumed or cleared session in a reused container costs about a second, and one that lost its tools gets them back |
| Making installed skills visible | The hook returns `reloadSkills: true` | `/reload-skills` at the start of each session; relying on the skills file watcher | Skill discovery runs before the hook finishes; a manual step would be forgotten |
| Reporting a failure | `additionalContext` in the JSON output, exit 0 | A non-zero exit; plain text on stdout | Only an exit-0 hook's output reaches Claude. Plain text can't share stdout with the JSON object Claude Code parses |
| Install order | `apm`, then skills, then the other tools | One `mise install` first | An unrelated tool's failure doesn't cost the session its skills |
| Reinstalling on every event | `skills` runs, removing and reinstalling, on every session event | Skipping the install when the lock file hasn't changed | About a second from APM's cache; skipping would need the hook to keep state about what it installed |
| Integrity of the mise download | The release's own `SHASUMS256.txt` | A hash pinned in the hook | Catches a corrupt download without a second value for Renovate to update; it doesn't defend against a compromised release, as a pinned hash would |

## Open Questions & Future Decisions

### Deferred
1. Other platforms for the hook, if cloud sessions run on anything but Linux x86-64.
2. Moving the mise-version regex manager into the shared preset, if several templates ship the hook.

## References

- HLD: Key Design Decisions, "A template-owned session hook with a repo-owned registration".
- Claude Code [hooks](https://code.claude.com/docs/en/hooks) (SessionStart output, `reloadSkills`, `CLAUDE_ENV_FILE`) and [skills](https://code.claude.com/docs/en/skills); [mise releases](https://github.com/jdx/mise/releases).
- agentic_development's own session hook, the working model for this one: its `docs/intent/repo-setup/repo-setup-design.md`.
