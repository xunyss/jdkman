# todo: env_hook.py -> C or Rust
"""
jdk_hook - Standalone shell hook for jdkman auto JVM switching.
Resolves a JVM slug to JAVA_HOME and outputs shell export commands.

Kept intentionally dependency-free (stdlib only) for fast startup.
"""
import json
import platform
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        sys.exit(1)

    env_tag = sys.argv[1]
    is_macos = platform.system() == "Darwin"

    # Mirror config.py path logic without importing it
    install_dir = Path.home() / ("Library/Java/JavaVirtualMachines" if is_macos else ".jdk")

    managed_db = install_dir / ".jdkman"
    if not managed_db.is_file():
        print(f"# jdkman: managed db not found", file=sys.stderr)
        sys.exit(1)

    managed = json.loads(managed_db.read_text())
    installed = managed.get("installed", {})
    aliases = managed.get("aliases", {})

    # Resolve alias → actual slug
    if env_tag in aliases:
        env_tag = aliases[env_tag]

    if env_tag not in installed:
        print(f"# jdkman: {env_tag} is not installed", file=sys.stderr)
        sys.exit(1)

    location = installed[env_tag]["location"]
    java_home = f"{location}/Contents/Home" if is_macos else location

    print(f'export JAVA_HOME="{java_home}"')


if __name__ == "__main__":
    main()

