"""
Base classes and protocols for result objects
"""

from .result_protocol import ResultProtocol
from .base_result import BaseResult
from .registry import ResultRegistry, AutoRegister
from .factory import ResultFactory

__all__ = [
    'ResultProtocol',
    'BaseResult', 
    'ResultRegistry',
    'AutoRegister',
    'ResultFactory'
] 