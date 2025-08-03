"""
플러그인 시스템 패키지
동적 로딩 및 확장 기능을 위한 플러그인 인프라
"""

from .base.plugin_manager import PluginManager
from .base.plugin_base import PluginBase

__all__ = ['PluginManager', 'PluginBase'] 