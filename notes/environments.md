# Auto JDK Switching (env) 동작 원리 정리

## 1. 개요

디렉토리별 `.java-version` 파일을 기반으로 `JAVA_HOME`을 자동으로 전환하는 기능이다.
디렉토리를 이동할 때마다 쉘 훅이 실행되어 해당 디렉토리의 JDK 설정을 적용한다.

```
~/project-a/   (.java-version: zulu-21)    → JAVA_HOME = /path/to/zulu-21
~/project-b/   (.java-version: temurin-17) → JAVA_HOME = /path/to/temurin-17
~/             (.java-version 없음)          → global 설정 적용 (없으면 JAVA_HOME unset)
```

---

## 2. 관련 커맨드

| 커맨드 | 설명 |
|---|---|
| `jdk activate <shell>` | 쉘 훅 스크립트 출력 (eval로 현재 세션에 적용) |
| `jdk deactivate` | 쉘 훅 제거 (jdk 쉘 함수가 자동으로 eval 처리) |
| `jdk use <distro>` | 현재 디렉토리에 `.java-version` 파일 생성 |
| `jdk use <distro> --global` | `~/.config/jdkman/.java-version` 생성 |
| `jdk unuse` | 현재 디렉토리의 `.java-version` 파일을 빈 파일로 초기화 |
| `jdk unuse --global` | global 파일을 빈 파일로 초기화 |

---

## 3. activate / deactivate

`activate`는 쉘 훅 스크립트를 **stdout으로 출력**만 한다. 현재 세션에 적용하려면 `eval`로 실행해야 한다.

```zsh
# ~/.zshrc 또는 현재 세션에서
eval "$(jdk activate zsh)"
eval "$(jdk activate bash)"
```

fish는 `eval $(...)`가 아닌 `| source` 방식을 사용한다.

```fish
# ~/.config/fish/config.fish
jdk activate fish | source
```

`activate` 실행 시 현재 쉘에 `_jdkman_jdk()` 래퍼 함수가 등록되고, `alias jdk=_jdkman_jdk`로 `jdk`가 이 함수를 가리킨다.
이후부터 `jdk` 명령은 바이너리가 아닌 **alias → 쉘 함수**로 실행된다.

```zsh
_jdkman_jdk() {
  case "$1" in
  deactivate)
    if [[ ! " $@ " =~ " --help " ]] && [[ ! " $@ " =~ " -h " ]]; then
      eval "$(command jdk deactivate "${2:-$_JDKMAN_SHELL}")"  # eval 자동 처리
    else
      command jdk "$@"   # --help/-h 는 바이너리로 직접 전달
    fi
    ;;
  *)
    command jdk "$@"   # 그 외는 바이너리로 위임
    ;;
  esac
}
alias jdk=_jdkman_jdk
compdef _jdk_completion _jdkman_jdk 2>/dev/null  # zsh: alias 확장 후에도 completion 동작
# bash: complete -o default -F _jdk_completion _jdkman_jdk 2>/dev/null
```

`which jdk` 출력이 함수 본문 대신 `jdk: aliased to _jdkman_jdk`로 표시된다.

`command jdk`로 바이너리를 직접 호출하는 이유: 쉘 함수 안에서 `jdk`를 그냥 호출하면 자기 자신을 재귀 호출하게 된다.

### deactivate

`jdk deactivate`는 `_jdkman_jdk()` 쉘 함수가 내부에서 자동으로 eval 처리하므로 사용자가 eval을 직접 쓸 필요가 없다.

```zsh
jdk deactivate          # _JDKMAN_SHELL 환경변수로 쉘 자동 감지
jdk deactivate --help   # --help/-h 있으면 eval 없이 바이너리로 직접 전달
```

deactivate 실행 시 제거되는 것:
- `chpwd_functions`, `precmd_functions`(zsh) 또는 `PROMPT_COMMAND`(bash)에서 훅 제거
- `jdk` alias 제거, `_jdkman_jdk`, `_jdkman_find_env_tag`, `_jdkman_hook` 함수 제거
- `JAVA_HOME` unset, `PATH`를 `_JDKMAN_ORIG_PATH`로 복원 (비-macOS)
- `_JDKMAN_SHELL`, `_JDKMAN_ORIG_PATH`, `_JDKMAN_CURRENT_ENV_TAG` unset

### 스크립트 파일 위치

```
src/jdkman/resources/env_scripts/
├── zsh              # zsh 훅 스크립트
├── zsh_dev          # zsh 개발용 (eval → echo, jdk hook-env 출력 확인용)
├── zsh_deactivate   # zsh 훅 제거 스크립트
├── bash             # bash 훅 스크립트
├── bash_dev         # bash 개발용
├── bash_deactivate  # bash 훅 제거 스크립트
├── fish             # fish 훅 스크립트
├── fish_dev         # fish 개발용
└── fish_deactivate  # fish 훅 제거 스크립트
```

mise의 `activate` 출력을 참고해서 설계했다.

---

## 4. 쉘 훅 동작 원리

### 훅 등록 방식

| 쉘 | 훅 메커니즘 | 발생 조건 |
|---|---|---|
| zsh | `precmd_functions` | 매 프롬프트 표시 직전 |
| zsh | `chpwd_functions` | `cd`로 디렉토리 변경 시 |
| bash | `PROMPT_COMMAND` | 매 프롬프트 표시 직전 |
| fish | `--on-event fish_prompt` | 매 프롬프트 표시 직전 |

> zsh의 `chpwd`가 발생하면 항상 `precmd`도 발생한다. 반대는 성립하지 않는다.
> `chpwd` 등록은 이론상 불필요하지만, 하위 호환성을 위해 유지한다.

### 최적화 전략 - Python 프로세스 최소화

`jdk hook-env`는 Python 프로세스를 띄우는 비용이 있다.
`cd`마다 무조건 실행하면 `pyenv`, `nvm` 등 다른 버전 관리 도구와 함께 사용 시 체감 성능 저하가 발생할 수 있다.

**해결책:** `.java-version` 탐색은 쉘에서 직접 처리하고, env_tag가 바뀌었을 때만 `jdk hook-env`를 호출한다.

```zsh
_jdkman_find_env_tag() {
  # Python 없이 쉘에서 직접 .java-version 탐색 (상위 디렉토리까지)
  local dir="$PWD" content
  while [[ "$dir" != "/" ]]; do
    if [[ -f "$dir/.java-version" ]]; then
      content="$(<"$dir/.java-version")"
      if [[ -n "$content" ]]; then
        echo "$content"
        return
      fi
    fi
    dir="${dir:h}"   # bash는 dir="$(dirname "$dir")"
  done
  # global fallback: ~/.config/jdkman/.java-version
  if [[ -f "$HOME/.config/jdkman/.java-version" ]]; then
    echo "$(<"$HOME/.config/jdkman/.java-version")"
  fi
}

_jdkman_hook() {
  local env_tag
  env_tag="$(_jdkman_find_env_tag)"
  if [[ "$env_tag" == "$_JDKMAN_CURRENT_ENV_TAG" ]]; then
    return   # env_tag 변경 없으면 jdk hook-env 실행 안 함
  fi
  _JDKMAN_CURRENT_ENV_TAG="$env_tag"
  if [[ -n "$env_tag" ]]; then
    eval "$(jdk hook-env "$env_tag" 2>/dev/null)"
  else
    unset JAVA_HOME
    [[ -n "${_JDKMAN_ORIG_PATH+x}" ]] && export PATH="$_JDKMAN_ORIG_PATH"
  fi
}
```

**`jdk hook-env`가 실행되는 경우:**
- `.java-version`(또는 global)에 내용이 존재하고
- 이전과 env_tag가 **다를 때만**

같은 디렉토리에 머물거나 `.java-version` 없는 곳을 이동할 때는 `jdk hook-env`가 실행되지 않는다.

### env_tag 비교의 부가 효과

`jdk use zulu-11`으로 현재 디렉토리의 `.java-version`을 변경하면,
다음 프롬프트 표시 시 `_JDKMAN_CURRENT_ENV_TAG`와 새 env_tag가 달라져 **즉시 적용**된다.
`cd` 없이도 반영된다.

---

## 5. jdk hook-env (단일 진입점)

`jdk hook-env`는 `jdk` 바이너리를 그대로 사용하되, **진입점에서 분기**한다.

```python
# src/jdkman/main.py
def invoke():
    if len(sys.argv) > 1 and sys.argv[1] == "hook-env":
        # Fast path: typer/click/rich/requests 미로드
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        from jdkman.env_hook import main
        main()
    else:
        from jdkman.cli import app
        app()
```

```toml
# pyproject.toml
[project.scripts]
jdk = "jdkman.main:invoke"
```

`sys.argv` 체크를 import 전에 수행하므로 heavy import가 발생하지 않는다.

| | `jdk hook-env` (fast path) | `jdk install` 등 |
|---|---|---|
| import | json, platform, sys, pathlib (stdlib만) | typer + click + rich + requests + ... |
| 예상 실행 시간 | 30~50ms | 100~200ms+ |

`jdk hook-env`는 `--help`에 노출되지 않는 내부 커맨드다.

### jdk hook-env 동작

```
jdk hook-env "zulu-21"
  → main.invoke(): "hook-env" 감지 → env_hook.main() 호출
  → MANAGED_JVM_DB(~/.jdk/.jdkman 또는 ~/Library/Java/JavaVirtualMachines/.jdkman) 읽기
  → aliases 먼저 resolve
  → installed에서 location 조회
  → stdout: export JAVA_HOME="/path/to/zulu-21/Contents/Home"
            export PATH="/path/to/zulu-21/bin:$_JDKMAN_ORIG_PATH"  (비-macOS만)
  → 에러(미설치 등): stderr 출력 후 exit 1
```

---

## 6. .java-version 파일

### 파일 종류

| 파일 | 위치 | 용도 |
|---|---|---|
| `.java-version` | 프로젝트 디렉토리 | 로컬 JDK 지정 |
| `.java-version` | `~/.config/jdkman/` | 전역 fallback |

### 탐색 순서

1. `$PWD`부터 루트(`/`)까지 상위 디렉토리를 순서대로 탐색
2. 발견된 `.java-version` 파일에 **내용이 있으면** 해당 env_tag 사용
3. 파일이 없거나 빈 파일이면 상위 디렉토리 계속 탐색
4. 모두 없으면 `~/.config/jdkman/.java-version` (global fallback)
5. 그것도 없으면 `unset JAVA_HOME`

### 빈 파일 동작

`jdk unuse`로 생성된 빈 `.java-version`은 **없는 것과 동일하게** 처리된다.
상위 디렉토리 탐색을 계속하고, 최종적으로 global 설정이 적용된다.

```
현재 디렉토리/.java-version  (빈파일)  → skip, 상위 탐색 계속
상위 디렉토리/.java-version  (없음)    → skip
~/.config/jdkman/.java-version  (zulu-11)  → JAVA_HOME = zulu-11
```

### 파일 형식

```
zulu-21
```

env_tag(slug 또는 alias) 한 줄만 작성한다.
개행 문자는 `$(<file)`로 읽을 때 zsh/bash가 자동으로 제거한다.

---

## 7. 개발 및 테스트

### 활성화 (현재 세션)

```zsh
source scripts/dev_activate.zsh          # 기본
source scripts/dev_activate.zsh --dev   # dev 모드
```

`dev_activate.zsh` 내부:
```zsh
eval "$(jdk activate zsh "$@")"
```

`--dev` 옵션이 있으면 `activate_script/zsh_dev`를 사용한다.
`zsh_dev`는 `zsh`와 동일하지만 `eval` 대신 `echo`를 사용해서 `jdk hook-env`의 출력을 터미널에서 직접 확인할 수 있다.

### jdk hook-env 직접 테스트

```zsh
jdk hook-env zulu-21
# → export JAVA_HOME="/Library/Java/JavaVirtualMachines/zulu-21/Contents/Home"
```

### 비활성화

```zsh
jdk deactivate   # jdk() 쉘 함수가 자동으로 eval 처리
```
