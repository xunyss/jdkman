from ._base import BaseVendorSpec


class Temurin(BaseVendorSpec):

    def name(self) -> str:
        return "temurin"

    def from_plist(self, props: dict[str, str]) -> bool:
        return props["JVMVendor"] == "Eclipse Adoptium"

    def image_type(self, props: dict[str, str]) -> str:
        return "jdk"

    def feature(self, props: dict[str, str]) -> str:
        return ""

    def jvm_impl(self, props: dict[str, str]) -> str:
        return ""

    def java_version(self, props: dict[str, str]) -> str:
        return props["JVMPlatformVersion"]

    def version(self, props: dict[str, str]) -> str:
        return props["JVMVersion"]

