#!/usr/bin/env bash
# Draai de tests lokaal op Windows. Home Assistant importeert fcntl/resource (Unix-only);
# tests/_winstubs levert lege vervangers. Gebruik dit NIET op Linux/CI.
export PATH="$HOME/AppData/Local/Microsoft/WinGet/Links:$PATH"
PYTHONPATH="tests/_winstubs" uv run pytest "$@"
