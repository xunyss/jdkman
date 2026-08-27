import importlib.metadata as meta
import json
import platform
import time
from importlib.metadata import version
from pathlib import Path
from typing import Any


#---------------------------------------------------------------------------------------------------
_platform_system = platform.system().lower()
_platform_machine = platform.machine().lower()

#---------------------------------------------------------------------------------------------------
def get_jvm_api_url() -> str:
    """
    JVM DATA API
    https://mise-java.jdx.dev/
    https://mise-java.jdx.dev/jvm/{releaseType}/{operatingSystem}/{architecture}.json
      releaseType: ga, ea
      operatingSystem: linux, macosx, windows
      architecture: aarch64, arm32, i686, x86_64
    """
    _OS_MAP = {
        "linux": "linux",
        "darwin": "macosx",
        "windows": "windows",
    }
    _ARCH_MAP = {
        # aarch64 (ARM 64-bit)
        "aarch64": "aarch64",  # Linux
        "arm64": "aarch64",    # macOS (Apple Silicon), Windows -> "ARM64"
        # arm32 (ARM 32-bit)
        "armv7l": "arm32",     # Linux
        "armv6l": "arm32",     # Linux
        "arm": "arm32",        # Windows -> "ARM"
        # x86_64 (64-bit Intel/AMD)
        "x86_64": "x86_64",    # Linux, macOS
        "amd64": "x86_64",     # Windows -> "AMD64", BSD
        # i686 (32-bit x86)
        "i686": "i686",        # Linux
        "i586": "i686",
        "i386": "i686",
        "x86": "i686",         # Windows
    }
    _os = _OS_MAP[_platform_system]
    _arch = _ARCH_MAP[_platform_machine]
    return f"https://mise-java.jdx.dev/jvm/ga/{_os}/{_arch}.json"


def platform_name() -> str:
    return f"{_platform_system}-{_platform_machine}"


def is_macos():
    return _platform_system == "darwin"

def is_windows():
    return _platform_system == "windows"

def is_linux():
    return _platform_system == "linux"


def is_dev() -> bool:
    # noinspection PyBroadException
    try:
        dist = meta.distribution("jdkman")
        direct_url = dist.read_text("direct_url.json")
        if direct_url:
            return json.loads(direct_url).get("dir_info", {}).get("editable", False)
    except Exception:
        pass
    return False

#---------------------------------------------------------------------------------------------------
APP_NAME = "jdkman"
APP_VERSION = version(APP_NAME)
JVM_API_URL = get_jvm_api_url()

#---------------------------------------------------------------------------------------------------
CACHE_DIR = Path.home() / ".cache" / APP_NAME
CATALOG_CACHE_FILE = CACHE_DIR / ".catalog"
CATALOG_CACHE_TTL = 60 * 60 * 24 * 7  # 7 days (sec)

CONFIG_DIR = Path.home() / ".config" / APP_NAME
MANAGED_JVM_DB = CONFIG_DIR / "managed"
LOCAL_ENV_FILE = ".java-version"
GLOBAL_ENV_FILE = CONFIG_DIR / LOCAL_ENV_FILE

INSTALL_DIR = Path.home() / ("Library/Java/JavaVirtualMachines" if is_macos() else ".jdk")

#---------------------------------------------------------------------------------------------------
DISABLE_SUGGEST_OPTIONS = True
CUSTOM_STYLE_HELP = True
CUSTOM_STYLE_ERROR = True
CUSTOM_STYLE_TABLE = True

# debugging
FORCE_VERBOSE = is_dev() and True
CLEAN_WORK_DIR = not is_dev()

#---------------------------------------------------------------------------------------------------
def cached_catalog() -> str | None:
    if CATALOG_CACHE_FILE.exists() and (time.time() - CATALOG_CACHE_FILE.stat().st_mtime) < CATALOG_CACHE_TTL:
        return CATALOG_CACHE_FILE.read_text()
    return None

def cache_catalog(catalog: list[dict[str, Any]]):
    CATALOG_CACHE_FILE.write_text(json.dumps(catalog))

def clear_catalog():
    CATALOG_CACHE_FILE.unlink(missing_ok=True)


def init_dirs():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)

