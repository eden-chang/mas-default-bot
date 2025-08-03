"""
Google Sheets 작업 모듈 (리팩토링된 버전)
깔끔한 API와 명확한 책임 분리로 최적화된 구조
"""

from .manager import SheetsManager, get_sheets_manager
from .connection import GoogleSheetsConnection
from .operations import GoogleSheetsOperations
from .cache import SheetsCacheManager, TimeBasedCacheStrategy, NoCacheStrategy
from .performance import SheetsPerformanceMonitor

__all__ = [
    'SheetsManager',
    'GoogleSheetsConnection', 
    'GoogleSheetsOperations',
    'SheetsCacheManager',
    'TimeBasedCacheStrategy',
    'NoCacheStrategy',
    'SheetsPerformanceMonitor',
    'get_sheets_manager'
]

# 기존 코드와의 호환성을 위한 별칭
get_sheets_manager = SheetsManager.get_instance 