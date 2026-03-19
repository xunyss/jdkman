import importlib
import inspect
import pkgutil
from pathlib import Path

from ._base import BaseVendorSpec


def _discover_spec() -> dict[str, BaseVendorSpec]:
    registry: dict[str, BaseVendorSpec] = {}
    package_path = Path(__file__).parent
    for module_info in pkgutil.iter_modules([str(package_path)]):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f".{module_info.name}", package=__name__)
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, BaseVendorSpec) and cls is not BaseVendorSpec:
                instance = cls()
                registry[instance.name()] = instance

    return registry

_spec_registry: dict[str, BaseVendorSpec] = _discover_spec()


def get_spec_vendor(props: dict[str, str]) -> str:
    for vendor_spec in _spec_registry.values():
        if vendor_spec.from_plist(props):
            return vendor_spec.name()
    return "unknown"


def get_spec(by: str | dict[str, str]) -> BaseVendorSpec:
    if isinstance(by, str):
        return _spec_registry[by]
    return _spec_registry[get_spec_vendor(by)]

