# zsh 자동완성 동작 원리 정리

## 1. 자동완성의 두 단계

자동완성은 항상 두 단계로 구성된다.

1. **핸들러 등록**: "jdk 명령어를 탭하면 이 함수를 호출해라"
2. **탭 입력 시 호출**: 등록된 함수가 실제로 완성 후보를 출력

```
compdef _jdk_completion jdk   ← 1단계: 등록
탭 입력 → _jdk_completion() 호출  ← 2단계: 실행
```

---

## 2. Typer가 생성하는 자동완성 스크립트

`_JDK_COMPLETE=source_zsh jdk` 실행 시 아래 스크립트를 stdout으로 출력한다.

```zsh
#compdef jdk

_jdk_completion() {
  eval $(env _TYPER_COMPLETE_ARGS="${words[1,$CURRENT]}" _JDK_COMPLETE=complete_zsh jdk)
}

compdef _jdk_completion jdk
```

- `#compdef jdk`: zsh가 이 파일을 `jdk` 완성 파일로 인식하는 태그
- `_jdk_completion()`: 탭 입력 시 실제로 호출되는 함수. `_JDK_COMPLETE=complete_zsh jdk`를 실행해서 후보 목록을 가져온다.
- `compdef _jdk_completion jdk`: `_jdk_completion`을 `jdk`의 완성 핸들러로 등록

### `_JDK_COMPLETE` 변수명 규칙

Typer(Click)가 자동으로 생성하며 변경 불가능하다.

```python
# Click 내부 로직
source_var = f"_{prog_name.upper().replace('-', '_').replace('.', '_')}_COMPLETE"
# prog_name = "jdk" → "_JDK_COMPLETE"
```

---

## 3. 자동완성 활성화 방법 비교

### 방법 1: `source dev_completion.zsh` (세션 한정)

```zsh
# scripts/dev_completion.zsh 내용
_JDK_COMPLETE=source_zsh jdk | source /dev/stdin
```

**반드시 `source`로 실행해야 한다.**

- `source` 없이 직접 실행하면 → **자식 프로세스(subshell)**에서 실행
- subshell에서 등록된 함수/환경은 부모 쉘(현재 터미널)로 전파되지 않음

```
# source 없이 실행 시
현재 터미널 (부모 쉘)
    └─ zsh scripts/dev_completion.zsh  (자식 프로세스)
           └─ compdef 등록됨 → 프로세스 종료, 사라짐 ❌

# source 실행 시
현재 터미널 (현재 쉘)
    └─ source scripts/dev_completion.zsh  (현재 쉘에서 직접 실행)
           └─ compdef 등록됨 → 유지됨 ✅
```

**동작 원리:**
`source /dev/stdin`이 스크립트 출력을 현재 쉘에서 직접 실행하므로 `compdef _jdk_completion jdk`가 즉시 실행된다. `fpath`, `compinit`, `.zshrc` 수정 없이 바로 동작.

**첫 탭부터 정상 동작** → `_jdk_completion`이 처음부터 바로 핸들러로 등록되기 때문.

---

### 방법 2: `jdk --install-completion` (영구 설치)

실행 시 두 가지 작업을 한다.

**① `~/.zfunc/_jdk` 파일 생성**

Typer 생성 스크립트를 그대로 저장.

**② `~/.zshrc` 마지막에 두 줄 추가**

```zsh
fpath+=~/.zfunc; autoload -Uz compinit; compinit
zstyle ':completion:*' menu select
```

**동작 원리:**

zsh 시작 시 `.zshrc`가 실행되면:
1. `fpath+=~/.zfunc` → `~/.zfunc` 디렉토리를 fpath에 추가
2. `compinit` → fpath 전체를 스캔하여 `_jdk` 파일 발견
3. `#compdef jdk` 태그를 읽어 `compdef _jdk jdk` 등록 → `_jdk`는 **autoload 상태**

**첫 탭 입력 시:**
- `_jdk`가 처음 호출되면서 파일 내용이 그때 로드·실행됨
- `_jdk_completion` 함수 정의 + `compdef _jdk_completion jdk` 실행 (핸들러 교체)
- `_jdk` 자체는 완성 결과를 출력하지 않음 → **첫 탭은 결과 없을 수 있음**

**두 번째 탭부터:**
- `_jdk_completion`이 핸들러 → 정상 동작 ✅

---

### 방법 3: `.zshrc`에 직접 한 줄 추가 (영구 설치, 간단 버전)

```zsh
# ~/.zshrc에 추가
_JDK_COMPLETE=source_zsh jdk | source /dev/stdin
zstyle ':completion:*' menu select   # 방향키 메뉴 원하면 추가
```

| 항목 | `fpath` + `compinit` 방식 | 한 줄 방식 |
|---|---|---|
| 시작 속도 | `compinit`이 fpath 전체 스캔해서 느림 | 빠름 |
| 다른 완성과 통합 | zsh 전체 완성 시스템과 통합 | `jdk`만 독립 등록 |
| `zstyle` 메뉴 | 자동 적용 | 따로 추가 필요 |
| 첫 탭 | 결과 없을 수 있음 | 정상 |

---

## 4. Homebrew formula에서의 자동완성 처리

### 저장 경로

```
/opt/homebrew/share/zsh/site-functions/_jdk
```

이 경로는 zsh 시작 시 fpath에 자동으로 포함되므로 별도 설정 불필요. `brew install jdkman` 하면 자동완성이 즉시 활성화된다.

### formula에서 스크립트를 패치하는 이유

```ruby
zsh_script = Utils.safe_popen_read({"_JDK_COMPLETE" => "source_zsh"}, bin/"jdk").lstrip
zsh_script = zsh_script.sub("compdef _jdk_completion jdk", <<~'ZSH'.chomp)
  if [ "$funcstack[1]" = "_jdk" ]; then
      _jdk_completion "$@"
  else
      compdef _jdk_completion jdk
  fi
ZSH
(zsh_completion/"_jdk").write zsh_script
```

**문제:** Homebrew는 파일명 `_jdk` = 함수명 `_jdk`로 autoload 등록.
탭 → `_jdk()` 호출 → `_jdk_completion` 정의만 하고 호출 안 함 → **완성 결과 없음**

**해결:** `$funcstack[1]`으로 호출 상황을 판별해서 즉시 실행.

```zsh
if [ "$funcstack[1]" = "_jdk" ]; then
    _jdk_completion "$@"   # zsh가 _jdk를 핸들러로 직접 호출한 상황 → 즉시 실행
else
    compdef _jdk_completion jdk  # source로 로드된 상황 → 등록
fi
```

### 방식별 최종 비교

| | `source dev_completion.zsh` | `--install-completion` | Homebrew |
|---|---|---|---|
| 저장 경로 | 없음 (메모리만) | `~/.zfunc/_jdk` | `/opt/homebrew/share/zsh/site-functions/_jdk` |
| 등록 시점 | source 즉시 | `compinit` 실행 시 (zsh 시작) | `compinit` 실행 시 (zsh 시작) |
| 등록 핸들러 | `_jdk_completion` | `_jdk` (→ 첫 탭에서 `_jdk_completion`으로 교체) | `_jdk` (패치로 내부에서 `_jdk_completion` 직접 호출) |
| 첫 탭 | 정상 ✅ | 결과 없을 수 있음 ⚠️ | 정상 ✅ |
| 지속성 | 세션 한정 | 영구 | 영구 |

---

## 5. `zstyle ':completion:*' menu select`

완성 후보를 **방향키로 선택 가능한 인터랙티브 메뉴**로 표시한다.

```
# zstyle 없음
$ jdk install <TAB>
temurin-21  zulu-17  corretto-11

# zstyle 있음
$ jdk install <TAB>
▶ temurin-21    ← 방향키로 이동 가능
  zulu-17
  corretto-11
```

---

## 부록. source / 자식 프로세스 / export

### 자식 프로세스 (subshell)

`sh a.sh` 또는 `./a.sh`로 실행하면 **자식 프로세스**에서 실행된다.
자식 프로세스에서 설정한 변수/함수는 프로세스 종료와 함께 사라지고 부모 쉘에 전달되지 않는다.

```sh
# a.sh
HELLO="WORLD"
```

```zsh
sh a.sh
echo $HELLO   # → 아무것도 안 나옴
```

### source (`. a.sh`)

`source a.sh`는 자식 프로세스를 만들지 않고 **현재 쉘에서 직접** 실행한다.
파일 안의 모든 변수/함수 정의가 현재 세션에 그대로 반영된다.

```zsh
source a.sh   # 또는 . a.sh
echo $HELLO   # → WORLD
```

### export의 방향

`export`는 환경변수를 **자식 프로세스로 전달**하는 것이다. 부모로 올라가지 않는다.

```
현재 세션 (부모)
    └─ sh a.sh  (자식)
           └─ export HELLO=WORLD  → 이 자식의 자식에게만 전달 가능
       ← 자식 종료, 부모는 모름 ❌
```

환경변수는 항상 **부모 → 자식** 방향으로만 흐른다. 자식에서 부모로 올라오는 방법은 없다.

| 방법 | 현재 세션 반영 | 이유 |
|---|---|---|
| `sh a.sh` | ❌ | 자식 프로세스에서 실행 |
| `export VAR=VALUE` (자식 안에서) | ❌ | 부모로 전달 불가 |
| `source a.sh` | ✅ | 현재 쉘에서 직접 실행 |
