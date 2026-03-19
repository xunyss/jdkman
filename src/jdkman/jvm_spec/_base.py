import re
from abc import ABCMeta, abstractmethod


class BaseVendorSpec(metaclass=ABCMeta):

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def from_plist(self, props: dict[str, str]) -> bool:
        pass

    @abstractmethod
    def image_type(self, props: dict[str, str]) -> str:
        pass

    @abstractmethod
    def feature(self, props: dict[str, str]) -> str:
        pass

    @abstractmethod
    def jvm_impl(self, props: dict[str, str]) -> str:
        pass

    @abstractmethod
    def java_version(self, props: dict[str, str]) -> str:
        pass

    @abstractmethod
    def version(self, props: dict[str, str]) -> str:
        pass

    def major_version(self, props: dict[str, str]) -> str:
        java_version = self.java_version(props)
        return "8" if java_version.startswith("1.8") else java_version.split(".")[0]

    def slug_item(self, props) -> tuple[str, dict]:
        slug_meta = {
            "vendor": self.name(),
            "image_type": self.image_type(props),
            "feature": self.feature(props),
            "jvm_impl": self.jvm_impl(props),
            "major_version": self.major_version(props),
            "java_version": self.java_version(props),
            "version": self.version(props),
        }
        return make_slug(slug_meta), slug_meta | {
            "location": props["JVMHomePath"],
        }


def make_slug(slug_meta: dict) -> str:
    parts = [slug_meta["vendor"]]
    if slug_meta["image_type"] == "jre":
        parts.append(slug_meta["image_type"])
    if slug_meta["feature"]:
        parts.append(slug_meta["feature"])
    if slug_meta["jvm_impl"]:
        parts.append(slug_meta["jvm_impl"])
    parts.append(slug_meta["major_version"])
    return "-".join(parts)

