"""
에러 처리 데코레이터들
"""

import functools
import time
from typing import Any, Callable, Optional, Tuple, Dict
from contextlib import contextmanager

from .types import (
    ErrorContext, ErrorHandlingResult, config
)
from .handler import get_error_handler
from .exceptions import (
    DiceError, CardError, FortuneError, CustomError,
    SheetAccessError
)
from .types import SheetError, BotAPIError


def error_handler(
    operation: str,
    max_retries: Optional[int] = None,
    fallback_result: Any = None,
    user_message: Optional[str] = None,
    log_level: str = 'warning'
) -> Callable:
    """
    최적화된 에러 처리 데코레이터
    
    Args:
        operation: 작업 이름
        max_retries: 최대 재시도 횟수
        fallback_result: 실패 시 반환값
        user_message: 사용자 메시지
        log_level: 로그 레벨
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            context = ErrorContext(operation=operation)
            handler = get_error_handler()
            
            # 컨텍스트 정보 추출 (함수 인자에서)
            if args and hasattr(args[0], 'user_id'):
                context.user_id = getattr(args[0], 'user_id', None)
                context.user_name = getattr(args[0], 'user_name', None)
            
            max_tries = max_retries or config.MAX_RETRIES
            last_error = None
            
            for attempt in range(max_tries):
                try:
                    return func(*args, **kwargs)
                
                except Exception as e:
                    last_error = e
                    context.add_data(attempt=attempt + 1, max_tries=max_tries)
                    
                    # 재시도 가능한 에러인지 확인
                    if isinstance(e, (SheetError, BotAPIError)) and attempt < max_tries - 1:
                        if handler._is_retryable_api_error(e):
                            wait_time = config.BASE_WAIT_TIME ** (attempt + 1)
                            time.sleep(wait_time)
                            continue
                    
                    # 재시도하지 않는 에러
                    break
            
            # 모든 재시도 실패
            result = handler.handle_command_error(last_error, context)
            
            if user_message:
                result.user_message = user_message
            
            if fallback_result is not None:
                return fallback_result
            else:
                raise result.error
        
        return wrapper
    return decorator


def safe_command_execution(operation: Optional[str] = None) -> Callable:
    """
    안전한 명령어 실행 데코레이터 (최적화)
    
    Args:
        operation: 작업 이름
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Tuple[str, bool]:
            op_name = operation or func.__name__
            context = ErrorContext(operation=op_name)
            handler = get_error_handler()
            
            try:
                # 명령어 객체에서 정보 추출
                if args and hasattr(args[0], '_get_command_name'):
                    context.command_type = args[0]._get_command_name()
                
                # 사용자 정보 추출
                if len(args) >= 2 and hasattr(args[1], 'id'):
                    context.user_id = args[1].id
                    context.user_name = getattr(args[1], 'display_name', getattr(args[1], 'username', None))
                
                result = func(*args, **kwargs)
                
                # CommandResult 처리
                if hasattr(result, 'is_successful'):
                    if result.is_successful():
                        return result.get_user_message(), True
                    else:
                        return result.get_user_message(), False
                
                # 튜플 결과 처리
                if isinstance(result, tuple) and len(result) >= 2:
                    return result[0], result[1] if len(result) > 1 else True
                
                # 단일 결과 처리
                return str(result), True
                
            except Exception as e:
                result = handler.handle_command_error(e, context)
                return result.user_message, False
        
        return wrapper
    return decorator


def safe_execute(
    operation: str,
    max_retries: Optional[int] = None,
    fallback_result: Any = None,
    context_data: Optional[Dict[str, Any]] = None
) -> Callable:
    """
    최적화된 안전한 실행 래퍼
    
    Args:
        operation: 작업 이름
        max_retries: 최대 재시도 횟수
        fallback_result: 실패 시 반환값
        context_data: 추가 컨텍스트 데이터
    """
    def execute(operation_func: Callable) -> ErrorHandlingResult:
        context = ErrorContext(operation=operation)
        if context_data:
            context.add_data(**context_data)
        
        handler = get_error_handler()
        max_tries = max_retries or config.MAX_RETRIES
        last_error = None
        
        for attempt in range(max_tries):
            try:
                result = operation_func()
                return ErrorHandlingResult(success=True, result=result, context=context)
                
            except Exception as e:
                last_error = e
                context.add_data(attempt=attempt + 1, max_tries=max_tries)
                
                # API 에러인 경우 재시도 조건 확인
                if isinstance(e, (SheetError, BotAPIError)) and attempt < max_tries - 1:
                    if handler._is_retryable_api_error(e):
                        wait_time = config.BASE_WAIT_TIME ** (attempt + 1)
                        time.sleep(wait_time)
                        continue
                else:
                    # 재시도하지 않는 에러의 경우 즉시 중단
                    break
        
        # 모든 재시도 실패
        result = handler.handle_command_error(last_error, context)
        if fallback_result is not None:
            result.result = fallback_result
        
        return result
    
    return execute


# 컨텍스트 매니저
@contextmanager
def error_context(operation: str, **context_data):
    """
    에러 컨텍스트 매니저 (최적화)
    
    Args:
        operation: 작업 이름
        **context_data: 컨텍스트 데이터
    """
    context = ErrorContext(operation=operation)
    context.add_data(**context_data)
    handler = get_error_handler()
    
    try:
        yield context
    
    except Exception as e:
        result = handler.handle_command_error(e, context)
        
        # 로깅
        if result.should_log:
            try:
                from utils.logging_config import logger
                error_severity = getattr(result.error, 'severity', None)
                if error_severity and error_severity.value >= 3:  # HIGH 이상
                    logger.error(f"에러 발생: {operation}", exc_info=True)
                else:
                    logger.warning(f"에러 발생: {operation}: {str(e)}")
            except (ImportError, AttributeError):
                # 로거가 없는 경우 기본 출력
                print(f"ERROR in {operation}: {str(e)}")
        
        # 재발생
        raise result.error


# 백워드 호환성을 위한 별칭
def handle_user_command_errors(func: Callable) -> Callable:
    """사용자 명령어 처리 에러를 핸들링하는 데코레이터 (백워드 호환성)"""
    return safe_command_execution()(func)


def retry_on_api_error(max_retries: int = None, fallback_return: Any = None):
    """API 에러 발생 시 자동 재시도하는 데코레이터 (백워드 호환성)"""
    return error_handler(
        operation="api_retry",
        max_retries=max_retries,
        fallback_result=fallback_return
    ) 