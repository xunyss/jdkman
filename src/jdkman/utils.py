import hashlib
import re
import tarfile
from pathlib import Path


def version_key(v: str) -> tuple:
    """
    버전 문자열을 정렬 가능한 튜플로 변환.

    return:
        (main: tuple[int], build: tuple[int], is_stable: bool)

    패턴별 처리:
        17.32.13.0                 -> ((17,32,13,0), (), True)
        21.0.5+11                  -> ((21,0,5), (11,), True)
        8u392+9                    -> ((8,392), (9,), True)
        17.0.5-b759.1              -> ((17,0,5), (759,1), True)  # JetBrains
        17.0.11.b1                 -> ((17,0,11), (1,), True)    # GraalVM
        21.0.0+35.0.LTS            -> ((21,0,0), (35,0), True)   # SapMachine
        22.1.0+java11              -> ((22,1,0), (), True)       # GraalVM flavor
        24.0.2.0-Final+java22      -> ((24,0,2,0), (), True)     # Mandrel
        21.0.5+11_openj9-0.48.0    -> ((21,0,5), (11,), True)    # Semeru
        23.0.1+11_openj9-0.49.0-m2 -> ((23,0,1), (11,), False)   # milestone=prerelease

    examples:
        sorted(data, key=lambda x: version_key(x['version']))
    """
    s = str(v).strip()
    is_prerelease = False
    build: tuple[int, ...] = ()

    # Step 1: '_' 뒤는 런타임 태그(openj9 등) → 무시, -m숫자 있으면 prerelease
    if '_' in s:
        s, runtime = s.split('_', 1)
        if re.search(r'-m\d+', runtime):
            is_prerelease = True

    # Step 2: '8u' → '8.'
    s = re.sub(r'^8u', '8.', s)

    # Step 3: '-Final' 제거
    s = s.replace('-Final', '')

    # Step 4: '+' 로 분리
    if '+' in s:
        s, build_str = s.split('+', 1)
        if re.match(r'java\d+', build_str):  # +java11 류 → 플레이버 태그, 무시
            pass
        else:
            build_str = re.sub(r'\.?LTS', '', build_str)  # .LTS 제거
            build = tuple(int(n) for n in re.findall(r'\d+', build_str))

    # Step 5: '-' 로 분리
    if '-' in s:
        s, dash = s.split('-', 1)
        if re.match(r'b\d+', dash):  # -b759.1 (JetBrains) → 빌드
            build = tuple(int(n) for n in re.findall(r'\d+', dash))
        elif re.match(r'm\d+', dash):  # -m2 → prerelease
            is_prerelease = True

    # Step 6: '.' 로 분리 → 숫자 세그먼트
    main: list[int] = []
    for seg in s.split('.'):
        if seg.isdigit():
            main.append(int(seg))
        elif re.match(r'^b\d+$', seg):  # .b1 (GraalVM community)
            build = (int(seg[1:]),)

    # trailing zeros 제거: (21,48,17,0) == (21,48,17) 로 취급. 단, 최소 2개는 유지: (21,0,0) → (21,0)
    while len(main) > 2 and main[-1] == 0:
        main.pop()

    return tuple(main), build, not is_prerelease


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_archive(archive_path: Path, extract_path: Path) -> None:
    if archive_path.name.endswith(".tar.gz"):
        with tarfile.open(archive_path) as tar:
            tar.extractall(extract_path)
    else:
        raise ValueError(f"Unsupported archive format: {archive_path}")


def remove_letters(text: str) -> str:
    return re.sub(r"[A-Za-z]", "", text).strip()


def shorten(path: Path) -> str | None:
    if path is None:
        return None
    try:
        return "~/" + str(path.relative_to(Path.home()))
    except ValueError:
        return str(path)

