#!/usr/bin/env zsh
# Load jdk auto-switching hook for the current shell session (dev only).
# Usage: source dev_activate.zsh [options]

eval "$(jdk activate zsh "$@")"
