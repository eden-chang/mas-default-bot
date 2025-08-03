"""
특화된 에러 핸들러들
"""

from .types import (
    SheetError, ErrorContext, ErrorSeverity, config, detect_korean_particle
)
from .exceptions import (
    DiceError, CardError
)


class SheetErrorHandler:
    """Google Sheets 전용 에러 핸들러 (최적화)"""
    
    @staticmethod
    def handle_worksheet_not_found(worksheet_name: str) -> SheetError:
        """워크시트를 찾을 수 없는 경우"""
        try:
            sheet_particle = detect_korean_particle(worksheet_name, 'object')
            message = f"'{worksheet_name}' 시트{sheet_particle} 찾을 수 없습니다."
        except Exception:
            message = f"'{worksheet_name}' 시트를 찾을 수 없습니다."
        
        return SheetError(
            message=message,
            worksheet=worksheet_name,
            operation="worksheet_access"
        )
    
    @staticmethod
    def handle_data_not_found(worksheet_name: str) -> SheetError:
        """데이터를 찾을 수 없는 경우"""
        return SheetError(
            message=config.get_error_message('DATA_NOT_FOUND'),
            worksheet=worksheet_name,
            operation="data_access"
        )
    
    @staticmethod
    def handle_api_quota_exceeded() -> SheetError:
        """API 할당량 초과"""
        return SheetError(
            message="API 할당량이 초과되었습니다. 잠시 후 다시 시도해 주세요.",
            operation="api_quota"
        )


class DiceErrorHandler:
    """다이스 명령어 전용 에러 핸들러 (최적화)"""
    
    @staticmethod
    def handle_invalid_format(dice_expression: str, user_name: str = None) -> DiceError:
        """잘못된 다이스 형식"""
        return DiceError(
            message=config.get_error_message('DICE_FORMAT_ERROR'),
            dice_expression=dice_expression,
            user_name=user_name
        )
    
    @staticmethod
    def handle_count_limit_exceeded(count: int, user_name: str = None) -> DiceError:
        """다이스 개수 제한 초과"""
        try:
            count_str = f"{count}개"
            count_particle = detect_korean_particle(count_str, 'subject')
            message = f"다이스 {count_str}{count_particle} 너무 많습니다. (최대 20개)"
        except Exception:
            message = f"다이스 {count}개가 너무 많습니다. (최대 20개)"
        
        return DiceError(
            message=message,
            dice_expression=f"{count}d*",
            user_name=user_name
        )
    
    @staticmethod
    def handle_sides_limit_exceeded(sides: int, user_name: str = None) -> DiceError:
        """다이스 면수 제한 초과"""
        try:
            sides_str = f"{sides}면"
            sides_particle = detect_korean_particle(sides_str, 'subject')
            message = f"다이스 {sides_str}{sides_particle} 너무 큽니다. (최대 1000면)"
        except Exception:
            message = f"다이스 {sides}면이 너무 큽니다. (최대 1000면)"
        
        return DiceError(
            message=message,
            dice_expression=f"*d{sides}",
            user_name=user_name
        )


class CardErrorHandler:
    """카드 명령어 전용 에러 핸들러 (최적화)"""
    
    @staticmethod
    def handle_invalid_count(count_str: str, user_name: str = None) -> CardError:
        """잘못된 카드 개수"""
        return CardError(
            message=config.get_error_message('CARD_NUMBER_ERROR'),
            user_name=user_name
        )
    
    @staticmethod
    def handle_count_out_of_range(count: int, user_name: str = None) -> CardError:
        """카드 개수 범위 초과"""
        try:
            count_str = f"{count}장"
            count_particle = detect_korean_particle(count_str, 'subject')
            message = f"카드 {count_str}{count_particle} 범위를 벗어났습니다. (1-52장)"
        except Exception:
            message = f"카드 {count}장이 범위를 벗어났습니다. (1-52장)"
        
        return CardError(
            message=message,
            card_count=count,
            user_name=user_name
        )
    
    @staticmethod
    def handle_missing_count(user_name: str = None) -> CardError:
        """카드 개수 누락"""
        return CardError(
            message=config.get_error_message('CARD_FORMAT_ERROR'),
            user_name=user_name
        ) 