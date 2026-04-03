#!/usr/bin/env zsh
# Remove jdk auto-switching hook from the current shell session (dev only).
# Usage: source dev_deactivate.zsh

eval "$(jdk deactivate zsh)"
