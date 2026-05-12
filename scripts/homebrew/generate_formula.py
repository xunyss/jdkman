#!/usr/bin/env python3
"""
Generate complete Homebrew Formula for jdkman.

Usage:
    uv export --no-hashes --format requirements-txt | python generate_formula.py <version>

Example:
    uv export --no-hashes --format requirements-txt | python generate_formula.py 0.1.5 > Formula/jdkman.rb
"""

import sys
import json
import urllib.request


PACKAGE_NAME = "jdkman"
HOMEPAGE = "https://github.com/xunyss/jdkman"
EXCLUDE = {"pytest", "iniconfig", "pluggy", "packaging", "colorama"}


def fetch_pypi(package, version):
    url = f"https://pypi.org/pypi/{package}/{version}/json"
    with urllib.request.urlopen(url) as resp:
        return json.load(resp)


def find_sdist(data):
    for entry in data["urls"]:
        if entry["packagetype"] == "sdist":
            return entry["url"], entry["digests"]["sha256"]
    return None, None


def find_whl(data, py3_none_any_only=False):
    """Find wheel URL and sha256. Prefer py3-none-any."""
    for entry in data["urls"]:
        if entry["packagetype"] == "bdist_wheel" and "py3-none-any" in entry["url"]:
            return entry["url"], entry["digests"]["sha256"], "whl"
    if py3_none_any_only:
        return None, None, None
    for entry in data["urls"]:
        if entry["packagetype"] == "sdist":
            return entry["url"], entry["digests"]["sha256"], "sdist"
    return None, None, None


def parse_requirements(lines):
    packages = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-e") or ";" in line:
            continue
        if "==" in line:
            name, version = line.split("==")
            name = name.strip()
            version = version.strip()
            if name.lower() not in EXCLUDE:
                packages.append((name, version))
    return packages


def resource_block(rb_name, url, sha256, kind):
    lines = [f'  resource "{rb_name}" do']
    if kind == "whl":
        lines.append(f'    url "{url}",')
        lines.append(f'        using: :nounzip')
    else:
        lines.append(f'    url "{url}"')
    lines.append(f'    sha256 "{sha256}"')
    lines.append(f'  end')
    return "\n".join(lines)


def zsh_completion_ruby(indent="    "):
    compdef_line = 'compdef _jdk_completion jdk'
    funcstack_block = "\n".join([
        'if [ "$funcstack[1]" = "_jdk" ]; then',
        '    _jdk_completion "$@"',
        'else',
        f'    {compdef_line}',
        'fi',
    ])
    lines = [
        'zsh_script = Utils.safe_popen_read({"_JDK_COMPLETE" => "source_zsh"}, bin/"jdk").lstrip',
        f"zsh_script = zsh_script.sub(\"{compdef_line}\", <<~'ZSH'.chomp)",
        *[f'  {line}' for line in funcstack_block.splitlines()],
        'ZSH',
        '(zsh_completion/"_jdk").write zsh_script',
    ]
    return "\n".join(f"{indent}{line}" for line in lines)



def main():
    if len(sys.argv) < 3:
        print("Usage: generate_formula.py <version> <github-archive-sha256>", file=sys.stderr)
        sys.exit(1)

    version = sys.argv[1]
    github_sha256 = sys.argv[2]
    github_url = f"https://github.com/xunyss/jdkman/archive/refs/tags/v{version}.tar.gz"

    # fetch main package info (wheel only)
    pkg_data = fetch_pypi(PACKAGE_NAME, version)
    whl_url, whl_sha256, _ = find_whl(pkg_data, py3_none_any_only=True)

    if not whl_url:
        print(f"ERROR: could not find whl for {PACKAGE_NAME}=={version}", file=sys.stderr)
        sys.exit(1)

    # parse dependencies from stdin
    lines = sys.stdin.readlines()
    packages = parse_requirements(lines)

    # build resource blocks: main package whl (for install method)
    resource_blocks = [
        resource_block("jdkman-whl", whl_url, whl_sha256, "whl")
    ]

    # dependencies
    for name, dep_version in packages:
        dep_data = fetch_pypi(name, dep_version)
        url, sha256, kind = find_whl(dep_data)
        if url:
            rb_name = name.replace("_", "-").lower()
            resource_blocks.append(resource_block(rb_name, url, sha256, kind))
        else:
            print(f"# WARNING: no url found for {name}=={dep_version}", file=sys.stderr)

    resources_str = "\n\n".join(resource_blocks)

    formula = f"""\
class Jdkman < Formula
  include Language::Python::Virtualenv

  desc "A command-line tool for installing and managing JVM distributions, and switching Java environments."
  homepage "{HOMEPAGE}"
  url "{github_url}"
  sha256 "{github_sha256}"
  license "MIT"

  depends_on "rust" => :build
  # depends_on "python@3"
  depends_on "python@3.14"

{resources_str}

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
{zsh_completion_ruby()}
    (bash_completion/"jdk").write Utils.safe_popen_read({{"_JDK_COMPLETE" => "source_bash"}}, bin/"jdk")
    (fish_completion/"jdk.fish").write Utils.safe_popen_read({{"_JDK_COMPLETE" => "source_fish"}}, bin/"jdk")
  end

  test do
    assert_match "jdk", shell_output("#{{bin}}/jdk --help")
  end
end
"""

    print(formula)


if __name__ == "__main__":
    main()

