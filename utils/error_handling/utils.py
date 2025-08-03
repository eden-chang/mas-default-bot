"""
에러 핸들링 유틸리티 함수들
"""

import traceback
from typing import Optional, Dict, Any
from datetime import datetime

from .types import (
    ErrorContext, ErrorSeverity, ErrorCategory, config, KST,
    BotException, SheetError, BotAPIError, UserError
)
from .exceptions import (
    DiceError, CardError, CustomError
)


def is_retryable_error(error: Exception) -> bool:
    """재시도 가능한 에러인지 확인 (최적화)"""
    if isinstance(error, (SheetError, BotAPIError)):
        error_str = str(error).lower()
        retryable_patterns = ['500', '503', 'internal error', 'timeout', 'rate limit']
        # 성능 최적화: any() 대신 명시적 루프 사용
        for pattern in retryable_patterns:
            if pattern in error_str:
                return True
        return False
    
    if isinstance(error, BotException):
        return error.severity <= ErrorSeverity.MEDIUM
    
    return False


def is_user_error(error: Exception) -> bool:
    """사용자 입력 오류인지 확인 (최적화)"""
    return isinstance(error, (
        UserError, 
        DiceError, 
        CardError,
        CustomError
    )) or (
        isinstance(error, BotException) and 
        error.category == ErrorCategory.USER_INPUT
    )


def is_system_error(error: Exception) -> bool:
    """시스템 오류인지 확인 (최적화)"""
    return isinstance(error, (
        SheetError, 
        BotAPIError
    )) or (
        isinstance(error, BotException) and 
        error.severity >= ErrorSeverity.HIGH
    )


def should_notify_admin(error: Exception) -> bool:
    """관리자에게 알림을 보내야 하는지 확인 (최적화)"""
    if isinstance(error, BotException):
        return error.severity >= ErrorSeverity.HIGH
    
    # 기존 예외의 경우 보수적으로 판단
    return isinstance(error, (SheetError, BotAPIError, ConnectionError, TimeoutError))


def get_user_friendly_message(error: Exception, user_name: Optional[str] = None) -> str:
    """사용자에게 친화적인 에러 메시지 반환 (한글 조사 적용)"""
    if isinstance(error, BotException):
        return error.get_korean_error_message(user_name)
    
    if isinstance(error, (SheetError, BotAPIError)):
        return config.get_error_message('TEMPORARY_ERROR')
    
    # 일반적인 예외의 경우
    return config.get_error_message('TEMPORARY_ERROR')


def format_error_for_user(error: Exception, user_name: Optional[str] = None, 
                         include_details: bool = False) -> str:
    """사용자에게 표시할 에러 메시지 포맷팅 (최적화)"""
    base_message = get_user_friendly_message(error, user_name)
    
    if include_details and config.DEBUG_MODE and isinstance(error, BotException):
        if error.error_code:
            base_message += f"\n(오류 코드: {error.error_code})"
    
    return base_message


def create_error_report(error: Exception, context: Optional[ErrorContext] = None) -> Dict[str, Any]:
    """에러 리포트 생성 (관리자용, 최적화)"""
    now = datetime.now(KST)
    
    report = {
        'timestamp': now.isoformat(),
        'error_type': error.__class__.__name__,
        'error_message': str(error),
        'is_retryable': is_retryable_error(error),
        'is_user_error': is_user_error(error),
        'is_system_error': is_system_error(error),
        'should_notify_admin': should_notify_admin(error)
    }
    
    # BotException 전용 정보
    if isinstance(error, BotException):
        report.update({
            'error_code': error.error_code,
            'severity': error.severity.name,
            'category': error.category.value,
            'error_context': error.context.to_dict() if error.context else None
        })
    
    # 추가 컨텍스트
    if context:
        report['additional_context'] = context.to_dict()
    
    # 디버그 모드에서만 트레이스백 포함
    if config.DEBUG_MODE:
        report['traceback'] = traceback.format_exc()
    
    return report 