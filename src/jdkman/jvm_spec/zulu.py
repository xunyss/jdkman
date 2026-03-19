from ._base import BaseVendorSpec
from ..utils import remove_letters


class Zulu(BaseVendorSpec):

    def name(self) -> str:
        return "zulu"

    def from_plist(self, props: dict[str, str]) -> bool:
        return (
            props["JVMVendor"] == "Azul Systems, Inc."
            and "zulu" in props["JVMName"].lower()
        )

    def image_type(self, props: dict[str, str]) -> str:
        return "jre" if "jre" in props["JVMName"].lower() else "jdk"

    def feature(self, props: dict[str, str]) -> str:
        # zulu: crac, javafx
        return ""

    def jvm_impl(self, props: dict[str, str]) -> str:
        return ""

    def java_version(self, props: dict[str, str]) -> str:
        return props["JVMVersion"]

    def version(self, props: dict[str, str]) -> str:
        return remove_letters(props["JVMName"])

