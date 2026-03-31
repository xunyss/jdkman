#!/usr/bin/env zsh
# Load jdk autocompletion for the current shell session (dev only).
# Usage: source scripts/dev_completion.zsh

# `_JDK_COMPLETE=source_zsh jdk` >>
# #compdef jdk
#
# _jdk_completion() {
#   eval $(env _TYPER_COMPLETE_ARGS="${words[1,$CURRENT]}" _JDK_COMPLETE=complete_zsh jdk)
# }
#
# compdef _jdk_completion jdk

# 현재 세션에 한하여 즉시 사용 가능
# 1. _jdk_completion() { ... }    # 함수 정의
# 2. compdef _jdk_completion jdk  # 핸들러 즉시 등록

# note: `_JDK_COMPLETE` variable cannot be modified
_JDK_COMPLETE=source_zsh jdk | source /dev/stdin
