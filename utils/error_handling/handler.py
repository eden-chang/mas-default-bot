"""
메인 에러 핸들러 모듈 (보완된 버전)
세분화된 에러 처리와 자동 복구 기능을 제공합니다.
"""

import threading
import weakref
import time
import traceback
import logging
from typing import Optional, Union, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

from .types import (
    ErrorContext, ErrorHandlingResult,
    ErrorSeverity, ErrorCategory, config, detect_korean_particle,
    BotException, CommandError, UserError, SheetError, BotAPIError
)
from .exceptions import (
    DiceError, CardError, FortuneError, CustomError, 
    UserNotFoundError, SheetAccessError
)
from .stats import ErrorStats


class RetryStrategy(Enum):
    """재시도 전략"""
    IMMEDIATE = "immediate"      # 즉시 재시도
    LINEAR_BACKOFF = "linear"    # 선형 백오프
    EXPONENTIAL_BACKOFF = "exponential"  # 지수 백오프
    FIBONACCI_BACKOFF = "fibonacci"  # 피보나치 백오프
    NO_RETRY = "no_retry"       # 재시도 안함


class ErrorRecoveryAction(Enum):
    """에러 복구 액션"""
    RETRY = "retry"              # 재시도
    FALLBACK = "fallback"        # 대체 방법 사용
    CACHE_ONLY = "cache_only"    # 캐시만 사용
    SKIP = "skip"                # 건너뛰기
    RESTART = "restart"          # 재시작
    ALERT = "alert"              # 알림


@dataclass
class ErrorRecoveryPlan:
    """에러 복구 계획"""
    action: ErrorRecoveryAction
    max_attempts: int = 3
    delay_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    fallback_function: Optional[Callable] = None
    alert_threshold: int = 5


@dataclass
class PerformanceMetrics:
    """성능 메트릭"""
    total_errors: int = 0
    handled_errors: int = 0
    recovery_attempts: int = 0
    successful_recoveries: int = 0
    average_recovery_time: float = 0.0
    last_error_time: float = 0.0
    error_rate: float = 0.0


class ErrorHandler:
    """세분화된 에러 핸들러 (보완된 버전)"""
    
    def __init__(self):
        self._stats = ErrorStats()
        self._retry_strategies: Dict[str, RetryStrategy] = {}
        self._recovery_plans: Dict[str, ErrorRecoveryPlan] = {}
        self._error_cache = weakref.WeakValueDictionary()
        self._performance_metrics = PerformanceMetrics()
        self._lock = threading.RLock()
        self._logger = logging.getLogger(__name__)
        
        # 기본 재시도 전략 설정
        self._setup_default_strategies()
        self._setup_default_recovery_plans()
    
    def _setup_default_strategies(self) -> None:
        """기본 재시도 전략 설정"""
        self._retry_strategies = {
            'api_error': RetryStrategy.EXPONENTIAL_BACKOFF,
            'network_error': RetryStrategy.LINEAR_BACKOFF,
            'sheet_error': RetryStrategy.EXPONENTIAL_BACKOFF,
            'user_error': RetryStrategy.NO_RETRY,
            'command_error': RetryStrategy.NO_RETRY,
            'system_error': RetryStrategy.IMMEDIATE,
        }
    
    def _setup_default_recovery_plans(self) -> None:
        """기본 복구 계획 설정"""
        self._recovery_plans = {
            'api_error': ErrorRecoveryPlan(
                action=ErrorRecoveryAction.RETRY,
                max_attempts=3,
                delay_seconds=2.0,
                backoff_multiplier=2.0
            ),
            'network_error': ErrorRecoveryPlan(
                action=ErrorRecoveryAction.RETRY,
                max_attempts=5,
                delay_seconds=1.0,
                backoff_multiplier=1.5
            ),
            'sheet_error': ErrorRecoveryPlan(
                action=ErrorRecoveryAction.FALLBACK,
                max_attempts=2,
                delay_seconds=3.0,
                backoff_multiplier=2.0
            ),
            'user_error': ErrorRecoveryPlan(
                action=ErrorRecoveryAction.SKIP,
                max_attempts=1
            ),
            'command_error': ErrorRecoveryPlan(
                action=ErrorRecoveryAction.SKIP,
                max_attempts=1
            ),
            'system_error': ErrorRecoveryPlan(
                action=ErrorRecoveryAction.ALERT,
                max_attempts=1,
                alert_threshold=1
            ),
        }
    
    def handle_command_error(self, error: Exception, context: ErrorContext) -> ErrorHandlingResult:
        """
        명령어 오류 처리 (세분화된 버전)
        
        Args:
            error: 발생한 예외
            context: 에러 컨텍스트
            
        Returns:
            ErrorHandlingResult: 처리 결과
        """
        start_time = time.time()
        
        try:
            # 에러 분류 및 통계 업데이트
            error_category = self._classify_error(error)
            self._stats.record_error(error, context)
            self._performance_metrics.total_errors += 1
            self._performance_metrics.last_error_time = time.time()
            
            # 복구 계획 결정
            recovery_plan = self._get_recovery_plan(error_category)
            
            # 에러 처리
            result = self._process_error_with_recovery(
                error, context, error_category, recovery_plan
            )
            
            # 성능 메트릭 업데이트
            recovery_time = time.time() - start_time
            self._update_performance_metrics(recovery_time, result.success)
            
            return result
            
        except Exception as e:
            # 에러 처리 중 발생한 에러
            self._logger.error(f"에러 처리 중 예외 발생: {str(e)}")
            return self._create_fallback_result(error, context)
    
    def handle_api_error(self, error: Exception, context: ErrorContext, 
                        max_retries: Optional[int] = None) -> ErrorHandlingResult:
        """
        API 오류 처리 (세분화된 재시도 로직)
        
        Args:
            error: 발생한 예외
            context: 에러 컨텍스트
            max_retries: 최대 재시도 횟수
            
        Returns:
            ErrorHandlingResult: 처리 결과
        """
        start_time = time.time()
        
        # API 에러 분류
        error_category = self._classify_api_error(error)
        recovery_plan = self._get_recovery_plan(error_category)
        
        if max_retries is not None:
            recovery_plan.max_attempts = max_retries
        
        # 재시도 로직 실행
        result = self._execute_retry_strategy(
            error, context, recovery_plan, self._retry_api_operation
        )
        
        # 성능 메트릭 업데이트
        recovery_time = time.time() - start_time
        self._update_performance_metrics(recovery_time, result.success)
        
        return result
    
    def handle_user_error(self, error: Exception, context: ErrorContext) -> ErrorHandlingResult:
        """
        사용자 오류 처리 (세분화된 버전)
        
        Args:
            error: 발생한 예외
            context: 에러 컨텍스트
            
        Returns:
            ErrorHandlingResult: 처리 결과
        """
        # 사용자 오류로 변환
        if not isinstance(error, UserError):
            user_error = UserError(
                message=str(error),
                user_id=context.user_id,
                user_name=context.user_name
            )
        else:
            user_error = error
        
        # 사용자 친화적 메시지 생성
        user_message = self._generate_user_friendly_message(user_error, context)
        
        return ErrorHandlingResult(
            success=False,
            error=user_error,
            context=context,
            user_message=user_message,
            should_log=False,
            should_notify_user=True,
            should_notify_admin=False
        )
    
    def handle_system_error(self, error: Exception, context: ErrorContext) -> ErrorHandlingResult:
        """
        시스템 오류 처리 (자동 복구 포함)
        
        Args:
            error: 발생한 예외
            context: 에러 컨텍스트
            
        Returns:
            ErrorHandlingResult: 처리 결과
        """
        # 시스템 오류는 항상 관리자에게 알림
        result = ErrorHandlingResult(
            success=False,
            error=error,
            context=context,
            user_message=config.get_error_message('SYSTEM_ERROR'),
            should_log=True,
            should_notify_user=True,
            should_notify_admin=True
        )
        
        # 자동 복구 시도
        if self._should_attempt_recovery(error):
            recovery_success = self._attempt_system_recovery(error, context)
            if recovery_success:
                result.success = True
                result.user_message = "시스템이 자동으로 복구되었습니다."
        
        return result
    
    def _classify_error(self, error: Exception) -> str:
        """에러 분류"""
        error_type = type(error).__name__.lower()
        error_message = str(error).lower()
        
        # API 관련 에러
        if any(keyword in error_message for keyword in ['api', 'http', 'network', 'connection']):
            return 'api_error'
        
        # 시트 관련 에러
        if any(keyword in error_message for keyword in ['sheet', 'google', 'spreadsheet']):
            return 'sheet_error'
        
        # 사용자 입력 에러
        if any(keyword in error_message for keyword in ['invalid', 'format', 'syntax']):
            return 'user_error'
        
        # 시스템 에러
        if any(keyword in error_message for keyword in ['memory', 'disk', 'permission']):
            return 'system_error'
        
        # 명령어 에러
        if isinstance(error, (DiceError, CardError, FortuneError, CustomError)):
            return 'command_error'
        
        return 'unknown_error'
    
    def _classify_api_error(self, error: Exception) -> str:
        """API 에러 세분 분류"""
        error_message = str(error).lower()
        
        # 네트워크 에러
        if any(keyword in error_message for keyword in ['timeout', 'connection', 'network']):
            return 'network_error'
        
        # 인증 에러
        if any(keyword in error_message for keyword in ['auth', 'token', 'unauthorized']):
            return 'auth_error'
        
        # 레이트 리밋
        if any(keyword in error_message for keyword in ['rate limit', 'too many requests']):
            return 'rate_limit_error'
        
        # 서버 에러
        if any(keyword in error_message for keyword in ['500', '503', 'internal error']):
            return 'server_error'
        
        return 'api_error'
    
    def _get_recovery_plan(self, error_category: str) -> ErrorRecoveryPlan:
        """복구 계획 가져오기"""
        return self._recovery_plans.get(error_category, ErrorRecoveryPlan(
            action=ErrorRecoveryAction.SKIP,
            max_attempts=1
        ))
    
    def _process_error_with_recovery(self, error: Exception, context: ErrorContext,
                                   error_category: str, recovery_plan: ErrorRecoveryPlan) -> ErrorHandlingResult:
        """복구를 포함한 에러 처리"""
        if recovery_plan.action == ErrorRecoveryAction.RETRY:
            return self._execute_retry_strategy(error, context, recovery_plan, self._retry_operation)
        elif recovery_plan.action == ErrorRecoveryAction.FALLBACK:
            return self._execute_fallback_strategy(error, context, recovery_plan)
        elif recovery_plan.action == ErrorRecoveryAction.CACHE_ONLY:
            return self._execute_cache_only_strategy(error, context, recovery_plan)
        elif recovery_plan.action == ErrorRecoveryAction.ALERT:
            return self._execute_alert_strategy(error, context, recovery_plan)
        else:  # SKIP
            return self._create_skip_result(error, context)
    
    def _execute_retry_strategy(self, error: Exception, context: ErrorContext,
                              recovery_plan: ErrorRecoveryPlan, retry_function: Callable) -> ErrorHandlingResult:
        """재시도 전략 실행"""
        strategy = self._retry_strategies.get(context.operation, RetryStrategy.EXPONENTIAL_BACKOFF)
        
        for attempt in range(recovery_plan.max_attempts):
            try:
                # 재시도 실행
                result = retry_function(error, context, attempt)
                if result.success:
                    self._performance_metrics.successful_recoveries += 1
                    return result
                
                # 재시도 간격 계산
                if attempt < recovery_plan.max_attempts - 1:
                    delay = self._calculate_retry_delay(strategy, attempt, recovery_plan)
                    time.sleep(delay)
                    
            except Exception as retry_error:
                self._logger.warning(f"재시도 {attempt + 1} 실패: {str(retry_error)}")
        
        # 모든 재시도 실패
        return self._create_failure_result(error, context)
    
    def _calculate_retry_delay(self, strategy: RetryStrategy, attempt: int, 
                              recovery_plan: ErrorRecoveryPlan) -> float:
        """재시도 지연 시간 계산"""
        base_delay = recovery_plan.delay_seconds
        
        if strategy == RetryStrategy.IMMEDIATE:
            return 0.0
        elif strategy == RetryStrategy.LINEAR_BACKOFF:
            return base_delay * (attempt + 1)
        elif strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            return base_delay * (recovery_plan.backoff_multiplier ** attempt)
        elif strategy == RetryStrategy.FIBONACCI_BACKOFF:
            return base_delay * self._fibonacci(attempt + 1)
        else:
            return base_delay
    
    def _fibonacci(self, n: int) -> int:
        """피보나치 수열 계산"""
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b
    
    def _execute_fallback_strategy(self, error: Exception, context: ErrorContext,
                                 recovery_plan: ErrorRecoveryPlan) -> ErrorHandlingResult:
        """대체 방법 전략 실행"""
        if recovery_plan.fallback_function:
            try:
                fallback_result = recovery_plan.fallback_function(context)
                return ErrorHandlingResult(
                    success=True,
                    error=error,
                    context=context,
                    user_message="대체 방법으로 처리되었습니다.",
                    should_log=True,
                    should_notify_user=True,
                    should_notify_admin=False
                )
            except Exception as fallback_error:
                self._logger.error(f"대체 방법 실패: {str(fallback_error)}")
        
        return self._create_fallback_result(error, context)
    
    def _execute_cache_only_strategy(self, error: Exception, context: ErrorContext,
                                   recovery_plan: ErrorRecoveryPlan) -> ErrorHandlingResult:
        """캐시만 사용 전략 실행"""
        # 캐시에서 데이터 조회 시도
        try:
            from utils.cache_manager import bot_cache
            cached_data = bot_cache.get(f"fallback_{context.operation}")
            
            if cached_data:
                return ErrorHandlingResult(
                    success=True,
                    error=error,
                    context=context,
                    user_message="캐시된 데이터를 사용합니다.",
                    should_log=True,
                    should_notify_user=True,
                    should_notify_admin=False
                )
        except Exception as cache_error:
            self._logger.error(f"캐시 조회 실패: {str(cache_error)}")
        
        return self._create_cache_fallback_result(error, context)
    
    def _execute_alert_strategy(self, error: Exception, context: ErrorContext,
                              recovery_plan: ErrorRecoveryPlan) -> ErrorHandlingResult:
        """알림 전략 실행"""
        error_count = self._stats.get_error_count(context.operation)
        
        if error_count >= recovery_plan.alert_threshold:
            return ErrorHandlingResult(
                success=False,
                error=error,
                context=context,
                user_message=config.get_error_message('SYSTEM_ERROR'),
                should_log=True,
                should_notify_user=True,
                should_notify_admin=True
            )
        else:
            return self._create_skip_result(error, context)
    
    def _retry_operation(self, error: Exception, context: ErrorContext, attempt: int) -> ErrorHandlingResult:
        """일반 작업 재시도"""
        # 실제 재시도 로직은 호출자가 구현
        return self._create_failure_result(error, context)
    
    def _retry_api_operation(self, error: Exception, context: ErrorContext, attempt: int) -> ErrorHandlingResult:
        """API 작업 재시도"""
        try:
            # API 재시도 로직 (실제 구현은 호출자가 담당)
            return ErrorHandlingResult(
                success=True,
                error=error,
                context=context,
                user_message="API 연결이 복구되었습니다.",
                should_log=True,
                should_notify_user=True,
                should_notify_admin=False
            )
        except Exception as retry_error:
            return self._create_failure_result(retry_error, context)
    
    def _should_attempt_recovery(self, error: Exception) -> bool:
        """복구 시도 여부 결정"""
        error_message = str(error).lower()
        
        # 복구 가능한 에러들
        recoverable_patterns = [
            'connection', 'timeout', 'temporary', 'rate limit',
            'service unavailable', 'internal server error'
        ]
        
        return any(pattern in error_message for pattern in recoverable_patterns)
    
    def _is_retryable_api_error(self, error: Exception) -> bool:
        """API 에러의 재시도 가능 여부 확인"""
        if isinstance(error, (SheetError, BotAPIError)):
            error_message = str(error).lower()
            retryable_patterns = [
                'connection', 'timeout', 'temporary', 'rate limit',
                'service unavailable', 'internal server error', 'quota exceeded'
            ]
            return any(pattern in error_message for pattern in retryable_patterns)
        return False
    
    def _attempt_system_recovery(self, error: Exception, context: ErrorContext) -> bool:
        """시스템 복구 시도"""
        try:
            # 메모리 정리
            import gc
            gc.collect()
            
            # 캐시 정리
            from utils.cache_manager import bot_cache
            bot_cache.clear_old_entries()
            
            # 연결 재설정
            self._reset_connections()
            
            return True
        except Exception as recovery_error:
            self._logger.error(f"시스템 복구 실패: {str(recovery_error)}")
            return False
    
    def _reset_connections(self) -> None:
        """연결 재설정"""
        try:
            # Google Sheets 연결 재설정
            from utils.sheets import SheetsManager
            sheets_manager = SheetsManager()
            if hasattr(sheets_manager, 'connection'):
                sheets_manager.connection = None
            
            # 마스토돈 API 연결 재설정
            # (실제 구현은 main.py에서 담당)
            
        except Exception as e:
            self._logger.error(f"연결 재설정 실패: {str(e)}")
    
    def _generate_user_friendly_message(self, error: Exception, context: ErrorContext) -> str:
        """사용자 친화적 메시지 생성"""
        try:
            if hasattr(error, 'get_korean_error_message') and context.user_name:
                return error.get_korean_error_message(context.user_name)
            elif hasattr(error, 'get_user_message'):
                return error.get_user_message()
            else:
                # 에러 타입별 사용자 친화적 메시지
                error_type = type(error).__name__.lower()
                if 'dice' in error_type:
                    return "주사위 명령어 형식이 올바르지 않습니다. 예: [2d6]"
                elif 'card' in error_type:
                    return "카드 명령어 형식이 올바르지 않습니다. 예: [카드뽑기/5장]"
                elif 'fortune' in error_type:
                    return "운세를 불러오는 중 오류가 발생했습니다."
                elif 'custom' in error_type:
                    return "커스텀 명령어를 찾을 수 없습니다."
                else:
                    return config.get_error_message('TEMPORARY_ERROR')
        except Exception:
            return config.get_error_message('TEMPORARY_ERROR')
    
    def _update_performance_metrics(self, recovery_time: float, success: bool) -> None:
        """성능 메트릭 업데이트"""
        self._performance_metrics.handled_errors += 1
        self._performance_metrics.recovery_attempts += 1
        
        if success:
            self._performance_metrics.successful_recoveries += 1
        
        # 평균 복구 시간 업데이트
        total_recoveries = self._performance_metrics.successful_recoveries
        if total_recoveries > 0:
            current_avg = self._performance_metrics.average_recovery_time
            new_avg = (current_avg * (total_recoveries - 1) + recovery_time) / total_recoveries
            self._performance_metrics.average_recovery_time = new_avg
        
        # 에러율 계산
        stats = self._stats.get_stats()
        total_operations = stats.get('total_errors', 0) + self._performance_metrics.handled_errors
        if total_operations > 0:
            self._performance_metrics.error_rate = self._performance_metrics.total_errors / total_operations
    
    def _create_fallback_result(self, error: Exception, context: ErrorContext) -> ErrorHandlingResult:
        """대체 방법 결과 생성"""
        return ErrorHandlingResult(
            success=False,
            error=error,
            context=context,
            user_message="일시적으로 서비스를 이용할 수 없습니다. 잠시 후 다시 시도해 주세요.",
            should_log=True,
            should_notify_user=True,
            should_notify_admin=True
        )
    
    def _create_failure_result(self, error: Exception, context: ErrorContext) -> ErrorHandlingResult:
        """실패 결과 생성"""
        return ErrorHandlingResult(
            success=False,
            error=error,
            context=context,
            user_message=config.get_error_message('TEMPORARY_ERROR'),
            should_log=True,
            should_notify_user=True,
            should_notify_admin=True
        )
    
    def _create_skip_result(self, error: Exception, context: ErrorContext) -> ErrorHandlingResult:
        """건너뛰기 결과 생성"""
        return ErrorHandlingResult(
            success=False,
            error=error,
            context=context,
            user_message=self._generate_user_friendly_message(error, context),
            should_log=False,
            should_notify_user=True,
            should_notify_admin=False
        )
    
    def _create_cache_fallback_result(self, error: Exception, context: ErrorContext) -> ErrorHandlingResult:
        """캐시 대체 결과 생성"""
        return ErrorHandlingResult(
            success=False,
            error=error,
            context=context,
            user_message="캐시된 데이터를 사용할 수 없습니다.",
            should_log=True,
            should_notify_user=True,
            should_notify_admin=False
        )
    
    def get_error_stats(self) -> Dict[str, Any]:
        """에러 통계 반환 (보완된 버전)"""
        stats = self._stats.get_stats()
        stats.update({
            'performance_metrics': {
                'total_errors': self._performance_metrics.total_errors,
                'handled_errors': self._performance_metrics.handled_errors,
                'recovery_attempts': self._performance_metrics.recovery_attempts,
                'successful_recoveries': self._performance_metrics.successful_recoveries,
                'average_recovery_time': self._performance_metrics.average_recovery_time,
                'error_rate': self._performance_metrics.error_rate,
                'last_error_time': self._performance_metrics.last_error_time
            },
            'recovery_success_rate': (
                self._performance_metrics.successful_recoveries / 
                max(self._performance_metrics.recovery_attempts, 1)
            )
        })
        return stats
    
    def get_performance_report(self) -> Dict[str, Any]:
        """성능 리포트 반환"""
        return {
            'error_handling_performance': {
                'total_errors': self._performance_metrics.total_errors,
                'handled_errors': self._performance_metrics.handled_errors,
                'recovery_success_rate': (
                    self._performance_metrics.successful_recoveries / 
                    max(self._performance_metrics.recovery_attempts, 1)
                ),
                'average_recovery_time': self._performance_metrics.average_recovery_time,
                'error_rate': self._performance_metrics.error_rate
            },
            'recovery_strategies': {
                strategy.value: count for strategy, count in 
                self._stats.get_strategy_counts().items()
            }
        }
    
    def clear_old_stats(self, hours: int = 24) -> int:
        """오래된 통계 정리"""
        cleared_count = self._stats.clear_old_entries(hours)
        
        # 성능 메트릭 초기화
        if hours >= 24:
            self._performance_metrics = PerformanceMetrics()
        
        return cleared_count
    
    def set_retry_strategy(self, operation: str, strategy: RetryStrategy) -> None:
        """재시도 전략 설정"""
        self._retry_strategies[operation] = strategy
    
    def set_recovery_plan(self, error_category: str, plan: ErrorRecoveryPlan) -> None:
        """복구 계획 설정"""
        self._recovery_plans[error_category] = plan


# 전역 에러 핸들러 인스턴스 (싱글톤 패턴)
_global_error_handler: Optional[ErrorHandler] = None
_handler_lock = threading.Lock()


def get_error_handler() -> ErrorHandler:
    """전역 에러 핸들러 반환 (스레드 안전)"""
    global _global_error_handler
    if _global_error_handler is None:
        with _handler_lock:
            if _global_error_handler is None:
                _global_error_handler = ErrorHandler()
    return _global_error_handler


def error_handler_decorator(max_retries: int = 3, recovery_action: ErrorRecoveryAction = ErrorRecoveryAction.RETRY):
    """에러 핸들러 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = get_error_handler()
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as error:
                    context = ErrorContext(
                        operation=func.__name__,
                        user_id=getattr(args[0], 'user_id', None) if args else None,
                        user_name=getattr(args[0], 'user_name', None) if args else None
                    )
                    
                    if attempt == max_retries - 1:
                        # 마지막 시도 실패
                        result = handler.handle_command_error(error, context)
                        raise result.error
                    else:
                        # 재시도
                        time.sleep(1.0 * (attempt + 1))
            
        return wrapper
    return decorator 