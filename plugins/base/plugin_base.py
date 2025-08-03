"""
플러그인 기본 클래스
모든 플러그인의 기본이 되는 클래스
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging


@dataclass
class PluginMetadata:
    """플러그인 메타데이터"""
    name: str
    version: str
    description: str
    author: str = "Unknown"
    dependencies: List[str] = None
    permissions: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.permissions is None:
            self.permissions = []


class PluginBase(ABC):
    """플러그인 기본 클래스"""
    
    def __init__(self, metadata: PluginMetadata):
        self.metadata = metadata
        self.enabled = False
        self.loaded = False
        self.logger = logging.getLogger(f"plugin.{metadata.name}")
        
        # 플러그인 상태
        self._error_count = 0
        self._last_error = None
        
    def get_name(self) -> str:
        """플러그인 이름 반환"""
        return self.metadata.name
    
    def get_version(self) -> str:
        """플러그인 버전 반환"""
        return self.metadata.version
    
    def get_description(self) -> str:
        """플러그인 설명 반환"""
        return self.metadata.description
    
    def is_enabled(self) -> bool:
        """플러그인 활성화 상태 확인"""
        return self.enabled
    
    def is_loaded(self) -> bool:
        """플러그인 로드 상태 확인"""
        return self.loaded
    
    def get_error_info(self) -> Dict[str, Any]:
        """에러 정보 반환"""
        return {
            'error_count': self._error_count,
            'last_error': str(self._last_error) if self._last_error else None
        }
    
    def on_load(self) -> bool:
        """
        플러그인 로드 시 호출
        반환값: True=성공, False=실패
        """
        try:
            self.logger.info(f"플러그인 로드 중: {self.metadata.name}")
            self._load_implementation()
            self.loaded = True
            self.logger.info(f"플러그인 로드 완료: {self.metadata.name}")
            return True
        except Exception as e:
            self._error_count += 1
            self._last_error = e
            self.logger.error(f"플러그인 로드 실패: {self.metadata.name} - {e}")
            return False
    
    def on_enable(self) -> bool:
        """
        플러그인 활성화 시 호출
        반환값: True=성공, False=실패
        """
        try:
            self.logger.info(f"플러그인 활성화 중: {self.metadata.name}")
            self._enable_implementation()
            self.enabled = True
            self.logger.info(f"플러그인 활성화 완료: {self.metadata.name}")
            return True
        except Exception as e:
            self._error_count += 1
            self._last_error = e
            self.logger.error(f"플러그인 활성화 실패: {self.metadata.name} - {e}")
            return False
    
    def on_disable(self) -> bool:
        """
        플러그인 비활성화 시 호출
        반환값: True=성공, False=실패
        """
        try:
            self.logger.info(f"플러그인 비활성화 중: {self.metadata.name}")
            self._disable_implementation()
            self.enabled = False
            self.logger.info(f"플러그인 비활성화 완료: {self.metadata.name}")
            return True
        except Exception as e:
            self._error_count += 1
            self._last_error = e
            self.logger.error(f"플러그인 비활성화 실패: {self.metadata.name} - {e}")
            return False
    
    def on_unload(self) -> bool:
        """
        플러그인 언로드 시 호출
        반환값: True=성공, False=실패
        """
        try:
            self.logger.info(f"플러그인 언로드 중: {self.metadata.name}")
            self._unload_implementation()
            self.loaded = False
            self.enabled = False
            self.logger.info(f"플러그인 언로드 완료: {self.metadata.name}")
            return True
        except Exception as e:
            self._error_count += 1
            self._last_error = e
            self.logger.error(f"플러그인 언로드 실패: {self.metadata.name} - {e}")
            return False
    
    @abstractmethod
    def _load_implementation(self):
        """플러그인 로드 구현 (하위 클래스에서 구현)"""
        pass
    
    @abstractmethod
    def _enable_implementation(self):
        """플러그인 활성화 구현 (하위 클래스에서 구현)"""
        pass
    
    @abstractmethod
    def _disable_implementation(self):
        """플러그인 비활성화 구현 (하위 클래스에서 구현)"""
        pass
    
    @abstractmethod
    def _unload_implementation(self):
        """플러그인 언로드 구현 (하위 클래스에서 구현)"""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """플러그인 상태 정보 반환"""
        return {
            'name': self.metadata.name,
            'version': self.metadata.version,
            'description': self.metadata.description,
            'author': self.metadata.author,
            'enabled': self.enabled,
            'loaded': self.loaded,
            'error_count': self._error_count,
            'last_error': str(self._last_error) if self._last_error else None
        } 