# Codexalgia

**Your hip hurts while Codex works. It relaxes when Codex is ready.**

A Chrome toolbar button that shows whether Codex CLI is working, with optional desktop notifications. It works on macOS, Ubuntu and Windows.

> *codexalgia* (n.): Codex + *-algia*, after *coxalgia* (hip pain). It comes on while Codex works and eases when Codex is ready.

- Website: <https://codexalgia.tpojka.com>
- Source: <https://github.com/Tpojka/codexalgia>

---

## Three states, one glance

| Icon | State | Meaning |
| :-: | --- | --- |
| 🔴 | **Working** | Codex is working on a task in at least one session |
| 🟢 | **Ready** | Codex has finished, you pressed Esc, or it's waiting for your approval |
| ⚪ | **Not connected** | The local helper isn't running. Run the installer |

Hover over the icon to see how many sessions are working.

## What you get

- **Live toolbar status:** the icon changes the moment Codex starts, stops or is interrupted, with no polling delay.
- **Every session:** the hip hurts while *any* Codex session is working.
- **Useful notifications:** optional alerts with the first line of Codex's answer, or the command waiting for your approval. No false alarms for quick calls Codex approves on its own.
- **Three platforms:** macOS, Ubuntu/Linux and Windows. The installer detects which one you're on.
- **Stays out of the way:** it leaves your other Codex hooks alone, and a reinstall keeps the trust you gave in `/hooks`.
- **Fully local:** nothing leaves your machine. The status goes from Codex hooks to Chrome over native messaging.

## Install

Requires Python 3.9 or newer, Google Chrome and Codex CLI.

**macOS**

```sh
git clone https://github.com/Tpojka/codexalgia.git
cd codexalgia
./install.sh
```

**Ubuntu**

```sh
sudo apt install python3 libnotify-bin   # notify-send, for the notifier
git clone https://github.com/Tpojka/codexalgia.git
cd codexalgia
./install.sh
```

**Windows**

```bat
winget install Python.Python.3.12
git clone https://github.com/Tpojka/codexalgia.git
cd codexalgia
install.cmd
```

The installer asks:

```
  1) Chrome extension
  2) Chrome extension + OS notifier
  3) Nothing (exit)
Choose 1, 2 or 3: 2
Play a sound with notifications? [Y/n]:
```

Then finish in Chrome and Codex (once):

1. Open `chrome://extensions` and turn on **Developer mode**.
2. Click **Load unpacked** and pick the `extension` folder the installer printed.
3. Pin **Codexalgia** to the toolbar.
4. Restart any running Codex sessions, then type `/hooks` in Codex and **trust** the Codexalgia hooks.

Codex doesn't run a hook until you've trusted it, so don't skip the last step. Running the installer again keeps that trust, because it rewrites its hooks in place with the same command.

## OS notifier

You get a notification when Codex finishes a turn or needs your approval. The title includes the project name.

| When | Title | Text |
| --- | --- | --- |
| Codex finishes a turn | Codex is ready · *project* | The first line of Codex's last answer |
| Codex asks for approval | Codex needs you · *project* | The command it wants to run, or the tool it wants to use |

Codex also asks its hooks about calls it then approves on its own, through its automatic reviewer or an earlier "approve for this session". So "Codex needs you" waits 5 seconds and comes only if Codex is still waiting for you.

Change the settings any time from the repository. They take effect with the next notification, with no restart:

```sh
python3 -m codexalgia.install set sound off           # silent notifications
python3 -m codexalgia.install set sound on
python3 -m codexalgia.install set notifications off   # no notifications at all
python3 -m codexalgia.install set notifications on
```

On Windows, use `py -3` instead of `python3`.

Or use your OS settings:

| OS | Where |
| --- | --- |
| macOS | System Settings → Notifications → **Script Editor** |
| Ubuntu (GNOME) | Settings → Sound → **System Sounds**, or Notifications → Do Not Disturb |
| Windows | Settings → System → Notifications → **Windows PowerShell** |

## How it works

```
Codex CLI ──hook──► codexalgia.pyz hook ──► sessions/<id>   (busy | ready)
                                └──────────► desktop notification (optional)

Chrome ──starts──► codexalgia.pyz host
                      watches sessions/, pushes status on change
                                  │  native messaging
                                  ▼
                   extension swaps the icon
```

| Codex event | Hip | Notification |
| --- | --- | --- |
| `UserPromptSubmit`, `PreToolUse`, `PostToolUse` | hurts | none |
| `PermissionRequest` | relaxes after 5 s, if still waiting | Codex needs you, after 5 s, if still waiting |
| `Stop` | relaxes | Codex is ready |
| `Interrupt` (Esc) | relaxes | none |
| `SessionStart`, `SessionEnd` | adds or removes the session | none |

The hook prints nothing and always exits cleanly, so it never answers an approval prompt for you or keeps Codex from stopping.

It covers **Codex CLI**. The Codex IDE extension and app share its engine and should work too, but they aren't tested yet. It doesn't cover Codex cloud tasks or ChatGPT.

---

Codexalgia 1.0.0 · [MIT](https://github.com/Tpojka/codexalgia/blob/main/LICENSE) © 2026 Goran Grbic · An independent project, not affiliated with OpenAI.
