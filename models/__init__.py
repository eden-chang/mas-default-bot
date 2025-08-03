"""
Models Module for Mastodon Bot

This module contains all data models and structures used throughout the bot.
The models are designed with extensibility and type safety in mind.

Key Components:
- CommandResult: Main result container for all bot commands
- BaseResult: Abstract base class for all result types
- ResultRegistry: Central registry for managing result types
- ResultFactory: Factory for creating result instances
- Various result types (DiceResult, CardResult, etc.)

Usage:
    from models import CommandResult, create_dice_result
    from models import ResultFactory, get_registered_result_types
"""

# Import enums
from .enums.command_type import CommandType
from .enums.command_status import CommandStatus

# Import base classes
from .base.base_result import BaseResult
from .base.registry import ResultRegistry, AutoRegister, result_registry
from .base.factory import ResultFactory, result_factory

# Import core classes
from .core.command_result import CommandResult
from .core.command_stats import CommandStats, GlobalCommandStats, global_stats

# Import result types
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

# Import utility functions
from .utils.helpers import get_registered_result_types, create_result_by_type, get_result_summary, determine_command_type
from .utils.validation import validate_result, validate_dice_result, validate_command_result, validate_result_text_korean_particles
from .utils.korean_particles import detect_korean_particle, format_with_particle

# Import user model
from .user import User

# Import backward compatibility functions
from .command_result import (
    create_dice_result,
    create_card_result,
    create_fortune_result,
    create_custom_result,
    create_help_result,
    create_money_result,
    create_inventory_result,
    create_shop_result,
    create_buy_result,
    create_transfer_result,
    create_item_description_result,
    # Test functions
    test_korean_particles,
    test_plugin_architecture,
    test_auto_registration,
    test_backward_compatibility,
)

# Export all public components
__all__ = [
    # Core classes
    'CommandResult',
    'BaseResult', 
    'ResultRegistry',
    'ResultFactory',
    'result_factory',
    
    # Enums
    'CommandType',
    'CommandStatus',
    
    # All result types
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
    
    # Factory functions (backward compatibility)
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
    'create_item_description_result',
    
    # Test functions
    'test_korean_particles',
    'test_plugin_architecture',
    'test_auto_registration',
    'test_backward_compatibility',
    
    # Utility functions
    'get_registered_result_types',
    'create_result_by_type',
    'validate_result',
    'get_result_summary',
    'determine_command_type',
    'validate_dice_result',
    'validate_command_result',
    'validate_result_text_korean_particles',
    'detect_korean_particle',
    'format_with_particle',
    
    # Decorator
    'AutoRegister',
    
    # User model
    'User',
    
    # Statistics
    'CommandStats',
    'GlobalCommandStats',
    'global_stats',
]

# Version information
__version__ = "2.0.0"

# Module metadata
__author__ = "Mastodon Bot Development Team"
__description__ = "Data models and structures for the Mastodon bot with extensible plugin architecture"

# Convenience function for quick access to common operations
def get_result_factory():
    """Get the global result factory instance."""
    return result_factory

def get_registry():
    """Get the global result registry instance."""
    return result_registry

# Quick validation function
def validate_all_results():
    """Validate all registered result types."""
    results = get_registered_result_types()
    validation_results = []
    for result_type in results:
        try:
            # Create a sample instance and validate it
            if hasattr(result_type, 'create_sample'):
                sample = result_type.create_sample()
                validation_results.append(validate_result(sample))
            else:
                validation_results.append(True)  # Assume valid if no sample method
        except Exception as e:
            validation_results.append(False)
    return all(validation_results)

# Plugin architecture utilities
def register_custom_result(result_class, command_type):
    """
    Register a custom result class with the registry.

    Args:
        result_class: The result class to register
        command_type: The CommandType enum value to associate with this result

    Example:
        @register_custom_result(CommandType.CUSTOM)
        class MyCustomResult(BaseResult):
            # ... implementation
    """
    result_registry.register(command_type, result_class)
    return result_class
