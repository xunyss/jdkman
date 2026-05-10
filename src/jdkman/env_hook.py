"""
jdk hook-env - Python fallback for jdkman auto JVM switching.
Resolves a JVM slug to JAVA_HOME and outputs shell export commands.

This is a fallback for pip-installed environments.
When installed via Homebrew, the native Rust binary `jdk-hook-env` is used instead,
and this code is NOT called by the shell hook.

Kept intentionally dependency-free (stdlib only) for fast startup.
"""
import json
import os
import platform
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        sys.exit(-1)

    env_tag = sys.argv[1]
    is_macos = platform.system() == "Darwin"

    managed_db = Path.home() / ".config" / "jdkman" / "managed"
    if not managed_db.is_file():
        print(f"# jdkman: managed db not found", file=sys.stderr)
        sys.exit(-1)

    managed = json.loads(managed_db.read_text())
    installed = managed.get("installed", {})
    aliases = managed.get("aliases", {})

    # Resolve alias → actual slug
    if env_tag in aliases:
        env_tag = aliases[env_tag]

    if env_tag not in installed:
        print(f"# jdkman: {env_tag} is not installed", file=sys.stderr)
        sys.exit(-1)

    location = installed[env_tag]["location"]
    java_home = f"{location}/Contents/Home" if is_macos else location
    if os.environ.get("_JDKMAN_SHELL") == "fish":
        print(f'set -gx JAVA_HOME "{java_home}"')
        if not is_macos:
            print(f'set -gx PATH "{java_home}/bin" $_JDKMAN_ORIG_PATH')
    else:
        print(f'export JAVA_HOME="{java_home}"')
        if not is_macos:
            orig_path = os.environ.get("_JDKMAN_ORIG_PATH", "")
            print(f'export PATH="{java_home}/bin:{orig_path}"')


if __name__ == "__main__":
    main()

