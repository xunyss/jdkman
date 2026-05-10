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

`activate` 실행 시 훅 함수들(`_jdkman_find_env_tag`, `_jdkman_hook`)이 등록된다.
`jdk` 자체는 그대로 binary이고 별도 래퍼 함수나 alias는 없다.

### deactivate

deactivate도 activate와 동일하게 `eval`로 실행해야 한다.

```zsh
eval "$(jdk deactivate zsh)"
eval "$(jdk deactivate bash)"
```

```fish
jdk deactivate fish | source
```

deactivate 실행 시 제거되는 것:
- `chpwd_functions`, `precmd_functions`(zsh) 또는 `PROMPT_COMMAND`(bash)에서 훅 제거
- `_jdkman_find_env_tag`, `_jdkman_hook` 함수 제거
- `JAVA_HOME` unset, `PATH`를 `_JDKMAN_ORIG_PATH`로 복원 (비-macOS)
- `_JDKMAN_SHELL`, `_JDKMAN_ORIG_PATH`, `_JDKMAN_CURRENT_ENV_TAG` unset

### eval 없이 jdk deactivate 하는 방법 (미채택)

`jdk deactivate`를 eval 없이 `jdk deactivate`만으로 실행할 수 있게 하려면, activate 시 `jdk` 래퍼 함수/alias를 등록하면 된다.

```zsh
# activate 스크립트에 포함
_jdkman_jdk() {
  case "$1" in
  deactivate)
    if [[ ! " $@ " =~ " --help " ]] && [[ ! " $@ " =~ " -h " ]]; then
      eval "$(command jdk deactivate "${2:-$_JDKMAN_SHELL}")"  # eval 자동 처리
    else
      command jdk "$@"
    fi
    ;;
  *)
    command jdk "$@"
    ;;
  esac
}
alias jdk=_jdkman_jdk
```

`command jdk`로 바이너리를 직접 호출하는 이유: alias/함수 안에서 `jdk`를 그냥 호출하면 자기 자신을 재귀 호출하게 된다.

**채택하지 않은 이유:** `jdk`가 alias가 되면서 zsh/bash의 자동완성이 alias 확장 후 `_jdkman_jdk` completion을 찾아 실패한다. activation 스크립트에서 `compdef _jdk_completion _jdkman_jdk`를 추가해 보완할 수 있으나, `compinit` 실행 순서에 따라 여전히 불안정하다. `jdk deactivate` 사용 빈도가 낮아 복잡성 대비 이득이 없다고 판단해 미채택.

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

### 최적화 전략 - 외부 프로세스 호출 최소화

`cd`마다 외부 프로세스를 실행하면 `pyenv`, `nvm` 등 다른 버전 관리 도구와 함께 사용 시 체감 성능 저하가 발생할 수 있다.

**해결책 1:** `.java-version` 탐색은 쉘에서 직접 처리하고, env_tag가 바뀌었을 때만 외부 프로세스를 호출한다.

**해결책 2:** env_tag → JAVA_HOME 변환을 수행하는 외부 프로세스로 Python 대신 네이티브 바이너리(`jdk-hook-env`)를 우선 사용한다. (섹션 6 참고)

```zsh
_jdkman_find_env_tag() {
  # 쉘에서 직접 .java-version 탐색 (상위 디렉토리까지)
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
    return   # env_tag 변경 없으면 외부 프로세스 실행 안 함
  fi
  _JDKMAN_CURRENT_ENV_TAG="$env_tag"
  if [[ -n "$env_tag" ]]; then
    if command -v jdk-hook-env &>/dev/null; then
      eval "$(jdk-hook-env "$env_tag" 2>/dev/null)"   # Rust 네이티브 바이너리 (Homebrew)
    else
      eval "$(jdk hook-env "$env_tag" 2>/dev/null)"   # Python fallback (pip)
    fi
  else
    unset JAVA_HOME
    [[ -n "${_JDKMAN_ORIG_PATH+x}" ]] && export PATH="$_JDKMAN_ORIG_PATH"
  fi
}
```

**외부 프로세스가 실행되는 경우:**
- `.java-version`(또는 global)에 내용이 존재하고
- 이전과 env_tag가 **다를 때만**

같은 디렉토리에 머물거나 `.java-version` 없는 곳을 이동할 때는 외부 프로세스가 실행되지 않는다.

### env_tag 비교의 부가 효과

`jdk use zulu-11`으로 현재 디렉토리의 `.java-version`을 변경하면,
다음 프롬프트 표시 시 `_JDKMAN_CURRENT_ENV_TAG`와 새 env_tag가 달라져 **즉시 적용**된다.
`cd` 없이도 반영된다.

---

## 5. jdk hook-env (Python fallback)

`jdk hook-env`는 `jdk-hook-env` 네이티브 바이너리가 없는 환경(pip 설치)에서 사용되는 Python fallback이다.
`jdk` 바이너리를 그대로 사용하되, **진입점에서 분기**해 heavy import를 건너뛴다.

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

| | `jdk-hook-env` (Rust) | `jdk hook-env` (Python fast path) | `jdk install` 등 |
|---|---|---|---|
| 구현 | `hook/src/main.rs` | `src/jdkman/env_hook.py` | `src/jdkman/cli.py` |
| import | 없음 (네이티브) | json, platform, sys, pathlib (stdlib만) | typer + click + rich + requests + ... |
| 실행 시간 | ~3ms | ~30ms | ~150ms+ |

`jdk hook-env`는 `--help`에 노출되지 않는 내부 커맨드다.

---

## 6. jdk-hook-env (Rust 네이티브 바이너리)

### 개요

`jdk-hook-env`는 shell hook의 핵심 동작(env_tag → JAVA_HOME 변환)을 Python 없이 수행하는 독립 네이티브 바이너리다.
Python 인터프리터 시작 비용을 완전히 제거해 `cd` 시 체감 성능을 크게 개선한다.

### 소스 위치

```
hook/                   # Rust crate 루트
├── Cargo.toml
└── src/
    └── main.rs
```

### 동작

```
jdk-hook-env "zulu-21"
  → MANAGED_JVM_DB(~/.config/jdkman/managed) 읽기
  → aliases 먼저 resolve
  → installed에서 location 조회
  → stdout: export JAVA_HOME="/path/to/zulu-21/Contents/Home"
            export PATH="/path/to/zulu-21/bin:$_JDKMAN_ORIG_PATH"  (비-macOS만)
  → 에러(미설치 등): stderr 출력 후 exit 1
```

fish shell은 `_JDKMAN_SHELL=fish` 환경변수로 감지해 `set -gx` 문법으로 출력한다.

### 설치 위치

| 설치 방법 | 위치 |
|---|---|
| Homebrew | `/opt/homebrew/bin/jdk-hook-env` |
| 개발 환경 | `.venv/bin/jdk-hook-env` |

### shell hook과의 연동

shell hook(`_jdkman_hook`)이 `command -v jdk-hook-env`로 존재 여부를 확인해 자동으로 선택한다.
별도 설정 없이 Homebrew 설치 시 자동으로 Rust 바이너리를 사용한다.

### 개발 환경 빌드

```zsh
./scripts/dev_sync.zsh
# → uv sync + cargo build --release + .venv/bin/에 복사
```

Rust 소스만 변경 시 직접 빌드도 가능하다:

```zsh
cargo build --release --manifest-path hook/Cargo.toml
cp hook/target/release/jdk-hook-env .venv/bin/
```

---

## 8. .java-version 파일

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

## 9. 개발 및 테스트

### 환경 세팅

```zsh
./scripts/dev_sync.zsh   # uv sync + Rust 빌드 + .venv/bin/에 jdk-hook-env 복사
```

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
`zsh_dev`는 `zsh`와 동일하지만 `eval` 대신 `echo`를 사용해서 실행 결과를 터미널에서 직접 확인할 수 있다.

### hook 직접 테스트

```zsh
# Rust 바이너리
jdk-hook-env zulu-21
# → export JAVA_HOME="/Library/Java/JavaVirtualMachines/zulu-21/Contents/Home"

# Python fallback
jdk hook-env zulu-21
# → export JAVA_HOME="/Library/Java/JavaVirtualMachines/zulu-21/Contents/Home"
```

### 비활성화

```zsh
jdk deactivate   # jdk() 쉘 함수가 자동으로 eval 처리
```
