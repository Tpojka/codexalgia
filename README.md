# Codexalgia

> [!IMPORTANT]
> **Archived.** Codexalgia is now part of [Perturbation](https://perturbation.tpojka.com) ([repository](https://github.com/Tpojka/perturbation)), one Chrome toolbar lamp for Claude Code, Codex CLI, GitHub Copilot CLI, Antigravity CLI, opencode, Goose and Qwen Code. Perturbation's installer finds Codexalgia and offers to remove it. This repository stays online, read-only, for reference.

A Chrome toolbar button that shows whether OpenAI's Codex CLI is working, with optional desktop notifications. It works on macOS, Ubuntu/Linux and Windows.

| Icon | Meaning |
| --- | --- |
| <img src="extension/icons/hip-pain-48.png" width="24"> | Hip in pain: Codex is working on a task |
| <img src="extension/icons/hip-ok-48.png" width="24"> | Hip without pain: Codex is ready (finished, interrupted, or waiting for your approval) |
| <img src="extension/icons/hip-unknown-48.png" width="24"> | Grey: the native host isn't connected (run the installer) |

Hover over the icon to see how many sessions are working.

The name is Codex + *-algia* (pain), after *coxalgia*, pain in the hip.

## Install

Requires Python 3.9 or newer, Google Chrome and Codex CLI. macOS ships Python as `/usr/bin/python3`. On Windows, install it from python.org or with `winget install Python.Python.3.12`.

```sh
./install.sh        # macOS / Ubuntu
install.cmd         # Windows
```

The installer detects your OS and asks what to install:

```
  1) Chrome extension
  2) Chrome extension + OS notifier
  3) Nothing (exit)
```

If you choose 2, it also asks `Play a sound with notifications? [Y/n]`.

To skip the prompts, pass the choice directly: `python3 -m codexalgia.install 2` (with sound) or `python3 -m codexalgia.install 2 --no-sound`.

Everything is copied into a per-user data directory, so you can move or delete the repository afterwards:

| OS | Data directory |
| --- | --- |
| macOS | `~/Library/Application Support/Codexalgia` |
| Ubuntu/Linux | `~/.local/share/codexalgia` (or `$XDG_DATA_HOME/codexalgia`) |
| Windows | `%LOCALAPPDATA%\Codexalgia` |

Then, once:

1. Open `chrome://extensions` and turn on **Developer mode**.
2. Click **Load unpacked** and select the `extension` folder inside the data directory. The installer prints the exact path.
3. Pin **Codexalgia** to the toolbar.
4. Restart any running Codex sessions, then type `/hooks` in Codex and **trust** the Codexalgia hooks.

Step 4 matters: Codex doesn't run a hook until you've reviewed and trusted it. Until then the hip stays relaxed.

Running the installer again is safe. It updates the installed copy, leaves your other hooks alone, and backs up `~/.codex/hooks.json` to `hooks.json.codexalgia.bak` before changing it. It rewrites its own hooks in place with the same command, so Codex keeps trusting them and you don't need `/hooks` again. The installer says whether the hooks changed. To change the notifier later, see [Notifier settings](#notifier-settings).

If you've set `CODEX_HOME`, the hooks go to `$CODEX_HOME/hooks.json` instead. If `~/.codex/config.toml` turns hooks off (`hooks = false` under `[features]`), the installer warns you.

## OS notifier

When the OS notifier is on, you get a notification when Codex finishes a turn or needs your approval. The title includes the project folder name.

| When | Title | Text |
| --- | --- | --- |
| Codex finishes a turn | Codex is ready · *project* | The first line of Codex's last answer |
| Codex asks for approval | Codex needs you · *project* | The command it wants to run, or the tool it wants to use |

"Codex needs you" comes 5 seconds after the request, and only if Codex is still waiting. See [Approvals](#approvals) for why.

How each OS shows them:

- **macOS:** built-in `osascript`, with the Glass sound. The first time, allow notifications for **Script Editor** in System Settings → Notifications.
- **Ubuntu/Linux:** `notify-send` (`sudo apt install libnotify-bin`), with the freedesktop "complete" sound through `paplay` when available.
- **Windows:** a toast through built-in PowerShell, with the default notification sound. No modules are needed.

### Notifier settings

Change the settings from the terminal, run from the repository. They take effect with the next notification, with no reinstall or restart:

```sh
python3 -m codexalgia.install set sound off           # silent notifications
python3 -m codexalgia.install set sound on
python3 -m codexalgia.install set notifications off   # no notifications at all
python3 -m codexalgia.install set notifications on
```

On Windows, use `py -3` instead of `python3`.

The settings are stored in `config.json` in the [data directory](#install), which you can also edit by hand:

```json
{ "notifications": true, "sound": false }
```

You can also mute or turn off the notifications in your OS settings, without touching Codexalgia:

| OS | Where |
| --- | --- |
| macOS | System Settings → Notifications → **Script Editor**: turn off "Play sound for notification", or turn notifications off |
| Ubuntu (GNOME) | Settings → Sound → **System Sounds** volume, or Settings → Notifications → Do Not Disturb |
| Windows | Settings → System → Notifications → **Windows PowerShell**: turn off "Play a sound when a notification arrives", or turn notifications off |

The notifications come from Script Editor on macOS and Windows PowerShell on Windows, because those are the built-in tools that show them. Changing these OS settings also affects other scripts that use the same tools.

## How it works

```
Codex CLI ──hook──► codexalgia.pyz hook ──► <data>/sessions/<session_id>   (busy | ready)
                                └──────────► desktop notification (if enabled)

Chrome ──starts──► codexalgia-host ──► codexalgia.pyz host
                      watches <data>/sessions, pushes status on change
                                  │  native messaging
                                  ▼
                   extension/background.js swaps the icon
```

Codex runs `codexalgia.pyz hook` for each event below and passes the event on stdin:

| Codex event | Session becomes | Notification |
| --- | --- | --- |
| `SessionStart` | ready | none |
| `UserPromptSubmit`, `PreToolUse`, `PostToolUse` | busy | none |
| `PermissionRequest` | ready after 5 s, if still waiting | "Codex needs you", after 5 s, if still waiting |
| `Stop` | ready | "Codex is ready" |
| `Interrupt` (you pressed Esc) | ready | none |
| `SessionEnd` | removed | none |

- **Multiple sessions:** the hip hurts while *any* session is busy.
- **Never in the way:** the hook prints nothing and always exits 0, so it never answers an approval prompt or keeps Codex from stopping. If it fails, Codex carries on.
- **Subagents** report their parent's session, so they keep the parent busy instead of showing up as separate sessions.
- **Crashes:** a session that crashes sends no more events, so a busy session with no hook activity for 15 minutes counts as ready. Change this with `CODEXALGIA_BUSY_STALE_SECONDS`.
- **Stable extension ID:** the `key` in `extension/manifest.json` fixes the ID to `pdfldjccnohafaolkilhbnhjkeaineaa`, which is the only extension the native host accepts.

### Approvals

Codex runs the `PermissionRequest` hook *before* it decides who approves a call. So the hook also fires for calls you'll never see a prompt for:

- the automatic reviewer (Guardian) is on and approves it, or
- you already approved the same command for this session.

To avoid false alarms, a request first counts as busy. The hip relaxes, and "Codex needs you" is sent, only if the session is still waiting 5 seconds later with no other hook activity. When Codex approves a call itself, the tool usually runs and finishes within that time, and its `PostToolUse` event cancels the reminder. A real prompt reaches you 5 seconds late.

An automatically approved command that runs longer than 5 seconds, or a slow automatic review, can still cause one false alarm. Change the delay with `CODEXALGIA_APPROVAL_GRACE_SECONDS`. The delayed notification comes from a small helper process the hook starts, so the hook itself returns at once and never holds up the approval.

### Scope

| Where Codex runs | Covered? |
| --- | --- |
| Codex CLI in the terminal | Yes |
| Codex IDE extension, Codex app | Probably, since they share the CLI's engine. Not tested yet |
| Codex cloud tasks | No: their hooks run on OpenAI's servers |
| ChatGPT website, ChatGPT desktop app | No: they have no hooks |

## Project layout

```
codexalgia/            Python package (standard library only)
  hook.py              Codex hook handler
  host.py              Chrome native messaging host
  state.py             per-session busy/ready files
  notify.py            desktop notifications per OS
  config.py, paths.py  installed settings and locations
  cli.py               entry point of the installed codexalgia.pyz
  install/             installer: copies files, registers the host, edits ~/.codex/hooks.json
extension/             Chrome extension (Manifest V3)
site/                  landing page for codexalgia.tpojka.com
tests/                 unittest suite
```

## Development

```sh
python3 -m unittest -v
```

The tests are self-contained. Every test uses a temporary home, data directory and Codex folder, so your real install isn't touched. CI runs them on macOS, Ubuntu and Windows with Python 3.9 and the latest Python 3.

To use a data directory other than the default, set `CODEXALGIA_HOME`.

## Uninstall

```sh
./uninstall.sh      # macOS / Ubuntu
uninstall.cmd       # Windows
```

This removes the hooks, the native host registration and the data directory. Then remove the extension from `chrome://extensions`.

See [CHANGELOG.md](CHANGELOG.md) for release history.

## License

[MIT](LICENSE) © 2026 Goran Grbic. An independent project, not affiliated with OpenAI.
