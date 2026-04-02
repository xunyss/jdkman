# jdkman

A command-line tool for installing, managing, and switching OpenJDK distributions.

---

## Why jdkman?

### JDK Management — Simple by Design

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

### Per-Project Java Environment Switching — Like jenv, But Integrated

Beyond managing installations, jdkman also handles per-project Java environment switching,
just like [jenv](https://www.jenv.be/).

- Set a Java version per directory with `jdk use zulu-21`
- A `.java-version` file is created in the current directory — **fully compatible with jenv**
- `JAVA_HOME` is automatically switched as you `cd` between projects
- Falls back to a global setting when no local `.java-version` is found
- Create short aliases like `jdk alias 21 zulu-21` for convenience

Since jdkman uses the same `.java-version` file format as jenv, you can adopt jdkman
in a team that already uses jenv — both tools will pick up the same file.

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

## Shell Integration (Auto Environment Switching)

To enable automatic `JAVA_HOME` switching when you change directories, add the following
to your shell configuration file.

**zsh** (`~/.zshrc`):

```zsh
eval "$(jdk activate zsh)"
```

**bash** (`~/.bashrc` or `~/.bash_profile`):

```bash
eval "$(jdk activate bash)"
```

**fish** (`~/.config/fish/config.fish`):

```fish
jdk activate fish | source
```

Once activated, jdkman reads the `.java-version` file in your current directory (or any
parent directory) and sets `JAVA_HOME` automatically. If no local file is found, it falls
back to the global setting configured with `jdk use --global`.

---

## Commands

### Management

#### `jdk remote [DISTRO]`

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

#### `jdk install <DISTRO>`

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

#### `jdk list`

Show all installed JDK distributions managed by jdkman.

```bash
jdk list
jdk ls      # alias
```

---

#### `jdk uninstall <DISTRO>`

Remove an installed JDK distribution.

```bash
jdk uninstall zulu-21
jdk rm zulu-21        # alias
```

---

#### `jdk upgrade <DISTRO>`

Upgrade an installed distribution to the latest patch version.

```bash
jdk upgrade zulu-21
jdk up zulu-21        # alias
```

---

#### `jdk outdated`

List installed distributions that have newer versions available.

```bash
jdk outdated
```

---

#### `jdk vendors`

List all available JDK vendors.

```bash
jdk vendors
jdk vendor    # alias
```

---

#### `jdk editions`

List all available JDK editions (vendor + feature combinations).

```bash
jdk editions
jdk edition    # alias
```

---

### Environment

#### `jdk use <DISTRO|ALIAS>`

Set the Java environment for the current directory.
Creates a `.java-version` file in the current directory.

```bash
jdk use zulu-21           # Set local (current directory)
jdk use 21                # Use an alias
jdk use zulu-21 --global  # Set global fallback (~/.config/jdkman/.java-version)
```

The `.java-version` file format is compatible with jenv.

---

#### `jdk unuse`

Clear the Java environment for the current directory or globally.

```bash
jdk unuse           # Remove local .java-version
jdk unuse --global  # Clear global setting
```

---

#### `jdk env`

Show the currently active Java environment and where it comes from.

```bash
jdk env
```

Displays the active distribution, version, scope (local/global), and the source `.java-version` file path.

---

#### `jdk alias <ALIAS> <DISTRO>`

Create a short alias for an installed distribution.

```bash
jdk alias 21 zulu-21       # Use "21" instead of "zulu-21"
jdk alias lts temurin-21
```

---

#### `jdk unalias <ALIAS>`

Remove an alias.

```bash
jdk unalias 21
```

---

#### `jdk aliases`

List all defined aliases and their status.

```bash
jdk aliases
```

---

#### `jdk activate <SHELL>`

Print the shell integration script that enables auto-switching.

```bash
eval "$(jdk activate zsh)"   # Add to ~/.zshrc
eval "$(jdk activate bash)"  # Add to ~/.bashrc
jdk activate fish | source   # Add to ~/.config/fish/config.fish
```

---

#### `jdk deactivate <SHELL>`

Remove the shell integration (auto-switching).

```bash
jdk deactivate zsh
jdk deactivate bash
jdk deactivate fish
```

---

### Tools

#### `jdk cleanup`

Remove cached data (downloaded archives and catalog cache).

```bash
jdk cleanup
jdk clean     # alias
jdk clear     # alias
```

---

#### `jdk home` *(macOS only)*

Show Java home paths for JVMs registered with the system.

```bash
jdk home           # List registered Java installations
jdk home --json    # Show detailed info in JSON format
```

---

#### `jdk mise [DISTRO]`

List or register JVM distributions as mise java tools.

```bash
jdk mise             # List current mise java tools
jdk mise zulu-21     # Register a distribution as a mise java tool
```

---

### About

#### `jdk version`

Show the jdkman version.

```bash
jdk version
jdk --version
jdk -v
```

---

## How Per-Project Switching Works

1. Add `eval "$(jdk activate zsh)"` (or bash, or `jdk activate fish | source` for fish) to your shell config.
2. Run `jdk use zulu-21` in a project directory — this creates a `.java-version` file.
3. Every time you `cd` into that directory (or any subdirectory), jdkman reads the nearest
   `.java-version` upward and sets `JAVA_HOME` automatically.
4. When you leave the directory, the global setting (or none) takes effect.

```
~/projects/
├── service-a/
│   └── .java-version   → "zulu-21"   → JAVA_HOME = zulu-21 path
└── legacy-app/
    └── .java-version   → "temurin-17" → JAVA_HOME = temurin-17 path
```

The `.java-version` file is a plain text file containing the distribution slug or alias.
Because it uses the same format as jenv, teams can mix jdkman and jenv users without conflict.

---

## License

MIT
