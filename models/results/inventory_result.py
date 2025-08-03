"""
Inventory result class
"""

from dataclasses import dataclass
from typing import Dict, Optional, Any
from ..base.base_result import BaseResult
from ..base.registry import AutoRegister
from ..enums.command_type import CommandType


@AutoRegister(CommandType.INVENTORY)
@dataclass
class InventoryResult(BaseResult):
    """인벤토리 결과 (조사 처리 적용)"""
    user_name: str
    user_id: str
    inventory: Dict[str, int]
    suffix: str
    money: Optional[int] = None
    currency_unit: Optional[str] = None
    
    def get_result_text(self) -> str:
        """결과 텍스트 반환 (올바른 조사 적용)"""
        try:
            from ..utils.korean_particles import detect_korean_particle
            user_particle = detect_korean_particle(self.user_name, 'topic')
            
            # 소지금 정보
            money_text = ""
            if self.money is not None and self.currency_unit:
                money_text = f"\n\n- 소지금: {self.money:,}{self.currency_unit}"
            
            if not self.inventory:
                return f"{self.user_name}{user_particle} 현재 가지고 있는 소지품이 없습니다.{money_text}"
            
            # 아이템별 올바른 조사 적용
            item_lines = []
            for item, count in self.inventory.items():
                item_particle = detect_korean_particle(item, 'object')
                item_lines.append(f"- {item}{item_particle} {count}개")
            
            items_text = "\n".join(item_lines)
            
            return f"{self.user_name}{user_particle} 현재 소지품은 다음과 같습니다.\n\n{items_text}{money_text}"
            
        except Exception:
            # 폴백: 기존 방식
            money_text = ""
            if self.money is not None and self.currency_unit:
                money_text = f"\n\n- 소지금: {self.money:,}{self.currency_unit}"
            
            if not self.inventory:
                return f"{self.user_name}{self.suffix} 현재 가지고 있는 소지품이 없습니다.{money_text}"
            
            item_lines = [f"- {item} {count}개" for item, count in self.inventory.items()]
            items_text = "\n".join(item_lines)
            
            return f"{self.user_name}의 현재 소지품은 다음과 같습니다.\n\n{items_text}{money_text}"
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'user_name': self.user_name,
            'user_id': self.user_id,
            'inventory': self.inventory,
            'suffix': self.suffix,
            'money': self.money,
            'currency_unit': self.currency_unit
        }
    
    def validate(self) -> bool:
        """유효성 검사"""
        return bool(self.user_name and self.user_id and self.inventory is not None) 