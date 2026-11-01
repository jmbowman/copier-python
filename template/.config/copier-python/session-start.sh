#!/bin/bash
# SessionStart hook owned by the copier-python template, registered in .claude/settings.json.
# In a cloud session it installs mise, the template's skills and the pinned tools, so the
# session has what a local `mise run setup` gives. It does nothing in local sessions.
# Stdout carries only the JSON object Claude Code reads; everything else goes to stderr.
set -uo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Renovate keeps this equal to the jdx/mise-action `version:` in the template repo's CI.
MISE_VERSION=2026.10.23
finished=false
mise="~/.local/bin/mise"

finish() {
  # $1: empty on success, else a notice for the agent.
  finished=true
  if [ -z "$1" ]; then
    printf '{"hookSpecificOutput": {"hookEventName": "SessionStart", "reloadSkills": true}}\n'
  else
    # JSON-escape backslashes and quotes, and turn tabs and newlines into spaces.
    notice=$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\t\n' '  ')
    printf '{"hookSpecificOutput": {"hookEventName": "SessionStart", "reloadSkills": true, "additionalContext": "%s"}}\n' "$notice"
  fi
  exit 0
}

fail() {
  # $1: the step that failed; $2: what is missing as a result.
  finish "Session setup failed at: $1. Missing: $2. mise is at $mise. Tell the user, and see the hook's stderr (claude --debug) for details."
}

on_exit() {
  # Whatever stops the script, stdout still carries the one object Claude Code reads.
  [ "$finished" = true ] || finish "Session setup stopped unexpectedly. Tools and skills may be missing. mise is at $mise. Tell the user, and see the hook's stderr (claude --debug) for details."
}
trap on_exit EXIT
# A signal ends the script through the EXIT trap, which reports and exits 0.
trap 'exit 1' TERM INT HUP

[ -n "${HOME:-}" ] || fail "finding HOME (it is unset)" "mise, every pinned tool and the template's skills"
bin_dir="$HOME/.local/bin"
mise="$bin_dir/mise"

install_mise() {
  local tmp asset base
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"; trap - RETURN' RETURN
  base="https://github.com/jdx/mise/releases/download/v$MISE_VERSION"
  asset="mise-v$MISE_VERSION-linux-x64.tar.gz"
  curl -fsSL -o "$tmp/$asset" "$base/$asset" || return 1
  curl -fsSL -o "$tmp/SHASUMS256.txt" "$base/SHASUMS256.txt" || return 1
  grep -q "  ./$asset\$" "$tmp/SHASUMS256.txt" || { echo "no checksum line for $asset" >&2; return 1; }
  (cd "$tmp" && grep "  ./$asset\$" SHASUMS256.txt | sha256sum -c --quiet -) || return 1
  tar -xzf "$tmp/$asset" -C "$tmp" || return 1
  install -D -m 0755 "$tmp/mise/bin/mise" "$mise"
}

current=$("$mise" --version 2>/dev/null | awk '{print $1; exit}')
if [ "$current" != "$MISE_VERSION" ]; then
  install_mise >&2 || fail "installing mise $MISE_VERSION" "mise, every pinned tool and the template's skills"
fi

[ -n "${CLAUDE_PROJECT_DIR:-}" ] && CDPATH= cd "$CLAUDE_PROJECT_DIR" >&2 \
  || fail "entering CLAUDE_PROJECT_DIR" "every pinned tool and the template's skills"
"$mise" trust --quiet >&2 || fail "mise trust" "every pinned tool and the template's skills"
"$mise" install apm >&2 || fail "mise install apm" "every pinned tool and the template's skills"
# Without this, `mise run` first installs every missing tool and stops if any fails.
MISE_TASK_RUN_AUTO_INSTALL=false "$mise" run skills >&2 \
  || fail "mise run skills" "every pinned tool and the template's skills"
"$mise" install --quiet >&2 || fail "mise install" "some pinned tools (the template's skills are installed)"

[ -n "${CLAUDE_ENV_FILE:-}" ] || fail "writing PATH (CLAUDE_ENV_FILE is unset)" "PATH entries for mise and the pinned tools"
paths=$("$mise" bin-paths | paste -sd: -) || fail "mise bin-paths" "PATH entries for mise and the pinned tools"
[ -n "$paths" ] || fail "mise bin-paths (it listed no tools)" "PATH entries for mise and the pinned tools"
line="export PATH=\"$bin_dir:$paths:\$PATH\""
if ! grep -qxF "$line" "$CLAUDE_ENV_FILE" 2>/dev/null; then
  echo "$line" >> "$CLAUDE_ENV_FILE" || fail "writing PATH to CLAUDE_ENV_FILE" "PATH entries for mise and the pinned tools"
fi

finish ""
