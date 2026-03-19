import pytest

from jdkman.installer import make_jvm_dir_name


def _info(vendor, image_type="jdk", features=None, major_version=21):
    return {
        "vendor": vendor,
        "image_type": image_type,
        "features": features or [],
        "jvm_impl": "hotspot",
        "major_version": major_version,
    }


@pytest.mark.parametrize("info, expected", [
    # 기본
    (_info("zulu"),                                "zulu-21.jdk"),
    (_info("temurin"),                             "temurin-21.jdk"),
    (_info("zulu", major_version=17),       "zulu-17.jdk"),
    # JRE
    (_info("zulu", image_type="jre"),       "zulu-21.jre"),
    # vendor alias
    (_info("graalvm"),                             "graalvm-ce-21.jdk"),
    (_info("graalvm-community"),                   "graalvm-ce-21.jdk"),
    (_info("oracle-graalvm"),                      "graalvm-21.jdk"),
    (_info("microsoft"),                           "ms-21.jdk"),
    (_info("jetbrains"),                           "jbr-21.jdk"),
    # feature 포함
    (_info("zulu", features=["javafx"]),    "zulu-javafx-21.jdk"),
    # notarized 는 무시
    (_info("kona", features=["notarized"]), "kona-21.jdk"),
])
def test_make_jvm_root_name(info, expected):
    assert make_jvm_dir_name(info) == expected

