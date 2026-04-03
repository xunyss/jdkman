# Homebrew Cellar 배포 원리 정리

## 1. 개요

`v*` 태그를 푸시하면 GitHub Actions가 자동으로 PyPI 배포 → Homebrew formula 생성 → bottle 빌드 → GitHub Release 업로드 → tap 업데이트를 순서대로 수행한다.

```
git tag v0.2.11 && git push origin v0.2.11
    │
    ├─ [ubuntu] PyPI 배포 (sdist + wheel)
    │
    └─ [macos]  Homebrew 배포
                  ├─ Formula 생성 (generate_formula.py)
                  ├─ bottle 빌드 (brew bottle)
                  ├─ GitHub Release에 bottle 업로드
                  ├─ Formula에 bottle 블록 삽입 (insert_bottle.py)
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

### PyPI 전파 대기

```bash
sleep 60
```

PyPI 배포 직후 formula 생성 스크립트가 PyPI API로 sha256을 조회하므로, 배포 완료 전에 API가 호출되면 실패한다. 60초 대기로 전파를 기다린다.

---

## 3. Formula 생성 (`generate_formula.py`)

### 실행 방식

```bash
# 1. GitHub archive sha256 계산
SHA256=$(curl -sL "https://github.com/xunyss/jdkman/archive/refs/tags/v0.2.11.tar.gz" \
  | shasum -a 256 | cut -d' ' -f1)

# 2. formula 생성
uv export --no-hashes --format requirements-txt \
  | python scripts/homebrew/generate_formula.py 0.2.11 $SHA256 \
  > homebrew-tap/Formula/jdkman.rb
```

`uv export`로 의존성 목록을 뽑아 stdin으로 전달하고, PyPI에서 각 패키지의 URL과 sha256을 조회해 formula를 생성한다.
GitHub archive sha256은 CI에서 별도로 계산해 인자로 전달한다.

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
  depends_on "python@3"

  resource "jdkman-whl" do       # jdkman wheel (설치 시 사용)
    url "https://files.pythonhosted.org/.../jdkman-0.2.11-py3-none-any.whl",
        using: :nounzip
    sha256 "..."
  end

  resource "requests" do         # 의존 패키지 (wheel 또는 sdist)
    url "..."
    sha256 "..."
  end

  def install
    system "cargo", "build", "--release", "--manifest-path", "hook/Cargo.toml"
    bin.install "hook/target/release/jdk-hook-env"

    venv = virtualenv_create(libexec, "python3")
    resources.each do |r|
      r.stage do
        whl = Pathname.pwd.glob("*.whl").first
        system libexec/"bin/python", "-m", "pip", "install", "--no-deps", whl
      end
    end
    bin.install_symlink libexec/"bin/jdk"
    # zsh/bash/fish 자동완성 생성
    ...
  end
end
```

### GitHub archive vs wheel 역할 분리

| 항목 | 사용 위치 | 이유 |
|---|---|---|
| `url` (GitHub archive) | formula 상단 / `def install`에서 Rust 빌드 | `hook/` 디렉토리 포함, 태그 푸시 즉시 사용 가능 |
| `resource "jdkman-whl"` (wheel) | `def install` 안에서 pip로 설치 | Python 빌드 도구 없이 wheel을 직접 설치 |

GitHub archive는 태그 푸시 즉시 자동 생성되므로 Release 생성 전에도 접근 가능하다.

### 의존성 처리

```python
EXCLUDE = {"pytest", "iniconfig", "pluggy", "packaging", "colorama"}
```

dev/test 전용 패키지는 제외한다. `colorama`는 Windows 전용이므로 macOS formula에서 불필요하다.

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

---

## 4. Bottle 빌드

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

## 5. GitHub Release 생성

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

## 6. Bottle 블록 삽입 (`insert_bottle.py`)

### 역할

`brew bottle --json`이 생성한 `.bottle.json`을 읽어, formula에 `bottle do ... end` 블록을 삽입한다.

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

### 출력: formula에 삽입되는 블록

```ruby
  bottle do
    root_url "https://github.com/xunyss/jdkman/releases/download/v0.2.11"
    sha256 cellar: :any_skip_relocation, arm64_sequoia: "abc123..."
    sha256 cellar: :any_skip_relocation, sequoia: "def456..."
  end
```

### 삽입 위치

`license "..."` 줄 바로 뒤에 삽입된다.

```ruby
  license "MIT"
              ↑ 여기 아래에 bottle 블록 삽입
  bottle do
    ...
  end
```

`cellar: :any_skip_relocation`은 이 패키지가 Homebrew Cellar의 어느 경로에도 재배치 가능함을 의미한다. Python virtualenv 기반 설치는 절대 경로에 의존하지 않으므로 이 값이 사용된다.

---

## 7. Tap 업데이트

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

## 8. Secrets

| Secret | 용도 |
|---|---|
| `PYPI_TOKEN` | PyPI 업로드 인증 |
| `HOMEBREW_TAP_TOKEN` | `xunyss/homebrew-tap` 레포 쓰기 + GitHub Release 생성 |

`HOMEBREW_TAP_TOKEN`은 두 가지 용도로 사용된다. `gh release create`와 `homebrew-tap` 레포 checkout/push 모두 이 토큰으로 처리된다.

---

## 9. 배포 체크리스트

```
□ pyproject.toml의 version을 태그와 일치하도록 업데이트
□ main 브랜치에 커밋 및 푸시
□ 태그 생성 및 푸시: git tag v0.2.11 && git push origin v0.2.11
□ GitHub Actions에서 두 job 모두 성공 확인
□ brew upgrade jdkman 으로 로컬 설치 테스트
```

> 태그는 반드시 `main` 브랜치 커밋에 붙여야 한다. `github.event.base_ref == 'refs/heads/main'` 조건 때문에 다른 브랜치에서 태그하면 Homebrew 배포 job이 스킵된다.
