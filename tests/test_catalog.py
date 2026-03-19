import pytest

from jdkman.catalog import make_slug, sort_slugs


# ── helpers ──────────────────────────────────────────────────────────────────

def _meta(vendor, image_type="jdk", features=None, jvm_impl="hotspot", major_version=21):
    return {
        "vendor": vendor,
        "image_type": image_type,
        "features": features or [],
        "jvm_impl": jvm_impl,
        "major_version": major_version,
    }


def _slug_info(vendor, image_type="jdk", features=None, jvm_impl="hotspot", major_version=21, versions=None):
    return {
        "vendor": vendor,
        "image_type": image_type,
        "features": features or [],
        "jvm_impl": jvm_impl,
        "major_version": major_version,
        "latest": "21.0.5",
        "versions": versions or [],
    }


def _version(version, java_version="21.0.5", dists=None):
    return {"java_version": java_version, "version": version, "dists": dists or []}


def _dist(created_at, file_type="tar.gz"):
    return {"file_type": file_type, "url": "", "checksum": "", "created_at": created_at}


# ── make_slug ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("meta, expected", [
    # 기본 JDK
    (_meta("zulu"),                                                "zulu-21"),
    (_meta("zulu", major_version=17),                       "zulu-17"),
    # JRE
    (_meta("zulu", image_type="jre"),                       "zulu-jre-21"),
    (_meta("zulu", image_type="jre", major_version=17),     "zulu-jre-17"),
    # feature 포함
    (_meta("zulu", features=["javafx"]),                    "zulu-javafx-21"),
    (_meta("zulu", image_type="jre", features=["javafx"]),  "zulu-jre-javafx-21"),
    (_meta("liberica", features=["lite"]),                  "liberica-lite-21"),
    # notarized 는 feature 로 취급 안 함
    (_meta("kona", features=["notarized"]),                 "kona-21"),
    # jvm_impl: hotspot/graalvm 은 생략
    (_meta("graalvm", jvm_impl="graalvm"),                  "graalvm-21"),
    # jvm_impl: openj9 는 포함 (semeru)
    (_meta("semeru", jvm_impl="openj9"),                    "semeru-openj9-21"),
])
def test_make_slug(meta, expected):
    assert make_slug(meta) == expected


# ── sort_slugs ───────────────────────────────────────────────────────────────

def test_sort_slugs_by_vendor():
    slugs = {
        "zulu-21":    _slug_info("zulu"),
        "temurin-21": _slug_info("temurin"),
        "liberica-21":_slug_info("liberica"),
    }
    result = list(sort_slugs(slugs).keys())
    assert result == ["liberica-21", "temurin-21", "zulu-21"]


def test_sort_slugs_by_major_version():
    slugs = {
        "zulu-21": _slug_info("zulu", major_version=21),
        "zulu-11": _slug_info("zulu", major_version=11),
        "zulu-17": _slug_info("zulu", major_version=17),
    }
    result = list(sort_slugs(slugs).keys())
    assert result == ["zulu-11", "zulu-17", "zulu-21"]


def test_sort_slugs_jdk_before_jre():
    slugs = {
        "zulu-jre-21": _slug_info("zulu", image_type="jre"),
        "zulu-21":     _slug_info("zulu", image_type="jdk"),
    }
    result = list(sort_slugs(slugs).keys())
    assert result == ["zulu-21", "zulu-jre-21"]


def test_sort_slugs_versions_ascending():
    slugs = {
        "zulu-21": _slug_info("zulu", versions=[
            _version("21.0.5+11"),
            _version("21.0.1+12"),
            _version("21.0.3+9"),
        ])
    }
    result = sort_slugs(slugs)["zulu-21"]["versions"]
    assert [v["version"] for v in result] == ["21.0.1+12", "21.0.3+9", "21.0.5+11"]


def test_sort_slugs_dists_by_created_at():
    slugs = {
        "zulu-21": _slug_info("zulu", versions=[
            _version("21.0.5", dists=[
                _dist("2024-03-01"),
                _dist("2024-01-01"),
                _dist("2024-06-01"),
            ])
        ])
    }
    result = sort_slugs(slugs)["zulu-21"]["versions"][0]["dists"]
    assert [d["created_at"] for d in result] == ["2024-01-01", "2024-03-01", "2024-06-01"]

