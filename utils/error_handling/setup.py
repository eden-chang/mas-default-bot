"""
에러 핸들링 설정 및 초기화 모듈
"""

import sys
from typing import Dict, Any
from .types import ErrorContext, config
from .handler import get_error_handler


def setup_global_exception_handler():
    """최적화된 전역 예외 핸들러 설정"""
    def handle_exception(exc_type, exc_value, exc_traceback):
        """처리되지 않은 예외 핸들러 (최적화)"""
        if issubclass(exc_type, KeyboardInterrupt):
            # Ctrl+C는 정상적으로 처리
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        try:
            # 컨텍스트 생성
            context = ErrorContext(
                operation="global_exception_handler",
                additional_data={
                    'exception_type': exc_type.__name__,
                    'exception_value': str(exc_value)
                }
            )
            
            # 에러 핸들러로 처리
            handler = get_error_handler()
            result = handler.handle_command_error(exc_value, context)
            
            # 로깅
            try:
                from utils.logging_config import logger
                logger.critical(
                    f"처리되지 않은 예외 발생: {exc_type.__name__}: {exc_value}",
                    exc_info=(exc_type, exc_value, exc_traceback)
                )
            except (ImportError, AttributeError):
                print(f"CRITICAL: 처리되지 않은 예외 - {exc_type.__name__}: {exc_value}")
        except Exception as e:
            # 에러 핸들러 자체에서 오류가 발생한 경우
            print(f"Error in sys.excepthook: {e}")
            # 원래 예외 정보 출력
            print(f"Original exception: {exc_type.__name__}: {exc_value}")
            import traceback
            traceback.print_exception(exc_type, exc_value, exc_traceback)
    
    sys.excepthook = handle_exception


def initialize_error_handling():
    """에러 핸들링 모듈 초기화"""
    # 전역 예외 핸들러 설정
    setup_global_exception_handler()
    
    # 에러 핸들러 인스턴스 생성
    get_error_handler()
    
    print("✅ ErrorHandler 초기화 완료")


# 성능 모니터링 함수들
def get_error_performance_metrics() -> Dict[str, Any]:
    """에러 처리 성능 메트릭 반환"""
    handler = get_error_handler()
    stats = handler.get_error_stats()
    
    # 성능 지표 계산
    total_errors = stats.get('total_errors', 0)
    recent_hour_errors = stats.get('recent_hour_errors', 0)
    
    # 에러율 계산
    error_rate = recent_hour_errors  # 시간당 에러 수
    
    # 가장 빈번한 에러 타입
    error_types = stats.get('error_types', {})
    most_common = max(error_types.items(), key=lambda x: x[1]) if error_types else None
    
    return {
        'total_errors': total_errors,
        'hourly_error_rate': error_rate,
        'most_common_error': most_common[0] if most_common else None,
        'most_common_count': most_common[1] if most_common else 0,
        'error_distribution': dict(error_types),
        'health_status': 'healthy' if error_rate < 10 else 'warning' if error_rate < 50 else 'critical'
    }


# 테스트 함수들 (개발용)
def test_error_handling():
    """에러 핸들링 테스트"""
    handler = get_error_handler()
    
    # 테스트 컨텍스트
    context = ErrorContext(
        operation="test",
        user_id="test_user",
        user_name="테스트"
    )
    
    # 다양한 에러 테스트
    from .exceptions import DiceError, CardError, UserError
    from .types import SheetError
    
    test_errors = [
        DiceError("테스트 다이스 에러", "2d6"),
        CardError("테스트 카드 에러", 5),
        UserError("테스트 사용자 에러", "test_user", "테스트"),
        SheetError("테스트 시트 에러", "TestSheet")
    ]
    
    for error in test_errors:
        result = handler.handle_command_error(error, context)
        print(f"에러: {error.__class__.__name__}")
        print(f"사용자 메시지: {result.user_message}")
        print(f"알림 필요: {result.should_notify_admin}")
        print("-" * 50)
    
    # 통계 출력
    stats = handler.get_error_stats()
    print("에러 통계:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    test_error_handling() 