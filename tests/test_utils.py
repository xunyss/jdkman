import pytest

from jdkman.utils import version_key


@pytest.mark.parametrize("version, expected", [
    # 순수 점(.) 구분 버전
    ("17.32.13.0",              ((17, 32, 13), (), True)),    # trailing 0 제거
    ("17.0.3.0.1",              ((17, 0, 3, 0, 1), (), True)),

    # '+' 빌드 번호
    ("21.0.5+11",               ((21, 0, 5), (11,), True)),
    ("11.0.22+7.1",             ((11, 0, 22), (7, 1), True)),

    # '8u' 표기
    ("8u392+9",                 ((8, 392), (9,), True)),

    # JetBrains '-b' 빌드
    ("17.0.5-b759.1",           ((17, 0, 5), (759, 1), True)),
    ("25.0.2-b329.70",          ((25, 0, 2), (329, 70), True)),

    # GraalVM Community '.b' 빌드
    ("17.0.11.b1",              ((17, 0, 11), (1,), True)),

    # SapMachine '+LTS'
    ("21.0.0+35.0.LTS",         ((21, 0), (35, 0), True)),   # trailing 0 제거, 최소 2개 유지

    # GraalVM flavor '+java' 태그 → 빌드 무시
    ("22.1.0+java11",           ((22, 1), (), True)),         # trailing 0 제거, 최소 2개 유지

    # Mandrel '-Final+java' → 둘 다 무시
    ("24.0.2.0-Final+java22",   ((24, 0, 2), (), True)),      # trailing 0 제거

    # Semeru '_openj9' 태그 → stable
    ("21.0.5+11_openj9-0.48.0", ((21, 0, 5), (11,), True)),

    # Semeru milestone → prerelease (is_stable=False)
    ("23.0.1+11_openj9-0.49.0-m2", ((23, 0, 1), (11,), False)),
])
def test_version_key(version, expected):
    assert version_key(version) == expected


def test_version_key_is_stable_true():
    _, _, is_stable = version_key("21.0.5+11")
    assert is_stable is True


def test_version_key_is_stable_false_for_milestone():
    _, _, is_stable = version_key("23.0.1+11_openj9-0.49.0-m2")
    assert is_stable is False


def test_version_key_sortable():
    versions = ["21.0.3+9", "21.0.5+11", "21.0.0+35.0.LTS"]
    sorted_versions = sorted(versions, key=version_key)
    assert sorted_versions == ["21.0.0+35.0.LTS", "21.0.3+9", "21.0.5+11"]


def test_version_key_stable_sorts_after_prerelease():
    stable = "23.0.1+11_openj9-0.49.0"
    prerelease = "23.0.1+11_openj9-0.49.0-m2"
    assert version_key(prerelease) < version_key(stable)

