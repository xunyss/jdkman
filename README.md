# jdkman

A command-line tool for installing and managing OpenJDK distributions.

---

## TODO: version 0.3.0
- [x] Add support for macOS
- [ ] Add support for Windows
- [ ] Add support for Linux
- [ ] Add auto environment like jEnv
- [ ] Update tests
- [x] version text graphic
- [ ] jdkman-0.2.12.arm64_sequoia.bottle.tar.gz vs jdkman--0.2.12.arm64_sequoia.bottle.tar.gz
- [ ] rich - to standard colors
- [ ] 중복제거 - out(f"{MARK_INVALID} {st_emp(slug)} is not installed!", highlight=False)

```
claude --resume 2e868346-0793-4682-abc8-cffbff1aa93d
```

### colors

터미널 앱/테마마다 색상 표현이 달라지는 문제를 피하기 위해, 아래 기준으로 색상을 사용한다.

**ANSI 16색 (터미널 테마가 재정의함)**

테마를 만든 사람이 해당 배경에 잘 보이도록 색을 조정해두기 때문에, 결과적으로 테마에 자연스럽게 적응된다.
accent 색상(강조, 경고, 오류 등)에 사용한다.

일반 8색 (0~7):

| 번호 | Rich named color |
|----|------------------|
| 0  | `black`          |
| 1  | `red`            |
| 2  | `green`          |
| 3  | `yellow`         |
| 4  | `blue`           |
| 5  | `magenta`        |
| 6  | `cyan`           |
| 7  | `white`          |

밝은 8색 (8~15):

| 번호 | Rich named color             |
|----|------------------------------|
| 8  | `bright_black` (= dark gray) |
| 9  | `bright_red`                 |
| 10 | `bright_green`               |
| 11 | `bright_yellow`              |
| 12 | `bright_blue`                |
| 13 | `bright_magenta`             |
| 14 | `bright_cyan`                |
| 15 | `bright_white`               |

**텍스트 스타일 (항상 배경과 대비됨)**

색 지정 없이 현재 foreground를 기준으로 상대적으로 동작하므로, 어떤 테마에서도 안전하다.
일반 텍스트, 강도 조절에 사용한다.

| 스타일      | Rich markup    | 비고                       |
|----------|----------------|--------------------------|
| 기본       | (markup 없음)    |                          |
| 굵게       | `[bold]`       |                          |
| 흐리게      | `[dim]`        |                          |
| 기울임      | `[italic]`     |                          |
| 밑줄       | `[underline]`  |                          |
| 이중 밑줄    | `[underline2]` | 터미널 지원 여부 다양             |
| 윗줄       | `[overline]`   | 터미널 지원 여부 다양             |
| 취소선      | `[strike]`     |                          |
| 색반전      | `[reverse]`    | foreground/background 교체 |
| 깜빡임 (느림) | `[blink]`      | 터미널 지원 여부 다양             |
| 깜빡임 (빠름) | `[blink2]`     | 터미널 지원 여부 다양             |
| 숨김       | `[conceal]`    | 터미널 지원 여부 다양             |
| 테두리      | `[frame]`      | 터미널 지원 여부 다양             |
| 원형 테두리   | `[encircle]`   | 터미널 지원 여부 다양             |

**사용하지 않는 것**

- `[grey70]`, `[color(220)]`, `[#FFD700]` 등 절대 색상 → 특정 테마에서 배경과 구분 안 될 수 있음

---

## Why jdkman?

How often do you actually need to pick between `21.0.3` and `21.0.5`?
Probably never. "The latest Zulu 21" is almost always good enough.

jdkman manages JDKs at exactly that level — no more, no less.

- `jdk install zulu-21` — just pick a vendor and a major version
- `jdk upgrade zulu-21` — updates to the latest patch automatically
- One installation per vendor + major version, always

No scrolling through minor version lists. No patch versions piling up.

On macOS, JDKs are installed under `~/Library/Java/JavaVirtualMachines/` — the standard
path where Gradle, IntelliJ, and most other tools automatically look for JDKs.
No extra configuration needed.

---

## Installation

**Homebrew (recommended):**

```bash
brew install xunyss/tap/jdkman
```

**pip:**

```bash
pip install jdkman
```

## Quick Start

```bash
# Browse available JDK distributions
jdk remote

# Install a distribution
jdk install zulu-21

# List installed distributions
jdk list

# Check for outdated installations
jdk outdated
```

---

## Commands

### `jdk remote [DISTRO]`

Browse JDK distributions available for download.

By default, shows only stable JDK builds. Use flags to include additional build types.

```bash
jdk remote                    # List all stable JDK builds
jdk remote zulu               # Filter by vendor prefix
jdk remote --version 21       # Filter by major version
jdk remote --all              # Include JRE and feature builds
jdk remote --with-jre         # Include JRE builds
jdk remote --with-feat        # Include feature builds (e.g. JavaFX, CRaC)
jdk remote --all zulu         # Combined: all build types, zulu only
```

**Options:**

| Option        | Short | Description                    |
|---------------|-------|--------------------------------|
| `--version`   | `-v`  | Filter by major version number |
| `--all`       | `-a`  | Include all build types        |
| `--with-jre`  | `-R`  | Include JRE builds             |
| `--with-feat` | `-F`  | Include feature builds         |

---

### `jdk install <DISTRO>`

Download and install a JDK distribution.

```bash
jdk install zulu-21
jdk install temurin-17
jdk install zulu-jre-21          # JRE variant
jdk install zulu-javafx-21       # With JavaFX
jdk install zulu-crac-21         # With CRaC
jdk install zulu-javafx-jre-21   # JRE + JavaFX
```

The `DISTRO` name follows this pattern:
```
{vendor}[-{feature}][-jre]-{major_version}
```

Use `jdk remote` to find the exact distribution name.

---

### `jdk list`

Show all installed JDK distributions managed by jdkman.

```bash
jdk list
jdk ls      # alias
```

---

### `jdk uninstall <DISTRO>`

Remove an installed JDK distribution.

```bash
jdk uninstall zulu-21
jdk remove zulu-21    # alias
jdk rm zulu-21        # alias
```

---

### `jdk upgrade <DISTRO>`

Upgrade an installed distribution to the latest patch version.

```bash
jdk upgrade zulu-21
jdk update zulu-21    # alias
```

---

### `jdk outdated`

List installed distributions that have newer versions available.

```bash
jdk outdated
```

---

### `jdk vendors`

List all available JDK vendors.

```bash
jdk vendors
jdk vendor    # alias
```

---

### `jdk cleanup`

Remove cached data (downloaded archives and catalog cache).

```bash
jdk cleanup
jdk clean     # alias
jdk clear     # alias
```

---

### `jdk home` *(macOS only)*

Show Java home paths for JVMs registered with the system.

```bash
jdk home           # List registered Java installations
jdk home --json    # Show detailed info in JSON format
```

---

### `jdk version`

Show the jdkman version.

```bash
jdk version
jdk --version
jdk -v
```

---

## License

MIT
