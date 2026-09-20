#!/usr/bin/env bash
# macOS / Ubuntu: install Codexalgia (see codexalgia/install).
cd "$(dirname "$0")" && exec python3 -m codexalgia.install "$@"
