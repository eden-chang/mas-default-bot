"""
Helper functions for result processing
"""

from typing import Optional, List
from ..base.base_result import BaseResult
from ..base.registry import result_registry
from ..enums.command_type import CommandType


def get_registered_result_types() -> List[str]:
    """등록된 결과 타입 목록 반환"""
    return result_registry.list_registered_types()


def create_result_by_type(command_type: str, **kwargs) -> Optional[BaseResult]:
    """타입별 결과 객체 생성"""
    return result_registry.create_result(command_type, **kwargs)


def get_result_summary(result: BaseResult) -> dict:
    """결과 객체 요약 정보 반환"""
    return result.get_summary()


def determine_command_type(command: str) -> CommandType:
    """명령어 문자열에서 타입 결정 (개선된 버전)"""
    command = command.lower().strip()
    
    # 키워드 매핑 테이블 (확장됨)
    keyword_mappings = {
        ('다이스', 'd'): CommandType.DICE,
        ('카드', '카드뽑기'): CommandType.CARD,
        ('운세',): CommandType.FORTUNE,
        ('도움말', '도움'): CommandType.HELP,
        ('소지금', '돈', '재화', '금액'): CommandType.MONEY,
        ('인벤토리', '소지품', '가방', '아이템'): CommandType.INVENTORY,
        ('상점', '가게', '상가'): CommandType.SHOP,
        ('구매', '구입', '사기'): CommandType.BUY,
        ('양도', '전달', '주기', '넘기기'): CommandType.TRANSFER,
        ('설명', '정보', '상세'): CommandType.ITEM_DESCRIPTION,
    }
    
    # 키워드 포함 여부 확인
    for keywords, cmd_type in keyword_mappings.items():
        if any(keyword in command for keyword in keywords):
            return cmd_type
    
    # 시스템 키워드 확인
    try:
        from config.settings import config
        if hasattr(config, 'SYSTEM_KEYWORDS') and command in config.SYSTEM_KEYWORDS:
            # 추가 매핑 로직
            pass
    except:
        pass
    
    return CommandType.CUSTOM 