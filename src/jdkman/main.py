"""
before: 실행 스크립트 분리:
[project.scripts]
jdk = "jdkman.cli:app"
jdk_hook = "jdkman.env_hook:main"
===>
after: 실행 스크립트 하나로 통합:
[project.scripts]
jdk = "jdkman.main:invoke"
"""
import sys
def invoke():
    """
    실행 스크립트 하나로 통합:
    [project.scripts]
    jdk = "jdkman.main:invoke"

    실행 스크립트 분리:
    [project.scripts]
    jdk = "jdkman.cli:app"
    jdk_hook = "jdkman.env_hook:main"
    """
    if len(sys.argv) > 1 and sys.argv[1] == "hook-env":
        # Fast path: skip heavy imports
        # Called by shell hook: jdk hook-env <slug>
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        from jdkman.env_hook import main
        main()
    else:
        from jdkman.cli import app
        app()

