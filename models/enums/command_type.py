"""
Command type enumeration
"""

from enum import Enum


class CommandType(Enum):
    """명령어 타입 열거형"""
    DICE = "dice"
    CARD = "card"
    FORTUNE = "fortune"
    CUSTOM = "custom"
    HELP = "help"
    MONEY = "money"
    INVENTORY = "inventory"
    SHOP = "shop"
    BUY = "buy"
    TRANSFER = "transfer"
    MONEY_TRANSFER = "money_transfer"
    ITEM_DESCRIPTION = "item_description"
    UNKNOWN = "unknown" 