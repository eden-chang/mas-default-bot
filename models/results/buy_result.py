"""
Buy result class
"""

from dataclasses import dataclass
from typing import Dict, Any
from ..base.base_result import BaseResult
from ..base.registry import AutoRegister
from ..enums.command_type import CommandType


@AutoRegister(CommandType.BUY)
@dataclass
class BuyResult(BaseResult):
    """구매 결과 (조사 처리 적용)"""
    user_name: str
    user_id: str
    item_name: str
    quantity: int
    unit_price: int
    total_cost: int
    remaining_money: int
    currency_unit: str
    
    def get_result_text(self) -> str:
        """결과 텍스트 반환 (올바른 조사 적용)"""
        try:
            from ..utils.korean_particles import detect_korean_particle
            item_particle = detect_korean_particle(self.item_name, 'object')
            return f"{self.item_name}{item_particle} {self.quantity}개 구매했습니다."
        except Exception:
            # 폴백: 기존 방식
            return f"{self.item_name} {self.quantity}개 구매에 성공했습니다."
    
    def get_detailed_result_text(self) -> str:
        """상세한 구매 결과 텍스트"""
        try:
            from ..utils.korean_particles import detect_korean_particle
            user_particle = detect_korean_particle(self.user_name, 'subject')
            item_particle = detect_korean_particle(self.item_name, 'object')
            
            return (f"{self.user_name}{user_particle} {self.item_name}{item_particle} {self.quantity}개 구매했습니다.\n"
                   f"단가: {self.unit_price:,}{self.currency_unit}\n"
                   f"총 비용: {self.total_cost:,}{self.currency_unit}\n"
                   f"잔여 금액: {self.remaining_money:,}{self.currency_unit}")
        except Exception:
            # 폴백
            return (f"{self.user_name}이 {self.item_name}을 {self.quantity}개 구매했습니다.\n"
                   f"단가: {self.unit_price:,}{self.currency_unit}\n"
                   f"총 비용: {self.total_cost:,}{self.currency_unit}\n"
                   f"잔여 금액: {self.remaining_money:,}{self.currency_unit}")
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'user_name': self.user_name,
            'user_id': self.user_id,
            'item_name': self.item_name,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'total_cost': self.total_cost,
            'remaining_money': self.remaining_money,
            'currency_unit': self.currency_unit
        }
    
    def validate(self) -> bool:
        """유효성 검사"""
        return bool(
            self.user_name and self.user_id and self.item_name and 
            self.quantity > 0 and self.unit_price >= 0 and 
            self.total_cost >= 0 and self.remaining_money >= 0 and 
            self.currency_unit
        ) 