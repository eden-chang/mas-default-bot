"""
Shop result class
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from ..base.base_result import BaseResult
from ..base.registry import AutoRegister
from ..enums.command_type import CommandType


@AutoRegister(CommandType.SHOP)
@dataclass
class ShopResult(BaseResult):
    """상점 결과"""
    items: List[Dict[str, Any]]
    currency_unit: str
    
    def get_result_text(self) -> str:
        """결과 텍스트 반환"""
        if not self.items:
            return "현재 상점에 판매중인 아이템이 없습니다."
        
        item_lines = []
        for item in self.items:
            name = item['name']
            price = item['price']
            description = item['description']
            item_lines.append(f"{name} ({price:,}{self.currency_unit}) : {description}")
        
        items_text = "\n".join(item_lines)
        return f"상점에서 구매 가능한 목록입니다.\n\n{items_text}"
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'items': self.items,
            'currency_unit': self.currency_unit
        }
    
    def validate(self) -> bool:
        """유효성 검사"""
        return bool(self.items is not None and self.currency_unit) 