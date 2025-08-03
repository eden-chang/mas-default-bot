"""
에러 생성 팩토리 함수들
"""

from typing import Optional
from .types import (
    config, detect_korean_particle, UserError, SheetError
)
from .exceptions import (
    DiceError, CardError, FortuneError, CustomError, UserNotFoundError
)


def create_dice_error(message: str, dice_expression: Optional[str] = None, 
                     user_name: Optional[str] = None) -> DiceError:
    """다이스 에러 생성 (한글 조사 처리)"""
    return DiceError(
        message=message,
        dice_expression=dice_expression,
        user_name=user_name
    )


def create_card_error(message: str, card_count: Optional[int] = None,
                     user_name: Optional[str] = None) -> CardError:
    """카드 에러 생성 (한글 조사 처리)"""
    return CardError(
        message=message,
        card_count=card_count,
        user_name=user_name
    )


def create_fortune_error(message: Optional[str] = None,
                        user_name: Optional[str] = None) -> FortuneError:
    """운세 에러 생성 (한글 조사 처리)"""
    return FortuneError(
        message=message,
        user_name=user_name
    )


def create_custom_error(message: str, custom_command: Optional[str] = None,
                       user_name: Optional[str] = None) -> CustomError:
    """커스텀 명령어 에러 생성 (한글 조사 처리)"""
    return CustomError(
        message=message,
        custom_command=custom_command,
        user_name=user_name
    )


def create_user_not_found_error(user_id: str, user_name: Optional[str] = None) -> UserError:
    """사용자 없음 에러 생성 (한글 조사 처리)"""
    try:
        if user_name:
            user_particle = detect_korean_particle(user_name, 'object')
            message = f"{user_name}{user_particle} 찾을 수 없습니다."
        else:
            message = config.get_error_message('USER_NOT_FOUND')
    except Exception:
        message = config.get_error_message('USER_NOT_FOUND')
    
    return UserError(
        message=message,
        user_id=user_id,
        user_name=user_name,
        error_type="not_found"
    )


def create_sheet_error(message: Optional[str] = None, worksheet: Optional[str] = None, 
                      operation: Optional[str] = None) -> SheetError:
    """시트 에러 생성"""
    return SheetError(
        message=message,
        worksheet=worksheet,
        operation=operation
    ) 