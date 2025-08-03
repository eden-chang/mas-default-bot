"""
Result factory for creating result objects
"""

from typing import Optional, List, Dict, Any
from ..enums.command_type import CommandType
from .base_result import BaseResult
from .registry import result_registry


class ResultFactory:
    """결과 객체 생성 팩토리"""
    
    def __init__(self):
        self.registry = result_registry
    
    def create_result(self, command_type: CommandType, **kwargs) -> Optional[BaseResult]:
        """결과 객체 생성"""
        return self.registry.create_result(command_type.value, **kwargs)
    
    def create_dice_result(self, expression: str, rolls: List[int], modifier: int = 0,
                          threshold: int = None, threshold_type: str = None):
        """다이스 결과 생성"""
        from ..results.dice_result import DiceResult
        
        total = sum(rolls) + modifier
        success_count = None
        fail_count = None
        
        if threshold is not None and threshold_type:
            if threshold_type == '<':
                success_count = sum(1 for roll in rolls if roll <= threshold)
            elif threshold_type == '>':
                success_count = sum(1 for roll in rolls if roll >= threshold)
            
            if success_count is not None:
                fail_count = len(rolls) - success_count
        
        return DiceResult(
            expression=expression,
            rolls=rolls,
            total=total,
            modifier=modifier,
            threshold=threshold,
            threshold_type=threshold_type,
            success_count=success_count,
            fail_count=fail_count
        )
    
    def create_card_result(self, cards: List[str]):
        """카드 결과 생성"""
        from ..results.card_result import CardResult
        return CardResult(cards=cards, count=len(cards))
    
    def create_fortune_result(self, fortune_text: str, user_name: str):
        """운세 결과 생성"""
        from ..results.fortune_result import FortuneResult
        return FortuneResult(fortune_text=fortune_text, user_name=user_name)
    
    def create_custom_result(self, command: str, original_phrase: str, 
                            processed_phrase: str, dice_results: List = None):
        """커스텀 결과 생성"""
        from ..results.custom_result import CustomResult
        return CustomResult(
            command=command,
            original_phrase=original_phrase,
            processed_phrase=processed_phrase,
            dice_results=dice_results or []
        )
    
    def create_help_result(self, help_text: str, command_count: int = 0):
        """도움말 결과 생성"""
        from ..results.help_result import HelpResult
        return HelpResult(help_text=help_text, command_count=command_count)
    
    def create_money_result(self, user_name: str, user_id: str, money_amount: int, currency_unit: str):
        """소지금 결과 생성"""
        from ..results.money_result import MoneyResult
        return MoneyResult(
            user_name=user_name,
            user_id=user_id,
            money_amount=money_amount,
            currency_unit=currency_unit
        )
    
    def create_inventory_result(self, user_name: str, user_id: str, inventory: Dict[str, int], suffix: str, 
                               money: Optional[int] = None, currency_unit: Optional[str] = None):
        """인벤토리 결과 생성"""
        from ..results.inventory_result import InventoryResult
        return InventoryResult(
            user_name=user_name,
            user_id=user_id,
            inventory=inventory,
            suffix=suffix,
            money=money,
            currency_unit=currency_unit
        )
    
    def create_shop_result(self, items: List[Dict[str, Any]], currency_unit: str):
        """상점 결과 생성"""
        from ..results.shop_result import ShopResult
        return ShopResult(items=items, currency_unit=currency_unit)
    
    def create_buy_result(self, user_name: str, user_id: str, item_name: str, quantity: int, 
                         unit_price: int, total_cost: int, remaining_money: int, currency_unit: str):
        """구매 결과 생성"""
        from ..results.buy_result import BuyResult
        return BuyResult(
            user_name=user_name,
            user_id=user_id,
            item_name=item_name,
            quantity=quantity,
            unit_price=unit_price,
            total_cost=total_cost,
            remaining_money=remaining_money,
            currency_unit=currency_unit
        )
    
    def create_transfer_result(self, giver_name: str, giver_id: str, receiver_name: str, 
                              receiver_id: str, item_name: str, dm_sent: bool):
        """양도 결과 생성"""
        from ..results.transfer_result import TransferResult
        return TransferResult(
            success=True,
            message=f"{receiver_name}님에게 양도했습니다.",
            giver_name=giver_name,
            giver_id=giver_id,
            receiver_name=receiver_name,
            receiver_id=receiver_id,
            item_name=item_name,
            dm_sent=dm_sent,
            dm_message=""
        )
    
    def create_item_description_result(self, item_name: str, price: int, description: str, currency_unit: str):
        """아이템 설명 결과 생성"""
        from ..results.item_description_result import ItemDescriptionResult
        return ItemDescriptionResult(
            item_name=item_name,
            price=price,
            description=description,
            currency_unit=currency_unit
        )


# 전역 팩토리 인스턴스
result_factory = ResultFactory() 