import plistlib
import subprocess

from .config import is_macos
from .jvm_spec import get_spec


# --------------------------------------------------------------------------------------------------
#  macOS
# --------------------------------------------------------------------------------------------------

def exec_java_home(*opts: str):
    command = ["/usr/libexec/java_home", *opts]
    return subprocess.run(command, capture_output=True, text=True)


def list_jvm_props() -> list[dict]:
    result = exec_java_home("-X")
    try:
        return plistlib.loads(result.stdout.strip().encode())
    except plistlib.InvalidFileException:
        return []


# --------------------------------------------------------------------------------------------------
#  windows
# --------------------------------------------------------------------------------------------------

def scan_program_files():
    pass


# --------------------------------------------------------------------------------------------------

def scan_unmanaged() -> dict[str, dict]:
    if is_macos():
        unmanaged: dict[str, dict] = {}
        for jvm_props in list_jvm_props():
            spec = get_spec(jvm_props)
            slug, slug_meta = spec.slug_item(jvm_props)
            unmanaged[slug] = slug_meta
        return unmanaged
    else:
        raise NotImplementedError

