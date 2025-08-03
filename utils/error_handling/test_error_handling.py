"""
에러 핸들링 모듈 테스트
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime

# 테스트할 모듈들 임포트
from .types import (
    ErrorSeverity, ErrorCategory, ErrorContext, ErrorHandlingResult,
    BotException, CommandError, UserError, SheetError, BotAPIError
)
from .exceptions import (
    DiceError, CardError, FortuneError, CustomError, UserNotFoundError,
    SheetAccessError
)
from .handler import ErrorHandler, get_error_handler
from .stats import ErrorStats
from .utils import (
    is_retryable_error, is_user_error, is_system_error, should_notify_admin,
    get_user_friendly_message, format_error_for_user, create_error_report
)
from .factory import (
    create_dice_error, create_card_error, create_fortune_error,
    create_custom_error, create_user_not_found_error, create_sheet_error
)
from .specialized import (
    SheetErrorHandler, DiceErrorHandler, CardErrorHandler
)


class TestErrorTypes(unittest.TestCase):
    """기본 타입 테스트"""
    
    def test_error_severity(self):
        """에러 심각도 테스트"""
        self.assertEqual(ErrorSeverity.LOW.value, 1)
        self.assertEqual(ErrorSeverity.MEDIUM.value, 2)
        self.assertEqual(ErrorSeverity.HIGH.value, 3)
        self.assertEqual(ErrorSeverity.CRITICAL.value, 4)
    
    def test_error_category(self):
        """에러 카테고리 테스트"""
        self.assertEqual(ErrorCategory.USER_INPUT.value, "user_input")
        self.assertEqual(ErrorCategory.COMMAND_EXECUTION.value, "command_exec")
        self.assertEqual(ErrorCategory.DATA_ACCESS.value, "data_access")
    
    def test_error_context(self):
        """에러 컨텍스트 테스트"""
        context = ErrorContext(
            operation="test_operation",
            user_id="test_user",
            user_name="테스트"
        )
        
        self.assertEqual(context.operation, "test_operation")
        self.assertEqual(context.user_id, "test_user")
        self.assertEqual(context.user_name, "테스트")
        
        # 데이터 추가 테스트
        context.add_data(test_key="test_value")
        self.assertEqual(context.additional_data["test_key"], "test_value")
        
        # 딕셔너리 변환 테스트
        context_dict = context.to_dict()
        self.assertIn("operation", context_dict)
        self.assertIn("user_id", context_dict)
        self.assertIn("timestamp", context_dict)
    
    def test_error_handling_result(self):
        """에러 처리 결과 테스트"""
        result = ErrorHandlingResult(
            success=False,
            error=Exception("테스트 에러"),
            user_message="테스트 메시지"
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.user_message, "테스트 메시지")
        self.assertTrue(result.has_user_message)


class TestExceptions(unittest.TestCase):
    """예외 클래스 테스트"""
    
    def test_dice_error(self):
        """다이스 에러 테스트"""
        error = DiceError("잘못된 다이스 형식", "2d6", user_name="테스트")
        
        self.assertEqual(error.dice_expression, "2d6")
        self.assertEqual(error.command_type, "dice")
        self.assertEqual(error.error_code, "DICE_ERROR")
        
        # 사용자 메시지 테스트
        user_message = error.get_user_message()
        self.assertIn("잘못된 형식", user_message)
    
    def test_card_error(self):
        """카드 에러 테스트"""
        error = CardError("잘못된 카드 개수", 5, user_name="테스트")
        
        self.assertEqual(error.card_count, 5)
        self.assertEqual(error.command_type, "card")
        self.assertEqual(error.error_code, "CARD_ERROR")
        
        # 사용자 메시지 테스트
        user_message = error.get_user_message()
        self.assertIn("잘못된 개수", user_message)
    
    def test_fortune_error(self):
        """운세 에러 테스트"""
        error = FortuneError(user_name="테스트")
        
        self.assertEqual(error.command_type, "fortune")
        self.assertEqual(error.error_code, "FORTUNE_ERROR")
    
    def test_custom_error(self):
        """커스텀 에러 테스트"""
        error = CustomError("잘못된 커스텀 명령어", "test_command", user_name="테스트")
        
        self.assertEqual(error.custom_command, "test_command")
        self.assertEqual(error.command_type, "custom")
        self.assertEqual(error.error_code, "CUSTOM_ERROR")
    
    def test_user_not_found_error(self):
        """사용자 없음 에러 테스트"""
        error = UserNotFoundError("test_user", "테스트")
        
        self.assertEqual(error.user_id, "test_user")
        self.assertEqual(error.user_name, "테스트")
        self.assertEqual(error.error_code, "USER_NOT_FOUND")
        
        # 사용자 메시지 테스트
        user_message = error.get_user_message()
        self.assertEqual(user_message, "등록되지 않은 사용자입니다.")
    
    def test_sheet_access_error(self):
        """시트 접근 에러 테스트"""
        error = SheetAccessError("test_sheet", "test_operation")
        
        self.assertEqual(error.worksheet, "test_sheet")
        self.assertEqual(error.operation, "test_operation")
        self.assertEqual(error.error_code, "SHEET_ACCESS_ERROR")
        
        # 사용자 메시지 테스트
        user_message = error.get_user_message()
        self.assertIn("접근할 수 없습니다", user_message)


class TestErrorHandler(unittest.TestCase):
    """에러 핸들러 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.handler = ErrorHandler()
        self.context = ErrorContext(
            operation="test_operation",
            user_id="test_user",
            user_name="테스트"
        )
    
    def test_handle_command_error(self):
        """명령어 에러 처리 테스트"""
        error = DiceError("테스트 에러", "2d6", user_name="테스트")
        result = self.handler.handle_command_error(error, self.context)
        
        self.assertFalse(result.success)
        self.assertEqual(result.error, error)
        self.assertTrue(result.should_notify_user)
        self.assertIsNotNone(result.user_message)
    
    def test_handle_user_error(self):
        """사용자 에러 처리 테스트"""
        error = UserError("테스트 사용자 에러", "test_user", "테스트")
        result = self.handler.handle_user_error(error, self.context)
        
        self.assertFalse(result.success)
        self.assertEqual(result.error, error)
        self.assertTrue(result.should_notify_user)
        self.assertFalse(result.should_notify_admin)
    
    def test_get_error_stats(self):
        """에러 통계 테스트"""
        # 에러 기록
        error = DiceError("테스트 에러", "2d6")
        self.handler._stats.record_error(error, self.context)
        
        # 통계 확인
        stats = self.handler.get_error_stats()
        self.assertIn("total_errors", stats)
        self.assertIn("error_types", stats)
        self.assertIn("DiceError", stats["error_types"])


class TestUtils(unittest.TestCase):
    """유틸리티 함수 테스트"""
    
    def test_is_retryable_error(self):
        """재시도 가능한 에러 확인 테스트"""
        # 재시도 가능한 에러
        retryable_error = SheetError("Internal Server Error")
        self.assertTrue(is_retryable_error(retryable_error))
        
        # 재시도 불가능한 에러
        non_retryable_error = UserError("사용자 입력 오류")
        self.assertFalse(is_retryable_error(non_retryable_error))
    
    def test_is_user_error(self):
        """사용자 에러 확인 테스트"""
        # 사용자 에러
        user_error = DiceError("다이스 형식 오류")
        self.assertTrue(is_user_error(user_error))
        
        # 시스템 에러
        system_error = SheetError("시트 접근 오류")
        self.assertFalse(is_user_error(system_error))
    
    def test_is_system_error(self):
        """시스템 에러 확인 테스트"""
        # 시스템 에러
        system_error = SheetError("시트 접근 오류")
        self.assertTrue(is_system_error(system_error))
        
        # 사용자 에러
        user_error = DiceError("다이스 형식 오류")
        self.assertFalse(is_system_error(user_error))
    
    def test_should_notify_admin(self):
        """관리자 알림 확인 테스트"""
        # 관리자 알림 필요한 에러
        critical_error = SheetError("심각한 오류")
        critical_error.severity = ErrorSeverity.HIGH
        self.assertTrue(should_notify_admin(critical_error))
        
        # 관리자 알림 불필요한 에러
        minor_error = UserError("사용자 입력 오류")
        self.assertFalse(should_notify_admin(minor_error))
    
    def test_get_user_friendly_message(self):
        """사용자 친화적 메시지 테스트"""
        error = DiceError("다이스 형식 오류", "2d6", user_name="테스트")
        message = get_user_friendly_message(error, "테스트")
        
        self.assertIsInstance(message, str)
        self.assertIn("잘못된 형식", message)


class TestFactory(unittest.TestCase):
    """팩토리 함수 테스트"""
    
    def test_create_dice_error(self):
        """다이스 에러 생성 테스트"""
        error = create_dice_error("잘못된 형식", "2d6", "테스트")
        
        self.assertIsInstance(error, DiceError)
        self.assertEqual(error.dice_expression, "2d6")
        self.assertEqual(error.user_name, "테스트")
    
    def test_create_card_error(self):
        """카드 에러 생성 테스트"""
        error = create_card_error("잘못된 개수", 5, "테스트")
        
        self.assertIsInstance(error, CardError)
        self.assertEqual(error.card_count, 5)
        self.assertEqual(error.user_name, "테스트")
    
    def test_create_fortune_error(self):
        """운세 에러 생성 테스트"""
        error = create_fortune_error("운세 오류", "테스트")
        
        self.assertIsInstance(error, FortuneError)
        self.assertEqual(error.user_name, "테스트")
    
    def test_create_custom_error(self):
        """커스텀 에러 생성 테스트"""
        error = create_custom_error("잘못된 명령어", "test_command", "테스트")
        
        self.assertIsInstance(error, CustomError)
        self.assertEqual(error.custom_command, "test_command")
        self.assertEqual(error.user_name, "테스트")
    
    def test_create_user_not_found_error(self):
        """사용자 없음 에러 생성 테스트"""
        error = create_user_not_found_error("test_user", "테스트")
        
        self.assertIsInstance(error, UserError)
        self.assertEqual(error.user_id, "test_user")
        self.assertEqual(error.user_name, "테스트")
    
    def test_create_sheet_error(self):
        """시트 에러 생성 테스트"""
        error = create_sheet_error("시트 오류", "test_sheet", "test_operation")
        
        self.assertIsInstance(error, SheetError)
        self.assertEqual(error.worksheet, "test_sheet")
        self.assertEqual(error.operation, "test_operation")


class TestSpecializedHandlers(unittest.TestCase):
    """특화 핸들러 테스트"""
    
    def test_sheet_error_handler(self):
        """시트 에러 핸들러 테스트"""
        # 워크시트 없음 에러
        error = SheetErrorHandler.handle_worksheet_not_found("test_sheet")
        self.assertIsInstance(error, SheetError)
        self.assertEqual(error.worksheet, "test_sheet")
        
        # 데이터 없음 에러
        error = SheetErrorHandler.handle_data_not_found("test_sheet")
        self.assertIsInstance(error, SheetError)
        self.assertEqual(error.worksheet, "test_sheet")
        
        # API 할당량 초과 에러
        error = SheetErrorHandler.handle_api_quota_exceeded()
        self.assertIsInstance(error, SheetError)
        self.assertIn("할당량", error.message)
    
    def test_dice_error_handler(self):
        """다이스 에러 핸들러 테스트"""
        # 잘못된 형식 에러
        error = DiceErrorHandler.handle_invalid_format("2d6", "테스트")
        self.assertIsInstance(error, DiceError)
        self.assertEqual(error.dice_expression, "2d6")
        self.assertEqual(error.user_name, "테스트")
        
        # 개수 제한 초과 에러
        error = DiceErrorHandler.handle_count_limit_exceeded(25, "테스트")
        self.assertIsInstance(error, DiceError)
        self.assertEqual(error.user_name, "테스트")
        
        # 면수 제한 초과 에러
        error = DiceErrorHandler.handle_sides_limit_exceeded(1500, "테스트")
        self.assertIsInstance(error, DiceError)
        self.assertEqual(error.user_name, "테스트")
    
    def test_card_error_handler(self):
        """카드 에러 핸들러 테스트"""
        # 잘못된 개수 에러
        error = CardErrorHandler.handle_invalid_count("abc", "테스트")
        self.assertIsInstance(error, CardError)
        self.assertEqual(error.user_name, "테스트")
        
        # 범위 초과 에러
        error = CardErrorHandler.handle_count_out_of_range(60, "테스트")
        self.assertIsInstance(error, CardError)
        self.assertEqual(error.card_count, 60)
        self.assertEqual(error.user_name, "테스트")
        
        # 개수 누락 에러
        error = CardErrorHandler.handle_missing_count("테스트")
        self.assertIsInstance(error, CardError)
        self.assertEqual(error.user_name, "테스트")


class TestStats(unittest.TestCase):
    """통계 관리 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.stats = ErrorStats()
        self.context = ErrorContext(
            operation="test_operation",
            user_id="test_user",
            user_name="테스트"
        )
    
    def test_record_error(self):
        """에러 기록 테스트"""
        error = DiceError("테스트 에러", "2d6")
        self.stats.record_error(error, self.context)
        
        # 통계 확인
        stats = self.stats.get_stats()
        self.assertGreater(stats["total_errors"], 0)
        self.assertIn("DiceError", stats["error_types"])
    
    def test_get_stats(self):
        """통계 반환 테스트"""
        # 여러 에러 기록
        errors = [
            DiceError("다이스 에러", "2d6"),
            CardError("카드 에러", 5),
            SheetError("시트 에러", "test_sheet")
        ]
        
        for error in errors:
            self.stats.record_error(error, self.context)
        
        # 통계 확인
        stats = self.stats.get_stats()
        self.assertIn("total_errors", stats)
        self.assertIn("error_types", stats)
        self.assertIn("recent_errors_count", stats)
        self.assertIn("severity_breakdown", stats)
    
    def test_reset_stats(self):
        """통계 초기화 테스트"""
        # 에러 기록
        error = DiceError("테스트 에러", "2d6")
        self.stats.record_error(error, self.context)
        
        # 초기화 전 통계
        stats_before = self.stats.get_stats()
        self.assertGreater(stats_before["total_errors"], 0)
        
        # 통계 초기화
        self.stats.reset_stats()
        
        # 초기화 후 통계
        stats_after = self.stats.get_stats()
        self.assertEqual(stats_after["total_errors"], 0)


if __name__ == "__main__":
    unittest.main() 