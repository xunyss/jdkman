#!/usr/bin/env python3
"""
Generate Homebrew Formula skeleton for jdkman.

Resource blocks for Python dependencies are filled in afterwards by
`brew update-python-resources`; the bottle block is filled in by
`brew bottle --merge --write`.

Usage:
    python generate_formula.py <version> <github-archive-sha256>
"""

import sys


HOMEPAGE = "https://github.com/xunyss/jdkman"


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
  depends_on "python@3.15"

  def install
    system "cargo", "build", "--release", "--manifest-path", "hook/Cargo.toml"
    bin.install "hook/target/release/jdk-hook-env"

    virtualenv_install_with_resources

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
