# jdkman

OpenJDK 배포판을 설치하고 관리하는 커맨드라인 도구입니다.

---

## Why jdkman?

JDK를 쓰다 보면 `21.0.3`이냐 `21.0.5`냐를 직접 골라야 하는 상황이 얼마나 될까요?
사실 거의 없죠. "Zulu 21 최신 버전" 이면 충분합니다.

jdkman은 딱 그 수준으로만 관리합니다.

- `jdk install zulu-21` — 벤더와 메이저 버전만 지정하면 끝
- `jdk upgrade zulu-21` — 최신 패치로 자동 갱신
- 같은 벤더 + 같은 메이저 버전은 항상 하나만 유지

마이너 버전 목록 뒤질 필요도, 패치 버전이 여러 개 쌓이는 일도 없습니다.

macOS에서는 `~/Library/Java/JavaVirtualMachines/` 에 설치되기 때문에
Gradle, IntelliJ 등 대부분의 개발 도구가 별도 설정 없이 바로 JDK를 탐지합니다.

---

## 설치

**Homebrew (권장):**

```bash
brew install xunyss/tap/jdkman
```

**pip:**

```bash
pip install jdkman
```

## 빠른 시작

```bash
# 설치 가능한 JDK 배포판 목록 조회
jdk remote

# 배포판 설치
jdk install zulu-21

# 설치된 배포판 목록 확인
jdk list

# 업데이트 가능한 항목 확인
jdk outdated
```

---

## 명령어

### `jdk remote [DISTRO]`

다운로드 가능한 JDK 배포판을 조회합니다.

기본적으로 안정 버전 JDK 빌드만 표시합니다. 플래그를 사용해 추가 빌드 유형을 포함할 수 있습니다.

```bash
jdk remote                    # 안정 버전 JDK 빌드 전체 목록
jdk remote zulu               # 벤더 이름으로 필터링
jdk remote --version 21       # 메이저 버전으로 필터링
jdk remote --all              # JRE 및 기능 빌드 포함
jdk remote --with-jre         # JRE 빌드 포함
jdk remote --with-feat        # 기능 빌드 포함 (예: JavaFX, CRaC)
jdk remote --all zulu         # 조합: 전체 빌드 유형 + zulu만
```

**옵션:**

| 옵션 | 단축키 | 설명 |
|------|--------|------|
| `--version` | `-v` | 메이저 버전 번호로 필터링 |
| `--all` | `-a` | 모든 빌드 유형 포함 |
| `--with-jre` | `-R` | JRE 빌드 포함 |
| `--with-feat` | `-F` | 기능 빌드 포함 |

---

### `jdk install <DISTRO>`

JDK 배포판을 다운로드하고 설치합니다.

```bash
jdk install zulu-21
jdk install temurin-17
jdk install zulu-jre-21          # JRE 버전
jdk install zulu-javafx-21       # JavaFX 포함
jdk install zulu-crac-21         # CRaC 포함
jdk install zulu-javafx-jre-21   # JRE + JavaFX
```

`DISTRO` 이름은 다음 패턴을 따릅니다:
```
{벤더}[-{기능}][-jre]-{메이저_버전}
```

정확한 배포판 이름은 `jdk remote` 명령으로 확인하세요.

---

### `jdk list`

jdkman으로 설치된 JDK 배포판 목록을 표시합니다.

```bash
jdk list
jdk ls      # 별칭
```

---

### `jdk uninstall <DISTRO>`

설치된 JDK 배포판을 제거합니다.

```bash
jdk uninstall zulu-21
jdk remove zulu-21    # 별칭
jdk rm zulu-21        # 별칭
```

---

### `jdk upgrade <DISTRO>`

설치된 배포판을 최신 패치 버전으로 업그레이드합니다.

```bash
jdk upgrade zulu-21
jdk update zulu-21    # 별칭
```

---

### `jdk outdated`

최신 버전이 존재하는 설치된 배포판 목록을 표시합니다.

```bash
jdk outdated
```

---

### `jdk vendors`

사용 가능한 모든 JDK 벤더 목록을 표시합니다.

```bash
jdk vendors
jdk vendor    # 별칭
```

---

### `jdk cleanup`

캐시 데이터(다운로드한 아카이브 및 카탈로그 캐시)를 삭제합니다.

```bash
jdk cleanup
jdk clean     # 별칭
jdk clear     # 별칭
```

---

### `jdk home` *(macOS 전용)*

시스템에 등록된 JVM의 Java 홈 경로를 표시합니다.

```bash
jdk home           # 등록된 Java 설치 목록
jdk home --json    # JSON 형식으로 상세 정보 표시
```

---

### `jdk version`

jdkman 버전을 표시합니다.

```bash
jdk version
jdk --version
jdk -v
```

---

## 라이선스

MIT
