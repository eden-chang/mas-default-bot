"""
Result registry and auto-registration system
"""

from typing import Dict, Type, Optional, List, Callable
from functools import wraps
from ..enums.command_type import CommandType
from .base_result import BaseResult
import logging


class ResultRegistry:
    """결과 클래스 자동 등록 시스템"""
    
    def __init__(self):
        self._results: Dict[str, Type[BaseResult]] = {}
        self._command_types: Dict[str, CommandType] = {}
        self._factories: Dict[str, Callable] = {}
        self.logger = logging.getLogger("result_registry")
        
        # 플러그인 관련
        self._plugin_results: Dict[str, Type[BaseResult]] = {}
        self._plugin_factories: Dict[str, Callable] = {}
    
    def register(self, command_type: CommandType, result_class: Type[BaseResult], 
                                 factory_func: Callable = None):
        """결과 클래스 등록"""
        self._results[command_type.value] = result_class
        self._command_types[command_type.value] = command_type
        if factory_func:
            self._factories[command_type.value] = factory_func
    
    def get_result_class(self, command_type: str) -> Optional[Type[BaseResult]]:
        """결과 클래스 조회"""
        return self._results.get(command_type)
    
    def get_command_type(self, command_type: str) -> Optional[CommandType]:
        """명령어 타입 조회"""
        return self._command_types.get(command_type)
    
    def get_factory(self, command_type: str) -> Optional[Callable]:
        """팩토리 함수 조회"""
        return self._factories.get(command_type)
    
    def list_registered_types(self) -> List[str]:
        """등록된 타입 목록 반환"""
        return list(self._results.keys())
    
    def create_result(self, command_type: str, **kwargs) -> Optional[BaseResult]:
        """결과 객체 생성"""
        # 먼저 플러그인 팩토리 확인
        factory = self.get_factory(command_type)
        if factory:
            return factory(**kwargs)
        
        # 플러그인 결과 클래스 확인
        result_class = self.get_result_class(command_type)
        if result_class:
            return result_class(**kwargs)
        
        return None
    
    def register_plugin_result(self, command_type: str, result_class: Type[BaseResult], 
                              factory_func: Callable = None):
        """플러그인 결과 클래스 등록"""
        self._plugin_results[command_type] = result_class
        if factory_func:
            self._plugin_factories[command_type] = factory_func
        self.logger.info(f"플러그인 결과 등록: {command_type}")
    
    def unregister_plugin_result(self, command_type: str):
        """플러그인 결과 클래스 등록 해제"""
        if command_type in self._plugin_results:
            del self._plugin_results[command_type]
        if command_type in self._plugin_factories:
            del self._plugin_factories[command_type]
        self.logger.info(f"플러그인 결과 등록 해제: {command_type}")
    
    def get_plugin_results(self) -> Dict[str, Type[BaseResult]]:
        """플러그인 결과 클래스 목록 반환"""
        return self._plugin_results.copy()
    
    def is_plugin_result(self, command_type: str) -> bool:
        """플러그인 결과인지 확인"""
        return command_type in self._plugin_results


# 전역 레지스트리 인스턴스
result_registry = ResultRegistry()


def AutoRegister(command_type: CommandType, factory_func: Callable = None):
    """자동 등록 데코레이터"""
    def decorator(cls: Type[BaseResult]):
        # 클래스 등록
        result_registry.register(command_type, cls, factory_func)
        
        # 클래스에 메타데이터 추가
        cls._command_type = command_type
        cls._registered = True
        
        @wraps(cls)
        def wrapper(*args, **kwargs):
            return cls(*args, **kwargs)
        
        return wrapper
    return decorator 