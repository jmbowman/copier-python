# Cloud sessions specs

Design: [cloud-sessions-design.md](cloud-sessions-design.md). "The hook" is the template-owned `.config/copier-python/session-start.sh` in a consumer rendered by the copier-python template. "A cloud session" means the hook runs with `CLAUDE_CODE_REMOTE` set to `true`. "The hook's mise" is `~/.local/bin/mise`. "The JSON object" is `{"hookSpecificOutput": {"hookEventName": "SessionStart", "reloadSkills": true}}`, optionally with an `additionalContext` string in `hookSpecificOutput`.

## Registration

- [x] **SESSION-REG-001**: When the copier-python template is rendered, the `.claude/settings.json` it writes shall parse as JSON equal to an object whose only key, `hooks`, holds only a `SessionStart` list with one entry, with no `matcher`, whose `hooks` list holds one hook with `type` `command` and `command` `"$CLAUDE_PROJECT_DIR"/.config/copier-python/session-start.sh`.
- [x] **SESSION-REG-002**: When the copier-python template is rendered, the hook shall be an executable regular file.

## The hook

- [x] **SESSION-HOOK-001**: When `CLAUDE_CODE_REMOTE` is not `true`, the hook shall exit 0, print nothing to stdout, and run no `mise` command.
- [x] **SESSION-HOOK-002**: In a cloud session, when the first whitespace-separated word of the hook's mise's `--version` output equals the hook's `MISE_VERSION`, the hook shall not download mise.
- [x] **SESSION-HOOK-003**: In a cloud session, when the hook's mise is missing or reports another version, the hook shall download `mise-v<MISE_VERSION>-linux-x64.tar.gz` and `SHASUMS256.txt` from mise's GitHub release `v<MISE_VERSION>`.
- [x] **SESSION-HOOK-010**: In a cloud session, the hook shall install the downloaded archive's `bin/mise` as the hook's mise only if the archive's SHA-256 matches the line for that archive in the downloaded `SHASUMS256.txt`, and shall treat a mismatch, a missing line or a failed download as a failed step named "installing mise".
- [x] **SESSION-HOOK-004**: In a cloud session, the hook shall run, in order and with `CLAUDE_PROJECT_DIR` as the working directory, the hook's mise with `trust`, `install apm`, `run skills` (with `MISE_TASK_RUN_AUTO_INSTALL=false`) and `install`, each by the absolute path of the hook's mise.
- [x] **SESSION-HOOK-005**: In a cloud session, after the install steps succeed, the line the hook writes to `CLAUDE_ENV_FILE` shall be `export PATH="<home>/.local/bin:<dirs>:$PATH"`, where `<home>` is the expanded home directory, `<dirs>` is the output of `mise bin-paths` joined with `:`, and `$PATH` is literal.
- [x] **SESSION-HOOK-011**: In a cloud session, the hook shall append that line to `CLAUDE_ENV_FILE` only when the file doesn't already hold that exact line.
- [x] **SESSION-HOOK-006**: In a cloud session, when every step succeeds, the hook's stdout shall parse as exactly one JSON object, equal to the JSON object without `additionalContext`, and the hook shall exit 0.
- [x] **SESSION-HOOK-007**: If a step fails in a cloud session, then the hook shall run no later step, its stdout shall parse as exactly one JSON object, the JSON object with an `additionalContext` naming the failed step and the absolute path of the hook's mise, and the hook shall exit 0.
- [x] **SESSION-HOOK-008**: If, in a cloud session, `CLAUDE_PROJECT_DIR` is unset or not a directory when the hook enters it, or `CLAUDE_ENV_FILE` is unset when the hook writes `PATH`, then the hook shall treat that as a failed step named after the variable.
- [x] **SESSION-HOOK-009**: If the hook exits in a cloud session without having printed the JSON object, then an `EXIT` trap shall print the JSON object with an `additionalContext` notice, and the hook shall exit 0.
- [x] **SESSION-HOOK-012**: The hook shall print no more than one JSON object in any run.

## The hook's mise version

- [x] **SESSION-MISE-001**: The hook's `MISE_VERSION` value, a version with no `v` prefix, shall equal the `version` input of the `jdx/mise-action` step in the copier-python repo's `.github/workflows/ci.yml`.
- [x] **SESSION-MISE-002**: The hook's `MISE_VERSION` shall be no older than the copier-python fragment's `min_version`.
- [x] **SESSION-MISE-003**: The copier-python repo's `.github/renovate.json` shall define a regex manager whose file pattern matches `template/.config/copier-python/session-start.sh`, whose match string captures the hook's `MISE_VERSION` value, and whose dependency name is `jdx/mise` with datasource `github-release-attachments`.
