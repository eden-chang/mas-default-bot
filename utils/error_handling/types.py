"""
에러 핸들링 기본 타입과 상수 정의
"""

import os
import sys
import threading
import weakref
from typing import Any, Optional, Dict
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import pytz

# 경로 설정 (VM 환경 대응)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

try:
    from gspread.exceptions import APIError as GSpreadAPIError
    from config.settings import config
    from utils.text_processing import detect_korean_particle, format_with_particle
except ImportError:
    # VM 환경에서 임포트 실패 시 폴백
    import importlib.util
    
    try:
        from gspread.exceptions import APIError as GSpreadAPIError
    except ImportError:
        class GSpreadAPIError(Exception):
            pass
    
    # config 로드 시도
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'settings.py')
        spec = importlib.util.spec_from_file_location("settings", config_path)
        settings_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(settings_module)
        config = settings_module.config
    except Exception:
        # 더미 config
        class DummyConfig:
            MAX_RETRIES = 3
            BASE_WAIT_TIME = 1
            DEBUG_MODE = False
            
            def get_error_message(self, key):
                messages = {
                    'TEMPORARY_ERROR': '일시적인 오류가 발생했습니다.',
                    'USER_NOT_FOUND': '사용자를 찾을 수 없습니다.',
                    'DICE_FORMAT_ERROR': '다이스 형식이 올바르지 않습니다.',
                    'CARD_NUMBER_ERROR': '카드 개수가 올바르지 않습니다.',
                    'CARD_FORMAT_ERROR': '카드 형식이 올바르지 않습니다.',
                    'DATA_NOT_FOUND': '데이터를 찾을 수 없습니다.'
                }
                return messages.get(key, '알 수 없는 오류가 발생했습니다.')
        
        config = DummyConfig()
    
    # 텍스트 처리 폴백
    def detect_korean_particle(word: str, particle_type: str) -> str:
        """폴백 조사 처리"""
        if not word:
            return ""
        
        last_char = word[-1]
        if '가' <= last_char <= '힣':
            code = ord(last_char) - ord('가')
            has_final = (code % 28) != 0
            
            if particle_type in ['object', 'eul_reul']:
                return '을' if has_final else '를'
            elif particle_type in ['subject', 'i_ga']:
                return '이' if has_final else '가'
            elif particle_type in ['topic', 'eun_neun']:
                return '은' if has_final else '는'
        
        return ""
    
    def format_with_particle(word: str, particle_type: str) -> str:
        """폴백 조사 결합"""
        particle = detect_korean_particle(word, particle_type)
        return f"{word}{particle}"


# KST 타임존
KST = pytz.timezone('Asia/Seoul')


class ErrorSeverity(Enum):
    """에러 심각도 (최적화된 분류)"""
    LOW = 1          # 사용자 입력 오류 등
    MEDIUM = 2       # 명령어 처리 오류
    HIGH = 3         # 시스템 연동 오류
    CRITICAL = 4     # 서비스 중단 수준


class ErrorCategory(Enum):
    """에러 카테고리 (최적화된 분류)"""
    USER_INPUT = "user_input"           # 사용자 입력 오류
    COMMAND_EXECUTION = "command_exec"  # 명령어 실행 오류
    DATA_ACCESS = "data_access"         # 데이터 접근 오류
    API_INTEGRATION = "api_integration" # API 연동 오류
    SYSTEM_ERROR = "system_error"       # 시스템 오류
    UNKNOWN = "unknown"                 # 분류되지 않은 오류


@dataclass
class ErrorContext:
    """최적화된 에러 컨텍스트"""
    operation: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    command: Optional[str] = None
    command_type: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(KST))
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    def add_data(self, **kwargs) -> None:
        """컨텍스트 데이터 추가"""
        self.additional_data.update(kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'operation': self.operation,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'command': self.command,
            'command_type': self.command_type,
            'timestamp': self.timestamp.isoformat(),
            **self.additional_data
        }
    
    def __enter__(self):
        """컨텍스트 매니저 진입"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        # 예외가 발생한 경우 로깅
        if exc_type is not None:
            from utils.logging_config import logger
            logger.error(f"ErrorContext에서 예외 발생: {exc_type.__name__}: {exc_val}")
        return False  # 예외를 다시 발생시킴


@dataclass
class ErrorHandlingResult:
    """최적화된 에러 처리 결과"""
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    user_message: Optional[str] = None
    retry_count: int = 0
    context: Optional[ErrorContext] = None
    should_log: bool = True
    should_notify_user: bool = False
    should_notify_admin: bool = False
    
    @property
    def has_user_message(self) -> bool:
        """사용자 메시지 존재 여부"""
        return self.user_message is not None and bool(self.user_message.strip())


# 최적화된 커스텀 예외 클래스들
class BotException(Exception):
    """최적화된 봇 기본 예외 클래스 (한글 조사 처리 포함)"""
    
    def __init__(self, message: str, error_code: str = None, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 category: ErrorCategory = ErrorCategory.UNKNOWN,
                 context: ErrorContext = None,
                 user_message: str = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or 'UNKNOWN_ERROR'
        self.severity = severity
        self.category = category
        self.context = context or ErrorContext("unknown")
        self._user_message = user_message
        self.timestamp = datetime.now(KST)
    
    def __str__(self) -> str:
        return self.message
    
    def get_user_message(self) -> str:
        """사용자에게 표시할 메시지 반환 (한글 조사 적용)"""
        if self._user_message:
            return self._user_message
        return self.message
    
    def get_korean_error_message(self, subject: Optional[str] = None) -> str:
        """한글 조사가 적용된 에러 메시지 생성"""
        try:
            if subject:
                subject_particle = detect_korean_particle(subject, 'subject')
                return f"{subject}{subject_particle} {self.get_user_message()}"
            return self.get_user_message()
        except Exception:
            return self.get_user_message()
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (로깅용)"""
        return {
            'error_type': self.__class__.__name__,
            'error_code': self.error_code,
            'message': self.message,
            'severity': self.severity.name,
            'category': self.category.value,
            'timestamp': self.timestamp.isoformat(),
            'context': self.context.to_dict() if self.context else None
        }


class CommandError(BotException):
    """최적화된 명령어 처리 오류"""
    
    def __init__(self, message: str, command: str = None, command_type: str = None,
                 user_id: str = None, user_name: str = None, **kwargs):
        context = ErrorContext(
            operation="command_execution",
            user_id=user_id,
            user_name=user_name,
            command=command,
            command_type=command_type
        )
        
        # kwargs에서 중복될 수 있는 매개변수들을 제거
        for param in ['context', 'error_code', 'severity', 'category', 'user_message']:
            kwargs.pop(param, None)
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.COMMAND_EXECUTION,
            context=context,
            **kwargs
        )
        self.command = command
        self.command_type = command_type


class UserError(BotException):
    """최적화된 사용자 관련 오류"""
    
    def __init__(self, message: str, user_id: str = None, user_name: str = None,
                 error_type: str = "user_error", **kwargs):
        context = ErrorContext(
            operation="user_validation",
            user_id=user_id,
            user_name=user_name
        )
        
        # kwargs에서 중복될 수 있는 매개변수들을 제거
        for param in ['context', 'error_code', 'severity', 'category', 'user_message']:
            kwargs.pop(param, None)
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.USER_INPUT,
            context=context,
            error_code=f'USER_{error_type.upper()}',
            **kwargs
        )
        self.user_id = user_id
        self.user_name = user_name


class SheetError(BotException):
    """최적화된 Google Sheets 오류"""
    
    def __init__(self, message: str = None, worksheet: str = None, 
                 operation: str = None, **kwargs):
        if message is None:
            message = config.get_error_message('TEMPORARY_ERROR')
        
        context = ErrorContext(
            operation=operation or "sheet_access",
            additional_data={'worksheet': worksheet}
        )
        
        # kwargs에서 중복될 수 있는 매개변수들을 제거
        for param in ['context', 'error_code', 'severity', 'category', 'user_message']:
            kwargs.pop(param, None)
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.DATA_ACCESS,
            context=context,
            error_code='SHEET_ERROR',
            **kwargs
        )
        self.worksheet = worksheet
        self.operation = operation


class BotAPIError(BotException):
    """최적화된 API 오류"""
    
    def __init__(self, message: str, api_service: str = None, 
                 operation: str = None, **kwargs):
        context = ErrorContext(
            operation=operation or "api_call",
            additional_data={'api_service': api_service}
        )
        
        # kwargs에서 중복될 수 있는 매개변수들을 제거
        for param in ['context', 'error_code', 'severity', 'category', 'user_message']:
            kwargs.pop(param, None)
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.API_INTEGRATION,
            context=context,
            error_code='API_ERROR',
            **kwargs
        )
        self.api_service = api_service


# 전역 에러 핸들러 인스턴스 (싱글톤 패턴) - handler.py로 이동됨 