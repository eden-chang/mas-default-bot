"""
Item description result class
"""

from dataclasses import dataclass
from typing import Dict, Any
from ..base.base_result import BaseResult
from ..base.registry import AutoRegister
from ..enums.command_type import CommandType


@AutoRegister(CommandType.ITEM_DESCRIPTION)
@dataclass 
class ItemDescriptionResult(BaseResult):
    """아이템 설명 결과"""
    item_name: str
    price: int
    description: str
    currency_unit: str
    
    def get_result_text(self) -> str:
        """결과 텍스트 반환"""
        formatted_price = f"{self.price:,}"
        return f"{self.item_name}({formatted_price}{self.currency_unit}) : {self.description}"
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'item_name': self.item_name,
            'price': self.price,
            'description': self.description,
            'currency_unit': self.currency_unit
        }
    
    def validate(self) -> bool:
        """유효성 검사"""
        return bool(
            self.item_name and self.description and 
            self.price >= 0 and self.currency_unit
        ) 