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

    slug = sys.argv[1]

    # Mirror config.py path logic without importing it
    if platform.system() == "Darwin":
        install_dir = Path.home() / "Library/Java/JavaVirtualMachines"
    else:
        install_dir = Path.home() / ".jdk"

    managed_db = install_dir / ".jdkman"
    if not managed_db.is_file():
        print(f"# jdkman: managed db not found", file=sys.stderr)
        sys.exit(1)

    managed = json.loads(managed_db.read_text())
    installed = managed.get("installed", {})
    aliases = managed.get("aliases", {})

    # Resolve alias → actual slug
    if slug in aliases:
        slug = aliases[slug]

    if slug not in installed:
        print(f"# jdkman: {slug} is not installed", file=sys.stderr)
        sys.exit(1)

    location = installed[slug]["location"]
    java_home = f"{location}/Contents/Home" if platform.system() == "Darwin" else location

    print(f'export JAVA_HOME="{java_home}"')


if __name__ == "__main__":
    main()

