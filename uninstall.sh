#!/usr/bin/env bash
# macOS / Ubuntu: remove Codexalgia.
cd "$(dirname "$0")" && exec python3 -m codexalgia.install uninstall
