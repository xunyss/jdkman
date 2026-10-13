# Homebrew Cellar 배포 원리 정리

## 1. 개요

`v*` 태그를 푸시하면 GitHub Actions가 자동으로 PyPI 배포 → Homebrew formula 생성 → bottle 빌드 → GitHub Release 업로드 → tap 업데이트를 순서대로 수행한다.

```
git tag v0.2.11 && git push origin v0.2.11
    │
    ├─ [ubuntu] PyPI 배포 (sdist + wheel)
    │
    └─ [macos]  Homebrew 배포
                  ├─ Formula 골격 생성 (generate_formula.py)
                  ├─ 의존성 resource 블록 생성 (brew update-python-resources)
                  ├─ bottle 빌드 (brew bottle)
                  ├─ GitHub Release에 bottle 업로드
                  ├─ Formula에 bottle 블록 삽입 (brew bottle --merge --write)
                  └─ homebrew-tap 레포에 커밋
```

배포 대상은 두 곳이다.

| 대상 | 레포 | 내용 |
|---|---|---|
| PyPI | `pypi.org/project/jdkman` | sdist + wheel |
| Homebrew tap | `xunyss/homebrew-tap` | `Formula/jdkman.rb` |
| GitHub Releases | `xunyss/jdkman` | bottle `.tar.gz` |

---

## 2. 전체 배포 흐름

### 트리거 조건

```yaml
on:
  push:
    tags:
      - "v*"
```

`v`로 시작하는 태그 푸시 시 실행된다. Homebrew 배포(`publish-homebrew`) job은 추가로 아래 조건을 만족해야 한다.

```yaml
needs: publish-pypi
if: github.event.base_ref == 'refs/heads/main'
```

- `needs: publish-pypi`: PyPI 배포가 성공한 후에만 실행
- `base_ref == 'refs/heads/main'`: `main` 브랜치에서 태그된 경우만 실행

### 버전 일치 검증

PyPI 배포 전에 태그와 `pyproject.toml` 버전이 일치하는지 확인한다.

```bash
TAG_VERSION=${GITHUB_REF_NAME#v}   # "v0.2.11" → "0.2.11"
PKG_VERSION=$(uv version --short)   # pyproject.toml의 version
if [ "$TAG_VERSION" != "$PKG_VERSION" ]; then exit 1; fi
```

배포 전에 `pyproject.toml`의 버전을 태그와 맞춰야 한다.

Homebrew 배포 과정은 `jdkman` 자신의 PyPI 메타데이터를 조회하지 않는다 (`4. 의존성 resource 생성` 참고 —
메인 패키지는 GitHub archive에서 직접 메타데이터를 읽는다). 그래서 PyPI 전파를 기다리는 `sleep` 같은
단계가 필요 없다. `needs: publish-pypi`는 "PyPI 배포가 끝난 뒤에만 Homebrew도 배포한다"는 순서 보장
목적으로만 남아있고, Homebrew job 자체의 동작에는 더 이상 PyPI 배포 완료가 기술적으로 필요하지 않다.

---

## 3. Formula 골격 생성 (`generate_formula.py`)

### 실행 방식

```bash
# 1. GitHub archive sha256 계산
SHA256=$(curl -sL "https://github.com/xunyss/jdkman/archive/refs/tags/v0.2.11.tar.gz" \
  | shasum -a 256 | cut -d' ' -f1)

# 2. formula 골격 생성 (의존성 resource는 아직 없음)
python scripts/homebrew/generate_formula.py 0.2.11 $SHA256 \
  > homebrew-tap/Formula/jdkman.rb
```

PyPI 의존성 조회 없이 `url`/`sha256`/`install`/`test` 블록만 있는 formula 골격을 만든다.
의존성 resource 블록은 `4. 의존성 resource 생성` 단계에서 공식 명령으로 채운다.

### 생성되는 Formula 구조

```ruby
class Jdkman < Formula
  include Language::Python::Virtualenv

  desc "..."
  homepage "..."
  url "https://github.com/xunyss/jdkman/archive/refs/tags/v0.2.11.tar.gz"   # GitHub archive
  sha256 "..."
  license "MIT"

  depends_on "rust" => :build   # Rust 바이너리 빌드 시에만 필요 (사용자 PC에는 불필요)
  depends_on "python@3.14"

  def install
    system "cargo", "build", "--release", "--manifest-path", "hook/Cargo.toml"
    bin.install "hook/target/release/jdk-hook-env"

    virtualenv_install_with_resources
    # zsh/bash/fish 자동완성 생성
    ...
  end
end
```

`virtualenv_install_with_resources`는 Homebrew의 Python CLI 표준 설치 패턴이다 (`language/python.rb`).
내부적으로 다음을 수행한다.

1. venv 생성
2. 선언된 `resource` 블록(의존성)을 전부 venv에 pip install
3. **`buildpath`(= `url`에서 받은 GitHub archive 소스)를 그 자리에서 직접 pip install하고, 생성된 entry-point 스크립트(`jdk`)를 자동으로 `bin/`에 링크**

즉 메인 패키지는 resource가 아니라 **소스에서 직접 빌드**된다. 과거엔 `jdkman-whl`이라는 가상의 resource를
만들어 PyPI에 이미 올라간 완성된 wheel을 따로 받아 pip install하는 방식을 썼는데, 이는 Homebrew 표준과
어긋나는 방식이었다 (표준 방식은 메인 패키지를 resource 목록에서 제외하고 buildpath에서 직접 빌드).
지금은 표준 패턴으로 교체되어 `bin.install_symlink`도 더 이상 필요 없다 (자동으로 링크됨).

### GitHub archive를 쓰는 이유

PyPI sdist에는 `hook/`(Rust 소스) 디렉토리가 포함되어 있지 않다. Rust 바이너리를 빌드하려면 전체 git
저장소 내용이 필요하므로, `url`은 PyPI가 아니라 GitHub archive를 가리킨다. GitHub archive는 태그 푸시
즉시 자동 생성되므로 Release 생성 전에도 접근 가능하다.

### zsh 자동완성 패치

formula 생성 시 zsh 스크립트 패치 코드도 Ruby로 인라인 생성된다 (상세 원리는 `notes/autocomplete.md` 참고).

```ruby
zsh_script = Utils.safe_popen_read({"_JDK_COMPLETE" => "source_zsh"}, bin/"jdk")
zsh_script = zsh_script.sub("compdef _jdk_completion jdk", <<~'ZSH'.chomp)
  if [ "$funcstack[1]" = "_jdk" ]; then
      _jdk_completion "$@"
  else
      compdef _jdk_completion jdk
  fi
ZSH
(zsh_completion/"_jdk").write zsh_script
```

Homebrew에는 `generate_completions_from_executable`이라는 공식 completion 생성 헬퍼가 있고 `:click`/`:typer`
포맷도 지원하지만, jdkman에는 그대로 맞지 않는다.

- `:click` 포맷은 `_JDK_COMPLETE=<shell>_source`를 쓴다. Click 8.0에서 완성 instruction 순서가
  `source_<shell>` → `<shell>_source`로 바뀌었는데, **Typer는 자신의 CLI 앱 하위호환을 위해 이 순서를
  일부러 원래대로(`source_<shell>`) 되돌리는 코드를 갖고 있다** (`typer/completion.py`의
  `shell_complete()` 참고 — click 버전과 무관하게 항상 구 포맷을 받는다). 그래서 `:click` 포맷은 Typer
  앱에는 애초에 맞지 않고, `_JDK_COMPLETE=source_zsh`가 (click 버전이 올라가도) 계속 정답이다.
  직접 확인: `_JDK_COMPLETE=source_zsh jdk`는 정상 스크립트를 출력하고, brew의 `:click` 포맷대로
  `_JDK_COMPLETE=zsh_source jdk`를 주면 `"Shell source not supported."` 에러가 난다.
- `:typer` 포맷은 `jdk --show-completion <shell>`을 호출하는데, `cli.py`의 `intercept_args()`가 프로덕션
  빌드에서 `--show-completion`/`--install-completion`을 의도적으로 막아놓았다.

그래서 위 수동 `_JDK_COMPLETE=source_zsh` 방식은 실수가 아니라 의도된 선택이며, typer를 업그레이드해도
이 하위호환 코드가 typer 안에 남아있는 한 깨지지 않는다. (typer가 이 호환 코드를 제거하는 breaking
change를 내는 경우에만 재검토가 필요하다.) 그대로 유지한다.

---

## 4. 의존성 resource 생성 (`brew update-python-resources`)

### 실행 방식

```bash
brew update-python-resources --exclude-packages=colorama xunyss/tap/jdkman
```

Homebrew 공식 명령으로, formula의 의존성 resource 블록을 자동으로 채운다. 과거의 `generate_formula.py`
내 수동 PyPI 조회/`EXCLUDE` 셋 로직을 전부 대체한다.

`--package-name`/`--version`을 주지 않으면, brew는 메인 패키지를 formula의 `url`(GitHub archive) 그
자체로 간주한다 (`utils/pypi.rb`의 `Package#basic_metadata` `@is_url` 분기). 즉:

- **메인 패키지(`jdkman` 자신)의 이름/버전은 GitHub archive를 직접 pip로 받아서 메타데이터를 읽어
  알아낸다. PyPI를 전혀 거치지 않는다** — 그래서 PyPI에 `jdkman`이 먼저 올라가 있을 필요가 없고
  (`2. 전체 배포 흐름`의 PyPI 전파 대기 참고), PyPI의 "최근 1일 이내 업로드 제외" cooldown 필터도
  적용되지 않는다.
- `requests`, `typer` 같은 **의존성들**은 여전히 PyPI에서 조회한다 (이미 안정적으로 게시된 서드파티
  패키지라 cooldown 문제가 없다).
- `--exclude-packages=colorama`: `colorama`는 click/typer의 Windows 전용(`platform_system == "Windows"`)
  의존성이라 macOS에서 pip가 정상적으로 환경 마커를 평가하면 애초에 리포트에 나타나지 않지만, 방어적으로
  명시해 둔다. (리포트에 없으면 조용히 무시되고, 있으면 제외됨)

이 명령은 내부적으로 `python@3.14` formula가 설치되어 있어야 하며, 없으면 자동으로 설치한다
(`Formula[python_name].ensure_installed!`). dev 전용 의존성(`pytest` 등)은 `pyproject.toml`의
`[project.dependencies]`에 없으므로(=`[dependency-groups] dev`에만 있음) 원래 메타데이터에 포함되지
않아 별도로 제외할 필요가 없다.

이 명령은 `brew tap xunyss/tap homebrew-tap`으로 등록된 tap 경로(`$(brew --repo xunyss/tap)/Formula/jdkman.rb`)
의 formula 파일을 직접 수정한다. `homebrew-tap/Formula/jdkman.rb`로의 반영은 `7. Bottle 블록 삽입` 단계의
`rsync`에서 한 번에 이루어진다 (두 단계가 같은 tap 경로 파일을 순서대로 수정하기 때문).

---

## 5. Bottle 빌드

### bottle이란

Homebrew의 bottle은 미리 빌드된 바이너리 패키지다. formula를 소스에서 빌드하는 대신 사전 빌드된 아카이브를 다운로드해 설치한다.

```
brew install xunyss/tap/jdkman
  → bottle 있음: tar.gz 다운로드 후 풀기 (수 초)
  → bottle 없음: 소스에서 빌드 (수 분)
```

### 빌드 과정

```bash
# 1. tap 등록 (로컬 디렉토리를 tap 소스로 사용)
brew tap xunyss/tap homebrew-tap
rsync -a ./homebrew-tap/ $(brew --repo xunyss/tap)/

# 2. bottle 빌드 옵션으로 설치
brew install --build-bottle xunyss/tap/jdkman

# 3. bottle 아카이브 생성
brew bottle --json \
  --root-url "https://github.com/xunyss/jdkman/releases/download/v0.2.11" \
  xunyss/tap/jdkman
```

`brew bottle`은 두 파일을 생성한다.

| 파일 | 내용 |
|---|---|
| `jdkman--0.2.11.arm64_sequoia.bottle.tar.gz` | 빌드된 패키지 아카이브 |
| `jdkman--0.2.11.arm64_sequoia.bottle.json` | sha256, root_url 등 메타데이터 |

### 파일명 정규화

`brew bottle`이 생성하는 파일명에 `--`(double dash)가 포함되므로 `-`(single dash)로 정규화한다.

```bash
for f in jdkman--*.tar.gz; do
  newname=$(echo "$f" | sed 's/jdkman--/jdkman-/')
  mv "$f" "$newname"
done
# jdkman--0.2.11.arm64_sequoia.bottle.tar.gz
# → jdkman-0.2.11.arm64_sequoia.bottle.tar.gz
```

GitHub Release 파일명과 formula의 `root_url` 기반 다운로드 경로를 일치시키기 위함이다.

---

## 6. GitHub Release 생성

```bash
gh release create "v0.2.11" \
  --repo xunyss/jdkman \
  --title "v0.2.11" \
  --notes "Release v0.2.11" \
  jdkman-*.tar.gz
```

bottle 파일을 GitHub Release asset으로 업로드한다. formula의 `root_url`이 이 주소를 가리킨다.

```
https://github.com/xunyss/jdkman/releases/download/v0.2.11/
  jdkman-0.2.11.arm64_sequoia.bottle.tar.gz
```

---

## 7. Bottle 블록 삽입 (`brew bottle --merge --write`)

### 역할

`brew bottle --json`이 생성한 `.bottle.json`을 읽어, formula에 `bottle do ... end` 블록을 삽입한다.
직접 regex로 끼워 넣는 custom 스크립트(`insert_bottle.py`) 대신, Homebrew 공식 명령을 사용한다.

```bash
JSON=$(ls jdkman--*.bottle.json jdkman-*.bottle.json 2>/dev/null | head -1)
brew bottle --merge --write --no-commit "$JSON"
rsync -a "$(brew --repo xunyss/tap)/Formula/" homebrew-tap/Formula/
```

- `--merge`: `.bottle.json`을 읽어 `bottle do ... end` 블록을 생성한다.
- `--write`: 생성한 블록을 formula 파일에 바로 반영한다. (기본적으로 커밋도 생성됨)
- `--no-commit`: 이 단계에서 자동 커밋을 만들지 않는다. 커밋은 뒤의 `8. Tap 업데이트` 단계에서 한 번에 수행한다.

`brew bottle --write`는 **brew가 tap으로 인식한 경로**(`$(brew --repo xunyss/tap)/Formula/jdkman.rb`)의 formula 파일을 직접 수정한다.
이 경로는 `brew tap xunyss/tap homebrew-tap` + `rsync`로 복사된 별도 사본이라, 수정 결과를 다시 `homebrew-tap/Formula/`로 `rsync`해 와야
실제로 커밋/푸시할 `homebrew-tap` 체크아웃에 반영된다.

### 입력: `.bottle.json`

```json
{
  "jdkman": {
    "bottle": {
      "root_url": "https://github.com/xunyss/jdkman/releases/download/v0.2.11",
      "rebuild": 0,
      "tags": {
        "arm64_sequoia": { "sha256": "abc123..." },
        "sequoia":        { "sha256": "def456..." }
      }
    }
  }
}
```

### 결과: formula에 삽입되는 블록

```ruby
  bottle do
    root_url "https://github.com/xunyss/jdkman/releases/download/v0.2.11"
    sha256 cellar: :any_skip_relocation, arm64_sequoia: "abc123..."
    sha256 cellar: :any_skip_relocation, sequoia: "def456..."
  end
```

`license "..."` 줄 바로 뒤에 삽입된다. `cellar: :any_skip_relocation`은 이 패키지가 Homebrew Cellar의 어느 경로에도
재배치 가능함을 의미한다. Python virtualenv 기반 설치는 절대 경로에 의존하지 않으므로 이 값이 사용된다.

---

## 8. Tap 업데이트

```bash
cd homebrew-tap
git add Formula/jdkman.rb
git commit -m "jdkman 0.2.11"
# Homebrew/actions/git-try-push@master 로 push
```

최종적으로 bottle 블록이 포함된 `jdkman.rb`가 `xunyss/homebrew-tap` 레포의 `main` 브랜치에 커밋된다.

사용자는 이후 아래 명령으로 설치한다.

```bash
brew install xunyss/tap/jdkman
```

---

## 9. Secrets

| Secret | 용도 |
|---|---|
| `PYPI_TOKEN` | PyPI 업로드 인증 |
| `HOMEBREW_TAP_TOKEN` | `xunyss/homebrew-tap` 레포 쓰기 + GitHub Release 생성 |

`HOMEBREW_TAP_TOKEN`은 두 가지 용도로 사용된다. `gh release create`와 `homebrew-tap` 레포 checkout/push 모두 이 토큰으로 처리된다.

---

## 10. 배포 체크리스트

```
□ pyproject.toml의 version을 태그와 일치하도록 업데이트
□ main 브랜치에 커밋 및 푸시
□ 태그 생성 및 푸시: git tag v0.2.11 && git push origin v0.2.11
□ GitHub Actions에서 두 job 모두 성공 확인
□ brew upgrade jdkman 으로 로컬 설치 테스트
```

> 태그는 반드시 `main` 브랜치 커밋에 붙여야 한다. `github.event.base_ref == 'refs/heads/main'` 조건 때문에 다른 브랜치에서 태그하면 Homebrew 배포 job이 스킵된다.
