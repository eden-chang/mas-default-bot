"""
에러 핸들링 패키지 - 모듈화된 구조
각 기능별로 분리된 에러 처리 모듈들을 제공합니다.
"""

from .types import (
    ErrorSeverity, ErrorCategory, ErrorContext, ErrorHandlingResult,
    BotException, CommandError, UserError, SheetError, BotAPIError
)

from .exceptions import (
    DiceError, CardError, FortuneError, CustomError, UserNotFoundError,
    SheetAccessError
)

from .handler import ErrorHandler, get_error_handler

from .decorators import (
    error_handler, safe_command_execution, safe_execute, error_context
)

from .utils import (
    is_retryable_error, is_user_error, is_system_error, should_notify_admin,
    get_user_friendly_message, format_error_for_user, create_error_report
)

from .specialized import (
    SheetErrorHandler, DiceErrorHandler, CardErrorHandler
)

from .stats import ErrorStats

from .factory import (
    create_dice_error, create_card_error, create_fortune_error,
    create_custom_error, create_user_not_found_error, create_sheet_error
)

from .setup import setup_global_exception_handler, initialize_error_handling

# 주요 인터페이스들
__all__ = [
    # 핵심 타입들
    'ErrorSeverity', 'ErrorCategory', 'ErrorContext', 'ErrorHandlingResult',
    'BotException', 'CommandError', 'UserError', 'SheetError', 'BotAPIError',
    
    # 특화 예외들
    'DiceError', 'CardError', 'FortuneError', 'CustomError', 
    'UserNotFoundError', 'SheetAccessError',
    
    # 핸들러
    'ErrorHandler', 'get_error_handler',
    
    # 데코레이터들
    'error_handler', 'safe_command_execution', 'safe_execute', 'error_context',
    
    # 유틸리티 함수들
    'is_retryable_error', 'is_user_error', 'is_system_error', 
    'should_notify_admin', 'get_user_friendly_message', 
    'format_error_for_user', 'create_error_report',
    
    # 특화 핸들러들
    'SheetErrorHandler', 'DiceErrorHandler', 'CardErrorHandler',
    
    # 팩토리 함수들
    'create_dice_error', 'create_card_error', 'create_fortune_error',
    'create_custom_error', 'create_user_not_found_error', 'create_sheet_error',
    
    # 설정 함수들
    'setup_global_exception_handler', 'initialize_error_handling'
]

# 백워드 호환성을 위한 별칭
from .decorators import handle_user_command_errors, retry_on_api_error
__all__.extend(['handle_user_command_errors', 'retry_on_api_error'])

# 백워드 호환성을 위한 handle_error 함수
def handle_error(error: Exception, context: str = "general", user_id: str = None) -> str:
    """에러 처리 함수 (백워드 호환성)"""
    from .handler import get_error_handler
    handler = get_error_handler()
    result = handler.handle_error(error, context, user_id)
    return result.user_message

# 백워드 호환성을 위한 log_error 함수
def log_error(message: str, error: Exception = None, **kwargs) -> None:
    """에러 로깅 함수 (백워드 호환성)"""
    from utils.logging_config import log_error as logging_error
    if error:
        logging_error(f"{message}: {error}", exc_info=True, **kwargs)
    else:
        logging_error(message, **kwargs) 