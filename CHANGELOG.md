# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-09-19

The first release. It was checked against the Codex source at `rust-v0.155.1`.

### Added

- **Chrome toolbar hip** that hurts while Codex is working and relaxes when Codex is ready. The tooltip shows how many sessions are working. The name comes from *coxalgia*, pain in the hip.
- **Codex hooks** in `~/.codex/hooks.json` (or `$CODEX_HOME/hooks.json`) for `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PermissionRequest`, `Stop`, `Interrupt` and `SessionEnd`.
  - `Interrupt` marks the session ready when you press Esc. The 15-minute rule remains for crashes, which send no event at all.
  - `SessionEnd` and `Interrupt` get a 3-second timeout, the most Codex allows for them. Codex runs hooks through a login shell, which can take longer than the default 1 second.
  - `SubagentStart` and `SubagentStop` aren't registered. Subagents report their parent's session ID, so their tool events already keep the parent busy, and the parent keeps working after a subagent stops.
- **Optional OS notifier** (macOS `osascript`, Linux `notify-send`, Windows PowerShell toast), with or without sound:
  - "Codex is ready", with the first line of Codex's last answer.
  - "Codex needs you", with the command waiting for approval. Codex's `PermissionRequest` has no message field, so the text is built from the tool name and its input.
- **Approval grace period.** Codex runs `PermissionRequest` hooks before it decides who approves, so they also fire for calls approved by Guardian or by an earlier "approve for this session". A request therefore counts as busy for 5 seconds (`CODEXALGIA_APPROVAL_GRACE_SECONDS`). Only if the session is still waiting after that does the hip relax and "Codex needs you" appear, sent by a detached helper so the hook returns at once. Fast calls that Codex approves itself cause no false alarm. Slow ones still can.
- **Trust-friendly installer.** Codex runs a hook only after you trust it with `/hooks`, and it remembers that trust by the hook's position in the file and a hash of its definition. The installer rewrites its own hooks in place with the same command and timeout, so reinstalling doesn't ask you to trust them again. It says whether the hooks changed and reminds you about `/hooks`.
- **Warning when hooks are off** through `[features] hooks = false` in `~/.codex/config.toml`.
- **Its own identifiers:** native host (`com.tpojka.codexalgia`), extension ID (`pdfldjccnohafaolkilhbnhjkeaineaa`), data directory and `codexalgia.pyz`, so it doesn't clash with other toolbar tools.
- The `set` command, `CODEXALGIA_HOME`, `CODEXALGIA_BUSY_STALE_SECONDS`, the unittest suite, and CI on macOS, Ubuntu and Windows.
- Landing page for codexalgia.tpojka.com in `site/`.

[1.0.0]: https://github.com/Tpojka/codexalgia/releases/tag/v1.0.0
