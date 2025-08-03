"""
에러 핸들링 모듈 - 모듈화된 구조로 리팩토링
기존 단일 파일을 여러 모듈로 분리하여 관리 용이성 향상
"""

# 새로운 모듈화된 구조로부터 모든 기능을 임포트
from .error_handling import *

# 백워드 호환성을 위한 별칭들
from .error_handling import (
    ErrorHandler, get_error_handler,
    error_handler, safe_command_execution, safe_execute, error_context,
    is_retryable_error, is_user_error, is_system_error, should_notify_admin,
    get_user_friendly_message, format_error_for_user, create_error_report,
    create_dice_error, create_card_error, create_fortune_error,
    create_custom_error, create_user_not_found_error, create_sheet_error,
    setup_global_exception_handler, initialize_error_handling
)

# 모듈 초기화
if __name__ != "__main__":
    try:
        initialize_error_handling()
    except Exception as e:
        print(f"⚠️ 에러 핸들링 초기화 중 오류 발생: {e}") 