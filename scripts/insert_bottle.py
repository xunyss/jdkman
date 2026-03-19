#!/usr/bin/env python3
"""
Insert bottle block into Homebrew Formula.

Usage:
    python insert_bottle.py <bottle.json> <formula.rb>
"""

import json
import re
import sys


def main():
    if len(sys.argv) < 3:
        print("Usage: insert_bottle.py <bottle.json> <formula.rb>", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    bottle = list(data.values())[0]["bottle"]
    root_url = bottle["root_url"]
    rebuild = bottle.get("rebuild", 0)

    lines = ["  bottle do", f'    root_url "{root_url}"']
    if rebuild > 0:
        lines.append(f"    rebuild {rebuild}")
    for tag, info in bottle["tags"].items():
        lines.append(f'    sha256 cellar: :any_skip_relocation, {tag}: "{info["sha256"]}"')
    lines.append("  end")
    block = "\n".join(lines)

    with open(sys.argv[2]) as f:
        formula = f.read()

    formula = re.sub(r'( {2}license "[^"]*"\n)', r'\1\n' + block + '\n', formula)

    with open(sys.argv[2], "w") as f:
        f.write(formula)


if __name__ == "__main__":
    main()

