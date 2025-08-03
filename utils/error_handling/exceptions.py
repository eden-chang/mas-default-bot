"""
특화된 예외 클래스들 정의
"""

from .types import (
    CommandError, UserError, SheetError, ErrorContext, 
    ErrorSeverity, ErrorCategory, config, detect_korean_particle
)


class DiceError(CommandError):
    """최적화된 다이스 오류 (한글 조사 처리)"""
    
    def __init__(self, message: str, dice_expression: str = None, **kwargs):
        super().__init__(
            message=message,
            command=f'dice/{dice_expression}' if dice_expression else 'dice',
            command_type='dice',
            error_code='DICE_ERROR',
            **kwargs
        )
        self.dice_expression = dice_expression
    
    def get_user_message(self) -> str:
        """다이스 오류 메시지 (한글 조사 적용)"""
        try:
            if self.dice_expression:
                dice_particle = detect_korean_particle(self.dice_expression, 'subject')
                return f"[{self.dice_expression}]{dice_particle} 잘못된 형식입니다.\n{self.message}"
            return self.message
        except Exception:
            return self.message


class CardError(CommandError):
    """최적화된 카드 오류 (한글 조사 처리)"""
    
    def __init__(self, message: str, card_count: int = None, **kwargs):
        super().__init__(
            message=message,
            command=f'card/{card_count}' if card_count else 'card',
            command_type='card',
            error_code='CARD_ERROR',
            **kwargs
        )
        self.card_count = card_count
    
    def get_user_message(self) -> str:
        """카드 오류 메시지 (한글 조사 처리)"""
        try:
            if self.card_count is not None:
                count_str = f"{self.card_count}장"
                count_particle = detect_korean_particle(count_str, 'subject')
                return f"{count_str}{count_particle} 잘못된 개수입니다.\n{self.message}"
            return self.message
        except Exception:
            return self.message


class FortuneError(CommandError):
    """최적화된 운세 오류"""
    
    def __init__(self, message: str = None, **kwargs):
        if message is None:
            message = "운세를 가져오는 중 오류가 발생했습니다."
        
        super().__init__(
            message=message,
            command='fortune',
            command_type='fortune',
            error_code='FORTUNE_ERROR',
            **kwargs
        )


class CustomError(CommandError):
    """최적화된 커스텀 명령어 오류"""
    
    def __init__(self, message: str, custom_command: str = None, **kwargs):
        super().__init__(
            message=message,
            command=f'custom/{custom_command}' if custom_command else 'custom',
            command_type='custom',
            error_code='CUSTOM_ERROR',
            **kwargs
        )
        self.custom_command = custom_command


class UserNotFoundError(UserError):
    """사용자를 찾을 수 없는 오류"""
    
    def __init__(self, user_id: str = None, user_name: str = None, **kwargs):
        message = config.get_error_message('USER_NOT_FOUND')
        
        context = ErrorContext(
            operation="user_lookup",
            user_id=user_id,
            user_name=user_name,
            additional_data={'error_type': 'user_not_found'}
        )
        
        super().__init__(
            message=message,
            user_id=user_id,
            user_name=user_name,
            error_type="user_not_found",
            context=context,
            error_code='USER_NOT_FOUND',
            **kwargs
        )
    
    def get_user_message(self) -> str:
        return "등록되지 않은 사용자입니다."


class SheetAccessError(SheetError):
    """시트 접근 오류"""
    
    def __init__(self, message: str = None, worksheet: str = None, 
                 operation: str = None, **kwargs):
        if message is None:
            message = "시트에 접근할 수 없습니다."
        
        context = ErrorContext(
            operation=operation or "sheet_access",
            additional_data={'worksheet': worksheet}
        )
        
        super().__init__(
            message=message,
            worksheet=worksheet,
            operation=operation,
            context=context,
            error_code='SHEET_ACCESS_ERROR',
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
    
    def get_user_message(self) -> str:
        return "시트에 접근할 수 없습니다. 잠시 후 다시 시도해주세요." 