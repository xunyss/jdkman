#!/usr/bin/env zsh
# Load jdk autocompletion for the current shell session (dev only).
# Usage: source scripts/dev-completion.zsh

_JDK_COMPLETE=source_zsh jdk | source /dev/stdin
