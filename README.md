# jdkman

A command-line tool for installing and managing OpenJDK distributions.

---

## TODO: version 0.3.0
- [x] Add support for macOS
- [ ] Add support for Windows
- [ ] Add support for Linux
- [ ] Update tests
- [ ] rich - to standard colors
- [ ] 중복제거 - out(f"{MARK_INVALID} {st_emp(slug)} is not installed!", highlight=False)
- [ ] convention - command 도움말, param 도움말, 변수명, 함수명
- [ ] java 실행시 /usr/bin/java 실항하게 하기 (shims)

- [ ] jdk help 에서 version, help 다른 섹션으로 내리기
- [x] command alias
- [ ] query current applied jdk

```

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
