"""
Result type classes for different commands
"""

# Import all result types
from .dice_result import DiceResult
from .card_result import CardResult
from .fortune_result import FortuneResult
from .custom_result import CustomResult
from .help_result import HelpResult
from .money_result import MoneyResult
from .inventory_result import InventoryResult
from .shop_result import ShopResult
from .buy_result import BuyResult
from .transfer_result import TransferResult
from .item_description_result import ItemDescriptionResult

__all__ = [
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
    'ItemDescriptionResult'
] 