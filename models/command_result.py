"""
명령어 결과 데이터 모델 - 리팩토링된 버전
분리된 모듈들을 import하여 사용합니다.
"""

# 새로운 분리된 모듈들에서 import
from .enums.command_type import CommandType
from .enums.command_status import CommandStatus
from .base.base_result import BaseResult
from .base.registry import ResultRegistry, AutoRegister, result_registry
from .base.factory import ResultFactory, result_factory
from .core.command_result import CommandResult
from .core.command_stats import CommandStats, GlobalCommandStats, global_stats
from .utils.helpers import get_registered_result_types, create_result_by_type, get_result_summary, determine_command_type
from .utils.validation import validate_result, validate_dice_result, validate_command_result, validate_result_text_korean_particles
from .utils.korean_particles import detect_korean_particle, format_with_particle

# 결과 타입들 import
from .results.dice_result import DiceResult
from .results.card_result import CardResult
from .results.fortune_result import FortuneResult
from .results.custom_result import CustomResult
from .results.help_result import HelpResult
from .results.money_result import MoneyResult
from .results.inventory_result import InventoryResult
from .results.shop_result import ShopResult
from .results.buy_result import BuyResult
from .results.transfer_result import TransferResult
from .results.item_description_result import ItemDescriptionResult

# 필요한 import 추가
from typing import List, Dict, Any, Optional

# 모듈 레벨에서 export할 클래스들
__all__ = [
    'CommandType',
    'CommandStatus', 
    'CommandResult',
    'DiceResult',
    'CardResult',
    'FortuneResult',
    'CustomResult',
    'HelpResult',
    'MoneyResult',
    'InventoryResult',
    'ShopResult',
    'BuyResult',
    'TransferResult',
    'ItemDescriptionResult',
    'create_dice_result',
    'create_card_result',
    'create_fortune_result',
    'create_custom_result',
    'create_help_result',
    'create_money_result',
    'create_inventory_result',
    'create_shop_result',
    'create_buy_result',
    'create_transfer_result',
    'create_item_description_result'
]

# 하위 호환성을 위한 헬퍼 함수들
def create_dice_result(expression: str, rolls: List[int], modifier: int = 0,
                      threshold: int = None, threshold_type: str = None) -> DiceResult:
    """다이스 결과 생성 헬퍼 (하위 호환성)"""
    return result_factory.create_dice_result(expression, rolls, modifier, threshold, threshold_type)


def create_card_result(cards: List[str]) -> CardResult:
    """카드 결과 생성 헬퍼 (하위 호환성)"""
    return result_factory.create_card_result(cards)


def create_fortune_result(fortune_text: str, user_name: str) -> FortuneResult:
    """운세 결과 생성 헬퍼 (하위 호환성)"""
    return result_factory.create_fortune_result(fortune_text, user_name)


def create_custom_result(command: str, original_phrase: str, 
                        processed_phrase: str, dice_results: List[DiceResult] = None) -> CustomResult:
    """커스텀 결과 생성 헬퍼 (하위 호환성)"""
    return result_factory.create_custom_result(command, original_phrase, processed_phrase, dice_results)


def create_help_result(help_text: str, command_count: int = 0) -> HelpResult:
    """도움말 결과 생성 헬퍼 (하위 호환성)"""
    return result_factory.create_help_result(help_text, command_count)


def create_money_result(user_name: str, user_id: str, money_amount: int, currency_unit: str) -> MoneyResult:
    """소지금 결과 생성 헬퍼 (하위 호환성)"""
    return result_factory.create_money_result(user_name, user_id, money_amount, currency_unit)


def create_inventory_result(user_name: str, user_id: str, inventory: Dict[str, int], suffix: str, 
                           money: Optional[int] = None, currency_unit: Optional[str] = None) -> InventoryResult:
    """인벤토리 결과 생성 헬퍼 (하위 호환성)"""
    return result_factory.create_inventory_result(user_name, user_id, inventory, suffix, money, currency_unit)


def create_shop_result(items: List[Dict[str, Any]], currency_unit: str) -> ShopResult:
    """상점 결과 생성 헬퍼 (하위 호환성)"""
    return result_factory.create_shop_result(items, currency_unit)


def create_buy_result(user_name: str, user_id: str, item_name: str, quantity: int, 
                     unit_price: int, total_cost: int, remaining_money: int, currency_unit: str) -> BuyResult:
    """구매 결과 생성 헬퍼 (하위 호환성)"""
    return result_factory.create_buy_result(user_name, user_id, item_name, quantity, 
                                          unit_price, total_cost, remaining_money, currency_unit)


def create_transfer_result(giver_name: str, giver_id: str, receiver_name: str, 
                          receiver_id: str, item_name: str, dm_sent: bool) -> TransferResult:
    """양도 결과 생성 헬퍼 (하위 호환성)"""
    return result_factory.create_transfer_result(giver_name, giver_id, receiver_name, 
                                               receiver_id, item_name, dm_sent)


def create_item_description_result(item_name: str, price: int, description: str, currency_unit: str) -> ItemDescriptionResult:
    """아이템 설명 결과 생성 헬퍼 (하위 호환성)"""
    return result_factory.create_item_description_result(item_name, price, description, currency_unit)


# 테스트 함수들 (하위 호환성)
def test_korean_particles():
    """한글 조사 처리 테스트 (하위 호환성)"""
    print("=== 한글 조사 처리 테스트 ===")
    
    # 테스트 데이터
    test_users = ["김철수", "박영희", "이몽룡", "성춘향"]
    test_items = ["검", "방패", "포션", "사과", "나무"]
    
    print("1. 운세 결과:")
    for user in test_users:
        fortune = create_fortune_result("좋은 일이 생길 것입니다.", user)
        print(f"  {fortune.get_result_text()}")
    
    print("\n2. 소지금 결과:")
    for user in test_users:
        money = create_money_result(user, f"user_{user}", 10000, "골드")
        print(f"  {money.get_result_text()}")
    
    print("\n3. 양도 결과:")
    for i, item in enumerate(test_items):
        if i < len(test_users):
            transfer = create_transfer_result(test_users[i], f"giver_{i}", 
                                            test_users[(i+1) % len(test_users)], f"receiver_{i}", 
                                            item, True)
            print(f"  {transfer.get_result_text()}")
            print(f"    DM: {transfer.get_dm_message()}")
    
    print("\n4. 구매 결과:")
    for item in test_items:
        buy = create_buy_result("구매자", "buyer", item, 1, 500, 500, 9500, "골드")
        print(f"  {buy.get_result_text()}")
    
    print("=" * 30)


def test_plugin_architecture():
    """플러그인 아키텍처 테스트 (하위 호환성)"""
    print("=== 플러그인 아키텍처 테스트 ===")
    
    # 등록된 타입 확인
    registered_types = get_registered_result_types()
    print(f"등록된 결과 타입: {registered_types}")
    
    # 팩토리를 통한 결과 생성 테스트
    dice_result = result_factory.create_dice_result("2d6", [3, 5], 2)
    print(f"다이스 결과: {dice_result.get_result_text()}")
    
    # 유효성 검사 테스트
    print(f"다이스 결과 유효성: {validate_result(dice_result)}")
    
    # 요약 정보 테스트
    print(f"다이스 결과 요약: {get_result_summary(dice_result)}")


def test_auto_registration():
    """자동 등록 시스템 테스트 (하위 호환성)"""
    print("\n=== 자동 등록 시스템 테스트 ===")
    
    # 모든 등록된 클래스 확인
    for cmd_type in CommandType:
        result_class = result_registry.get_result_class(cmd_type.value)
        if result_class:
            print(f"✅ {cmd_type.value}: {result_class.__name__}")
        else:
            print(f"❌ {cmd_type.value}: 등록되지 않음")
    
    # 팩토리 함수 확인
    for cmd_type in CommandType:
        factory = result_registry.get_factory(cmd_type.value)
        if factory:
            print(f"🔧 {cmd_type.value}: 팩토리 함수 있음")
        else:
            print(f"⚠️ {cmd_type.value}: 팩토리 함수 없음")


def test_backward_compatibility():
    """하위 호환성 테스트 (하위 호환성)"""
    print("\n=== 하위 호환성 테스트 ===")
    
    # 기존 헬퍼 함수들이 정상 작동하는지 확인
    try:
        dice = create_dice_result("1d20", [15])
        card = create_card_result(["♠A", "♥K"])
        fortune = create_fortune_result("좋은 일이 생길 것입니다.", "테스트유저")
        
        print(f"다이스: {dice.get_result_text()}")
        print(f"카드: {card.get_result_text()}")
        print(f"운세: {fortune.get_result_text()}")
        
        print("✅ 모든 기존 헬퍼 함수가 정상 작동합니다.")
        
    except Exception as e:
        print(f"❌ 호환성 문제 발생: {e}")


if __name__ == "__main__":
    test_korean_particles()
    test_plugin_architecture()
    test_auto_registration()
    test_backward_compatibility() 