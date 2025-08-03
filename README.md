# 🤖 마스토돈 자동봇 (Mastodon Default Bot)

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Mastodon.py](https://img.shields.io/badge/Mastodon.py-1.8.1-green.svg)](https://github.com/halcy/Mastodon.py)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 실시간 데이터 반영과 성능 최적화가 적용된 마스토돈 자동봇 시스템

## 📋 목차

- [개요](#-개요)
- [주요 기능](#-주요-기능)
- [시스템 요구사항](#-시스템-요구사항)
- [설치 및 설정](#-설치-및-설정)
- [사용법](#-사용법)
- [프로젝트 구조](#-프로젝트-구조)
- [설정 가이드](#-설정-가이드)
- [플러그인 개발](#-플러그인-개발)
- [문제 해결](#-문제-해결)
- [기여하기](#-기여하기)
- [라이선스](#-라이선스)

## 🎯 개요

마스토돈 자동봇은 **실시간 데이터 반영**과 **성능 최적화**를 중점으로 설계된 고급 봇 시스템입니다. Google Sheets와 연동하여 동적으로 명령어를 관리하고, 플러그인 아키텍처를 통해 확장 가능한 구조를 제공합니다.

### ✨ 핵심 특징

- 🔄 **실시간 데이터 반영**: Google Sheets 변경사항 즉시 반영
- ⚡ **성능 최적화**: 메모리 효율적 설계 및 캐시 최적화
- 🔌 **플러그인 시스템**: 동적 명령어 확장 지원
- 🛡️ **강력한 에러 처리**: 체계적인 에러 분류 및 자동 복구
- 📊 **상세한 모니터링**: 성능 통계 및 상태 추적
- 🌏 **한국어 최적화**: 한글 조사 자동 처리

## 🚀 주요 기능

### 🎲 기본 명령어

| 명령어 | 형식 | 설명 | 예시 |
|--------|------|------|------|
| **다이스** | `[2d6]` | 주사위 굴림 | `[1d20>15]` (15 이상 성공) |
| **카드뽑기** | `[카드뽑기/5장]` | 카드 뽑기 | `[카드 뽑기/3장]` |
| **운세** | `[운세]` | 오늘의 운세 | `[운세]` |
| **도움말** | `[도움말]` | 사용 가능한 명령어 | `[도움말]` |

### 🔧 고급 기능

- **커스텀 명령어**: Google Sheets에서 동적 관리
- **DM 지원**: 개인 메시지로 민감한 정보 전송
- **성능 모니터링**: 실시간 처리 통계
- **자동 복구**: 네트워크 오류 시 자동 재연결
- **관리자 알림**: 시스템 오류 시 관리자에게 알림

## 💻 시스템 요구사항

### 필수 요구사항

- **Python**: 3.8 이상
- **메모리**: 최소 512MB (권장 1GB)
- **네트워크**: 안정적인 인터넷 연결
- **저장공간**: 최소 100MB

### 권장 사양

- **Python**: 3.9 이상
- **메모리**: 2GB 이상
- **CPU**: 멀티코어 프로세서
- **네트워크**: 고속 인터넷 연결

## 📦 설치 및 설정

### 1. 저장소 클론

```bash
git clone https://github.com/your-username/mastodon-default-bot.git
cd mastodon-default-bot
```

### 2. 가상환경 생성 및 활성화

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
# 마스토돈 API 설정
MASTODON_CLIENT_ID=your_client_id
MASTODON_CLIENT_SECRET=your_client_secret
MASTODON_ACCESS_TOKEN=your_access_token
MASTODON_API_BASE_URL=https://your-instance.com

# Google Sheets 설정
SHEET_NAME=기본 자동봇 시트
GOOGLE_CREDENTIALS_PATH=credentials.json

# 봇 설정
SYSTEM_ADMIN_ID=admin
LOG_LEVEL=INFO
DEBUG_MODE=False

# 성능 설정
BOT_MAX_RETRIES=5
BOT_BASE_WAIT_TIME=2
MAX_DICE_COUNT=20
MAX_DICE_SIDES=1000
MAX_CARD_COUNT=52
```

### 5. Google Sheets 설정

1. **Google Cloud Console**에서 프로젝트 생성
2. **Google Sheets API** 활성화
3. **서비스 계정** 생성 및 키 다운로드
4. `credentials.json` 파일을 프로젝트 루트에 배치
5. Google Sheets에 서비스 계정 이메일 공유

### 6. 봇 실행

```bash
python main.py
```

## 📖 사용법

### 기본 사용법

봇을 멘션하여 명령어를 실행하세요:

```
@봇이름 [2d6]          # 주사위 2개를 6면체로 굴림
@봇이름 [카드뽑기/5장]   # 카드 5장을 뽑음
@봇이름 [운세]          # 오늘의 운세를 보여줌
@봇이름 [도움말]        # 사용 가능한 명령어 목록
```

### 고급 사용법

#### 다이스 명령어

```bash
[2d6]           # 기본 주사위
[1d20>15]       # 15 이상 성공
[3d6<4]         # 4 이하 성공
[2d10+5]        # 수정자 적용
```

#### 커스텀 명령어

Google Sheets의 `커스텀` 시트에서 관리:

| 명령어 | 문구 |
|--------|------|
| `[안녕]` | 안녕하세요! 반갑습니다. |
| `[날씨]` | 오늘 날씨는 맑습니다. |

### 관리자 명령어

```
@봇이름 [상태]          # 봇 상태 확인
@봇이름 [통계]          # 처리 통계 확인
@봇이름 [재시작]        # 봇 재시작 (관리자만)
```

## 📁 프로젝트 구조

```
mastodon_default_bot/
├── 📄 main.py                          # 메인 실행 파일
├── 📄 requirements.txt                 # Python 의존성
├── 📄 .env.example                     # 환경 변수 템플릿
├── 📄 README.md                        # 프로젝트 문서
├── 📄 check_setup.py                   # 설정 검증 도구
├── 📄 test_integration.py              # 통합 테스트
├── 📄 test_plugin_system.py            # 플러그인 테스트
│
├── 📁 config/                          # 설정 관리
│   ├── 📄 __init__.py
│   ├── 📄 settings.py                  # 애플리케이션 설정
│   └── 📄 validators.py                # 설정 검증
│
├── 📁 commands/                        # 명령어 시스템
│   ├── 📄 __init__.py
│   ├── 📄 base_command.py              # 기본 명령어 클래스
│   ├── 📄 dice_command.py              # 다이스 명령어
│   ├── 📄 card_command.py              # 카드 명령어
│   ├── 📄 fortune_command.py           # 운세 명령어
│   ├── 📄 help_command.py              # 도움말 명령어
│   └── 📄 custom_command.py            # 커스텀 명령어
│
├── 📁 handlers/                        # 이벤트 핸들러
│   ├── 📄 __init__.py
│   ├── 📄 stream_handler.py            # 스트림 이벤트 처리
│   └── 📄 command_router.py            # 명령어 라우팅
│
├── 📁 models/                          # 데이터 모델
│   ├── 📄 __init__.py
│   ├── 📄 command_result.py            # 명령어 결과
│   ├── 📄 user.py                      # 사용자 모델
│   ├── 📄 README.md                    # 모델 문서
│   │
│   ├── 📁 base/                        # 기본 클래스
│   │   ├── 📄 __init__.py
│   │   ├── 📄 base_result.py           # 결과 기본 클래스
│   │   ├── 📄 factory.py               # 팩토리 패턴
│   │   ├── 📄 registry.py              # 자동 등록 시스템
│   │   └── 📄 result_protocol.py       # 결과 프로토콜
│   │
│   ├── 📁 enums/                       # 열거형
│   │   ├── 📄 __init__.py
│   │   ├── 📄 command_type.py          # 명령어 타입
│   │   └── 📄 command_status.py        # 명령어 상태
│   │
│   ├── 📁 results/                     # 결과 타입
│   │   ├── 📄 __init__.py
│   │   ├── 📄 dice_result.py           # 다이스 결과
│   │   ├── 📄 card_result.py           # 카드 결과
│   │   ├── 📄 fortune_result.py        # 운세 결과
│   │   ├── 📄 custom_result.py         # 커스텀 결과
│   │   ├── 📄 help_result.py           # 도움말 결과
│   │   ├── 📄 money_result.py          # 소지금 결과
│   │   ├── 📄 inventory_result.py      # 인벤토리 결과
│   │   ├── 📄 shop_result.py           # 상점 결과
│   │   ├── 📄 buy_result.py            # 구매 결과
│   │   ├── 📄 transfer_result.py       # 양도 결과
│   │   └── 📄 item_description_result.py # 아이템 설명
│   │
│   ├── 📁 core/                        # 핵심 로직
│   │   ├── 📄 __init__.py
│   │   ├── 📄 command_result.py        # 명령어 결과
│   │   └── 📄 command_stats.py         # 명령어 통계
│   │
│   └── 📁 utils/                       # 유틸리티
│       ├── 📄 __init__.py
│       ├── 📄 helpers.py               # 헬퍼 함수
│       ├── 📄 korean_particles.py      # 한글 조사 처리
│       └── 📄 validation.py            # 검증 함수
│
├── 📁 utils/                           # 유틸리티 모듈
│   ├── 📄 __init__.py
│   ├── 📄 cache_manager.py             # 캐시 관리
│   ├── 📄 dm_sender.py                 # DM 전송
│   ├── 📄 error_handling.py            # 에러 처리
│   ├── 📄 logging_config.py            # 로깅 설정
│   ├── 📄 message_chunking.py          # 메시지 분할
│   ├── 📄 sheets_operations.py         # 시트 작업
│   ├── 📄 text_processing.py           # 텍스트 처리
│   │
│   ├── 📁 error_handling/              # 에러 처리 시스템
│   │   ├── 📄 __init__.py
│   │   ├── 📄 decorators.py            # 에러 데코레이터
│   │   ├── 📄 exceptions.py            # 커스텀 예외
│   │   ├── 📄 factory.py               # 에러 팩토리
│   │   ├── 📄 handler.py               # 에러 핸들러
│   │   ├── 📄 README.md                # 에러 처리 문서
│   │   ├── 📄 setup.py                 # 에러 처리 설정
│   │   ├── 📄 specialized.py           # 특화된 에러 처리
│   │   ├── 📄 stats.py                 # 에러 통계
│   │   ├── 📄 test_error_handling.py   # 에러 처리 테스트
│   │   ├── 📄 types.py                 # 에러 타입
│   │   └── 📄 utils.py                 # 에러 유틸리티
│   │
│   └── 📁 sheets/                      # Google Sheets 모듈
│       ├── 📄 __init__.py
│       ├── 📄 cache.py                 # 시트 캐시
│       ├── 📄 connection.py            # 연결 관리
│       ├── 📄 interfaces.py            # 인터페이스
│       ├── 📄 manager.py               # 시트 관리자
│       ├── 📄 operations.py            # 시트 작업
│       └── 📄 performance.py           # 성능 모니터링
│
├── 📁 plugins/                         # 플러그인 시스템
│   ├── 📄 __init__.py
│   │
│   ├── 📁 base/                        # 플러그인 기본
│   │   ├── 📄 __init__.py
│   │   ├── 📄 plugin_base.py           # 플러그인 기본 클래스
│   │   └── 📄 plugin_manager.py        # 플러그인 관리자
│   │
│   ├── 📁 commands/                    # 명령어 플러그인
│   │   ├── 📄 __init__.py
│   │   ├── 📄 command_plugin.py        # 명령어 플러그인
│   │   └── 📄 command_registry.py      # 명령어 레지스트리
│   │
│   └── 📁 examples/                    # 플러그인 예시
│       ├── 📄 __init__.py
│       ├── 📄 hello_plugin.py          # 인사 플러그인
│       └── 📄 weather_plugin.py        # 날씨 플러그인
│
├── 📁 .venv/                           # 가상환경 (생성됨)
├── 📄 bot.log                          # 봇 로그 (생성됨)
├── 📄 command_usage.log                # 명령어 사용 로그 (생성됨)
└── 📄 credentials.json                 # Google 인증 파일 (사용자 제공)
```

## ⚙️ 설정 가이드

### 환경 변수 상세 설명

#### 마스토돈 API 설정

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `MASTODON_CLIENT_ID` | 마스토돈 앱 클라이언트 ID | `abc123def456` |
| `MASTODON_CLIENT_SECRET` | 마스토돈 앱 클라이언트 시크릿 | `xyz789uvw012` |
| `MASTODON_ACCESS_TOKEN` | 마스토돈 액세스 토큰 | `token123` |
| `MASTODON_API_BASE_URL` | 마스토돈 인스턴스 URL | `https://mastodon.social` |

#### Google Sheets 설정

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `SHEET_NAME` | Google Sheets 이름 | `기본 자동봇 시트` |
| `GOOGLE_CREDENTIALS_PATH` | 인증 파일 경로 | `credentials.json` |

#### 봇 동작 설정

| 변수명 | 설명 | 기본값 | 범위 |
|--------|------|--------|------|
| `BOT_MAX_RETRIES` | 최대 재시도 횟수 | `5` | 1-10 |
| `BOT_BASE_WAIT_TIME` | 기본 대기 시간 (초) | `2` | 1-60 |
| `MAX_DICE_COUNT` | 최대 주사위 개수 | `20` | 1-100 |
| `MAX_DICE_SIDES` | 최대 주사위 면수 | `1000` | 2-10000 |
| `MAX_CARD_COUNT` | 최대 카드 장수 | `52` | 1-52 |

#### 시스템 설정

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `SYSTEM_ADMIN_ID` | 관리자 계정 ID | `admin` |
| `LOG_LEVEL` | 로그 레벨 | `INFO` |
| `DEBUG_MODE` | 디버그 모드 | `False` |

### Google Sheets 구조

봇이 사용하는 Google Sheets는 다음 워크시트를 포함해야 합니다:

#### 📊 명단 (사용자 정보)
| 아이디 | 이름 | 등록일 | 마지막활동 |
|--------|------|--------|------------|
| user123 | 김철수 | 2024-01-01 | 2024-01-15 |

#### 🎯 커스텀 (커스텀 명령어)
| 명령어 | 문구 | 활성화 |
|--------|------|--------|
| 안녕 | 안녕하세요! 반갑습니다. | TRUE |
| 날씨 | 오늘 날씨는 맑습니다. | TRUE |

#### 📖 도움말 (명령어 설명)
| 명령어 | 설명 | 카테고리 |
|--------|------|----------|
| 다이스 | 주사위를 굴립니다 | 기본 |
| 카드뽑기 | 카드를 뽑습니다 | 기본 |

#### 🔮 운세 (운세 문구)
| 문구 |
|------|
| 오늘은 좋은 일이 생길 것입니다. |
| 새로운 기회가 찾아올 것입니다. |

## 🔌 플러그인 개발

### 플러그인 구조

```python
from plugins.base.plugin_base import PluginBase, PluginMetadata

class MyPlugin(PluginBase):
    """내 플러그인"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my_plugin",
            version="1.0.0",
            description="내 플러그인 설명",
            author="작성자"
        )
    
    def on_load(self) -> bool:
        """플러그인 로드 시 실행"""
        return True
    
    def on_enable(self) -> bool:
        """플러그인 활성화 시 실행"""
        return True
    
    def on_disable(self) -> bool:
        """플러그인 비활성화 시 실행"""
        return True
    
    def on_unload(self) -> bool:
        """플러그인 언로드 시 실행"""
        return True
```

### 명령어 플러그인 예시

```python
from commands.base_command import BaseCommand
from models.command_result import CommandResult, CommandType

class HelloCommand(BaseCommand):
    """인사 명령어 플러그인"""
    
    def _get_command_type(self) -> CommandType:
        return CommandType.CUSTOM
    
    def _get_command_name(self) -> str:
        return "hello"
    
    def _execute_command(self, user, keywords):
        return "안녕하세요!", None
    
    def get_help_text(self) -> str:
        return "인사를 합니다."
```

## 🛠️ 문제 해결

### 일반적인 문제들

#### 1. 마스토돈 API 연결 실패

**증상**: `마스토돈 API 연결 실패` 오류

**해결 방법**:
1. 환경 변수 확인
2. 액세스 토큰 유효성 검사
3. 네트워크 연결 확인

```bash
# 환경 변수 확인
python check_setup.py
```

#### 2. Google Sheets 연결 실패

**증상**: `Google Sheets 연결 실패` 오류

**해결 방법**:
1. `credentials.json` 파일 확인
2. 서비스 계정 권한 확인
3. 시트 공유 설정 확인

#### 3. 명령어 인식 안됨

**증상**: 봇이 명령어를 인식하지 못함

**해결 방법**:
1. 명령어 형식 확인
2. 봇 계정명 확인
3. 멘션 형식 확인

### 로그 분석

#### 로그 파일 위치
- `bot.log`: 메인 로그
- `command_usage.log`: 명령어 사용 로그

#### 로그 레벨 설정

```env
LOG_LEVEL=DEBUG  # 상세한 디버그 정보
LOG_LEVEL=INFO   # 일반 정보 (기본값)
LOG_LEVEL=WARNING # 경고만
LOG_LEVEL=ERROR  # 오류만
```

### 성능 최적화

#### 캐시 설정

```env
FORTUNE_CACHE_TTL=3600  # 운세 캐시 TTL (초)
```

#### 메모리 사용량 모니터링

```bash
# 메모리 사용량 확인
python -c "import psutil; print(psutil.Process().memory_info().rss / 1024 / 1024, 'MB')"
```

## 🧪 테스트

### 통합 테스트 실행

```bash
python test_integration.py
```

### 플러그인 테스트

```bash
python test_plugin_system.py
```

### 설정 검증

```bash
python check_setup.py
```

## 📊 모니터링

### 성능 통계 확인

봇이 실행 중일 때 다음 명령어로 통계를 확인할 수 있습니다:

```
@봇이름 [상태]    # 봇 상태 확인
@봇이름 [통계]    # 처리 통계 확인
```

### 로그 모니터링

```bash
# 실시간 로그 확인
tail -f bot.log

# 오류 로그만 확인
grep "ERROR" bot.log
```

## 🤝 기여하기

### 개발 환경 설정

1. 저장소 포크
2. 개발 브랜치 생성
3. 변경사항 구현
4. 테스트 실행
5. Pull Request 생성

### 코드 스타일

- **Python**: PEP 8 준수
- **주석**: 한국어 주석 사용
- **문서화**: 모든 함수에 docstring 작성

### 테스트 작성

새로운 기능을 추가할 때는 반드시 테스트를 작성하세요:

```python
def test_new_feature():
    """새로운 기능 테스트"""
    # 테스트 코드 작성
    assert result == expected
```

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 📞 지원

### 이슈 리포트

버그 리포트나 기능 요청은 [GitHub Issues](https://github.com/your-username/mastodon-default-bot/issues)를 이용해 주세요.

### 문의

- **이메일**: your-email@example.com
- **마스토돈**: @your-account@mastodon.social

### 기여자

- [@your-username](https://github.com/your-username) - 프로젝트 메인테이너

---

**⭐ 이 프로젝트가 도움이 되었다면 스타를 눌러주세요!** 