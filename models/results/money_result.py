"""
Money result class
"""

from dataclasses import dataclass
from typing import Dict, Any
from ..base.base_result import BaseResult
from ..base.registry import AutoRegister
from ..enums.command_type import CommandType


@AutoRegister(CommandType.MONEY)
@dataclass
class MoneyResult(BaseResult):
    """소지금 결과 (조사 처리 적용)"""
    user_name: str
    user_id: str
    money_amount: int
    currency_unit: str
    
    def get_result_text(self) -> str:
        """결과 텍스트 반환 (올바른 조사 적용)"""
        try:
            from ..utils.korean_particles import detect_korean_particle
            user_particle = detect_korean_particle(self.user_name, 'topic')
            formatted_amount = f"{self.money_amount:,}"
            return f"{self.user_name}{user_particle} 현재 소지금은 {formatted_amount}{self.currency_unit}입니다."
        except Exception:
            # 폴백: 기존 방식
            formatted_amount = f"{self.money_amount:,}"
            return f"{self.user_name}의 현재 소지금은 {formatted_amount}{self.currency_unit}입니다."
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'user_name': self.user_name,
            'user_id': self.user_id,
            'money_amount': self.money_amount,
            'currency_unit': self.currency_unit
        }
    
    def validate(self) -> bool:
        """유효성 검사"""
        return bool(self.user_name and self.user_id and self.money_amount >= 0 and self.currency_unit) 