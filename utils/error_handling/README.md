# 에러 핸들링 모듈

모듈화된 에러 처리 시스템으로, 기존의 단일 대용량 파일을 기능별로 분리하여 관리 용이성을 향상시켰습니다.

## 구조

```
utils/error_handling/
├── __init__.py          # 메인 인터페이스
├── types.py             # 기본 타입과 상수
├── exceptions.py        # 특화된 예외 클래스들
├── handler.py           # 메인 에러 핸들러
├── stats.py             # 에러 통계 관리
├── decorators.py        # 에러 처리 데코레이터들
├── utils.py             # 유틸리티 함수들
├── specialized.py       # 특화된 에러 핸들러들
├── factory.py           # 에러 생성 팩토리 함수들
├── setup.py             # 설정 및 초기화
└── README.md           # 이 파일
```

## 주요 기능

### 1. 기본 타입 (`types.py`)
- `ErrorSeverity`: 에러 심각도 (LOW, MEDIUM, HIGH, CRITICAL)
- `ErrorCategory`: 에러 카테고리 (USER_INPUT, COMMAND_EXECUTION, 등)
- `ErrorContext`: 에러 컨텍스트 정보
- `ErrorHandlingResult`: 에러 처리 결과
- 기본 예외 클래스들: `BotException`, `CommandError`, `UserError`, `SheetError`, `BotAPIError`

### 2. 특화된 예외 (`exceptions.py`)
- `DiceError`: 다이스 명령어 오류
- `CardError`: 카드 명령어 오류
- `FortuneError`: 운세 명령어 오류
- `CustomError`: 커스텀 명령어 오류
- `UserNotFoundError`: 사용자 없음 오류
- `SheetAccessError`: 시트 접근 오류

### 3. 메인 핸들러 (`handler.py`)
- `ErrorHandler`: 통합 에러 처리 클래스
- 명령어 오류, API 오류, 사용자 오류 처리
- 재시도 로직 및 한글 조사 처리

### 4. 통계 관리 (`stats.py`)
- `ErrorStats`: 에러 통계 수집 및 관리
- 시간별, 타입별 에러 분석
- 메모리 효율적인 통계 저장

### 5. 데코레이터 (`decorators.py`)
- `@error_handler`: 일반적인 에러 처리
- `@safe_command_execution`: 안전한 명령어 실행
- `@safe_execute`: 안전한 함수 실행
- `error_context`: 컨텍스트 매니저

### 6. 유틸리티 (`utils.py`)
- 에러 분류 함수들 (`is_retryable_error`, `is_user_error`, 등)
- 사용자 친화적 메시지 생성
- 에러 리포트 생성

### 7. 특화 핸들러 (`specialized.py`)
- `SheetErrorHandler`: Google Sheets 전용
- `DiceErrorHandler`: 다이스 명령어 전용
- `CardErrorHandler`: 카드 명령어 전용

### 8. 팩토리 함수 (`factory.py`)
- 각종 에러 생성 함수들
- 한글 조사 처리 포함

### 9. 설정 (`setup.py`)
- 전역 예외 핸들러 설정
- 모듈 초기화
- 성능 모니터링

## 사용법

### 기본 사용

```python
from utils.error_handling import (
    ErrorHandler, get_error_handler,
    error_handler, safe_command_execution
)

# 에러 핸들러 사용
handler = get_error_handler()
result = handler.handle_command_error(error, context)

# 데코레이터 사용
@error_handler("dice_command")
def roll_dice(expression):
    # 다이스 로직
    pass

@safe_command_execution()
def process_command(command, user):
    # 명령어 처리
    pass
```

### 특화된 에러 생성

```python
from utils.error_handling import (
    create_dice_error, create_card_error,
    DiceErrorHandler, CardErrorHandler
)

# 에러 생성
error = create_dice_error("잘못된 형식", "2d6", "사용자")

# 특화 핸들러 사용
error = DiceErrorHandler.handle_invalid_format("2d6", "사용자")
```

### 통계 확인

```python
from utils.error_handling import get_error_handler

handler = get_error_handler()
stats = handler.get_error_stats()
print(f"총 에러 수: {stats['total_errors']}")
```

## 확장 방법

### 새로운 에러 타입 추가

1. `exceptions.py`에 새로운 예외 클래스 정의
2. `factory.py`에 생성 함수 추가
3. `specialized.py`에 특화 핸들러 추가 (필요시)

### 새로운 데코레이터 추가

1. `decorators.py`에 새로운 데코레이터 함수 정의
2. `__init__.py`에 임포트 추가

### 새로운 유틸리티 추가

1. `utils.py`에 새로운 유틸리티 함수 정의
2. `__init__.py`에 임포트 추가

## 장점

1. **모듈화**: 기능별로 분리되어 관리 용이
2. **확장성**: 새로운 기능 추가가 쉬움
3. **유지보수성**: 각 모듈이 독립적으로 수정 가능
4. **재사용성**: 필요한 기능만 선택적으로 임포트 가능
5. **테스트 용이성**: 각 모듈별로 독립적인 테스트 가능
6. **백워드 호환성**: 기존 코드와 호환

## 성능 최적화

- 메모리 효율적인 통계 관리
- 약한 참조를 사용한 캐싱
- 스레드 안전한 싱글톤 패턴
- 한글 조사 처리 최적화 