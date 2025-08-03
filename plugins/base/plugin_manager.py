"""
플러그인 관리자
플러그인의 생명주기를 관리하고 동적 로딩을 지원합니다.
"""

import os
import sys
import importlib
import logging
from typing import Dict, List, Optional, Any, Type
from pathlib import Path

from .plugin_base import PluginBase, PluginMetadata


class PluginManager:
    """플러그인 관리자"""
    
    def __init__(self):
        self.plugins: Dict[str, PluginBase] = {}
        self.plugin_paths: Dict[str, str] = {}
        self.logger = logging.getLogger("plugin_manager")
        
        # 플러그인 디렉토리 설정
        self.plugin_directories = []
        
        # 이벤트 콜백
        self._on_plugin_loaded = None
        self._on_plugin_enabled = None
        self._on_plugin_disabled = None
        self._on_plugin_unloaded = None
    
    def add_plugin_directory(self, directory: str):
        """플러그인 디렉토리 추가"""
        if os.path.exists(directory) and os.path.isdir(directory):
            self.plugin_directories.append(directory)
            self.logger.info(f"플러그인 디렉토리 추가: {directory}")
        else:
            self.logger.warning(f"플러그인 디렉토리가 존재하지 않음: {directory}")
    
    def set_event_callbacks(self, on_loaded=None, on_enabled=None, 
                           on_disabled=None, on_unloaded=None):
        """이벤트 콜백 설정"""
        self._on_plugin_loaded = on_loaded
        self._on_plugin_enabled = on_enabled
        self._on_plugin_disabled = on_disabled
        self._on_plugin_unloaded = on_unloaded
    
    def discover_plugins(self) -> List[str]:
        """플러그인 디렉토리에서 플러그인 발견"""
        discovered_plugins = []
        
        for directory in self.plugin_directories:
            if not os.path.exists(directory):
                continue
                
            for item in os.listdir(directory):
                plugin_path = os.path.join(directory, item)
                
                # 디렉토리이고 __init__.py가 있는 경우
                if os.path.isdir(plugin_path):
                    init_file = os.path.join(plugin_path, "__init__.py")
                    if os.path.exists(init_file):
                        discovered_plugins.append(plugin_path)
                        self.logger.debug(f"플러그인 발견: {plugin_path}")
                
                # .py 파일인 경우
                elif item.endswith('.py') and not item.startswith('__'):
                    discovered_plugins.append(plugin_path)
                    self.logger.debug(f"플러그인 발견: {plugin_path}")
        
        return discovered_plugins
    
    def load_plugin(self, plugin_path: str) -> bool:
        """플러그인 로드"""
        try:
            # 이미 로드된 플러그인인지 확인
            if plugin_path in self.plugin_paths.values():
                self.logger.warning(f"이미 로드된 플러그인: {plugin_path}")
                return False
            
            # 플러그인 모듈 로드
            plugin_module = self._load_plugin_module(plugin_path)
            if not plugin_module:
                return False
            
            # 플러그인 인스턴스 생성
            plugin_instance = self._create_plugin_instance(plugin_module)
            if not plugin_instance:
                return False
            
            # 플러그인 등록
            plugin_name = plugin_instance.get_name()
            self.plugins[plugin_name] = plugin_instance
            self.plugin_paths[plugin_name] = plugin_path
            
            # 플러그인 로드 실행
            if plugin_instance.on_load():
                self.logger.info(f"플러그인 로드 성공: {plugin_name}")
                
                # 이벤트 콜백 호출
                if self._on_plugin_loaded:
                    self._on_plugin_loaded(plugin_instance)
                
                return True
            else:
                self.logger.error(f"플러그인 로드 실패: {plugin_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"플러그인 로드 중 오류 발생: {plugin_path} - {e}")
            return False
    
    def load_all_plugins(self) -> Dict[str, bool]:
        """모든 플러그인 로드"""
        results = {}
        discovered_plugins = self.discover_plugins()
        
        for plugin_path in discovered_plugins:
            plugin_name = os.path.basename(plugin_path)
            results[plugin_name] = self.load_plugin(plugin_path)
        
        return results
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """플러그인 활성화"""
        if plugin_name not in self.plugins:
            self.logger.error(f"플러그인을 찾을 수 없음: {plugin_name}")
            return False
        
        plugin = self.plugins[plugin_name]
        
        if plugin.is_enabled():
            self.logger.warning(f"이미 활성화된 플러그인: {plugin_name}")
            return True
        
        if not plugin.is_loaded():
            self.logger.error(f"로드되지 않은 플러그인: {plugin_name}")
            return False
        
        if plugin.on_enable():
            self.logger.info(f"플러그인 활성화 성공: {plugin_name}")
            
            # 이벤트 콜백 호출
            if self._on_plugin_enabled:
                self._on_plugin_enabled(plugin)
            
            return True
        else:
            self.logger.error(f"플러그인 활성화 실패: {plugin_name}")
            return False
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """플러그인 비활성화"""
        if plugin_name not in self.plugins:
            self.logger.error(f"플러그인을 찾을 수 없음: {plugin_name}")
            return False
        
        plugin = self.plugins[plugin_name]
        
        if not plugin.is_enabled():
            self.logger.warning(f"이미 비활성화된 플러그인: {plugin_name}")
            return True
        
        if plugin.on_disable():
            self.logger.info(f"플러그인 비활성화 성공: {plugin_name}")
            
            # 이벤트 콜백 호출
            if self._on_plugin_disabled:
                self._on_plugin_disabled(plugin)
            
            return True
        else:
            self.logger.error(f"플러그인 비활성화 실패: {plugin_name}")
            return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """플러그인 언로드"""
        if plugin_name not in self.plugins:
            self.logger.error(f"플러그인을 찾을 수 없음: {plugin_name}")
            return False
        
        plugin = self.plugins[plugin_name]
        
        # 먼저 비활성화
        if plugin.is_enabled():
            plugin.on_disable()
        
        # 언로드
        if plugin.on_unload():
            self.logger.info(f"플러그인 언로드 성공: {plugin_name}")
            
            # 이벤트 콜백 호출
            if self._on_plugin_unloaded:
                self._on_plugin_unloaded(plugin)
            
            # 등록 정보 제거
            del self.plugins[plugin_name]
            if plugin_name in self.plugin_paths:
                del self.plugin_paths[plugin_name]
            
            return True
        else:
            self.logger.error(f"플러그인 언로드 실패: {plugin_name}")
            return False
    
    def get_plugin(self, plugin_name: str) -> Optional[PluginBase]:
        """플러그인 조회"""
        return self.plugins.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, PluginBase]:
        """모든 플러그인 조회"""
        return self.plugins.copy()
    
    def get_enabled_plugins(self) -> Dict[str, PluginBase]:
        """활성화된 플러그인 조회"""
        return {name: plugin for name, plugin in self.plugins.items() 
                if plugin.is_enabled()}
    
    def get_plugin_status(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """플러그인 상태 조회"""
        plugin = self.get_plugin(plugin_name)
        if plugin:
            return plugin.get_status()
        return None
    
    def get_all_plugin_status(self) -> Dict[str, Dict[str, Any]]:
        """모든 플러그인 상태 조회"""
        return {name: plugin.get_status() for name, plugin in self.plugins.items()}
    
    def _load_plugin_module(self, plugin_path: str):
        """플러그인 모듈 로드"""
        try:
            # 절대 경로로 변환
            abs_path = os.path.abspath(plugin_path)
            
            # 디렉토리인 경우
            if os.path.isdir(abs_path):
                module_name = os.path.basename(abs_path)
                sys.path.insert(0, os.path.dirname(abs_path))
                module = importlib.import_module(module_name)
            else:
                # 파일인 경우
                module_name = os.path.splitext(os.path.basename(abs_path))[0]
                sys.path.insert(0, os.path.dirname(abs_path))
                module = importlib.import_module(module_name)
            
            return module
            
        except Exception as e:
            self.logger.error(f"모듈 로드 실패: {plugin_path} - {e}")
            return None
    
    def _create_plugin_instance(self, module) -> Optional[PluginBase]:
        """플러그인 인스턴스 생성"""
        try:
            # 모듈에서 PluginBase를 상속받은 클래스 찾기
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                
                if (isinstance(attr, type) and 
                    issubclass(attr, PluginBase) and 
                    attr != PluginBase and
                    attr.__name__ not in ['CommandPlugin', 'PluginBase'] and
                    not attr.__name__.startswith('Base') and
                    not attr.__name__.endswith('Base')):
                    
                    # 인스턴스 생성 시도
                    try:
                        # 메타데이터가 있는 경우
                        if hasattr(module, 'PLUGIN_METADATA'):
                            metadata = module.PLUGIN_METADATA
                        else:
                            # 기본 메타데이터 생성
                            metadata = PluginMetadata(
                                name=attr_name,
                                version="1.0.0",
                                description=f"Plugin {attr_name}",
                                author="Unknown"
                            )
                        
                        self.logger.info(f"플러그인 인스턴스 생성 시도: {attr_name}")
                        instance = attr(metadata)
                        self.logger.info(f"플러그인 인스턴스 생성 완료: {attr_name}")
                        return instance
                        
                    except Exception as e:
                        self.logger.error(f"플러그인 인스턴스 생성 실패: {attr_name} - {e}")
                        continue
            
            self.logger.error(f"유효한 플러그인 클래스를 찾을 수 없음: {module.__name__}")
            return None
            
        except Exception as e:
            self.logger.error(f"플러그인 인스턴스 생성 중 오류: {e}")
            return None 