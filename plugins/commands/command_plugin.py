"""
명령어 플러그인 기본 클래스
"""

from abc import abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from ..base.plugin_base import PluginBase, PluginMetadata
from models.base.base_result import BaseResult


@dataclass
class CommandContext:
    """명령어 실행 컨텍스트"""
    user_name: str
    user_id: str
    message: str
    command: str
    args: List[str]
    raw_message: str
    timestamp: float
    additional_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_data is None:
            self.additional_data = {}


class CommandPlugin(PluginBase):
    """명령어 플러그인 기본 클래스"""
    
    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        self.command_patterns: List[str] = []
        self.help_text: str = ""
        self.permissions: List[str] = []
        
    def get_command_patterns(self) -> List[str]:
        """명령어 패턴 목록 반환"""
        return self.command_patterns.copy()
    
    def get_help_text(self) -> str:
        """도움말 텍스트 반환"""
        return self.help_text
    
    def get_permissions(self) -> List[str]:
        """필요한 권한 목록 반환"""
        return self.permissions.copy()
    
    def can_execute(self, context: CommandContext) -> bool:
        """명령어 실행 가능 여부 확인"""
        # 기본적으로는 모든 사용자가 실행 가능
        # 하위 클래스에서 권한 체크 등을 구현
        return True
    
    def execute(self, context: CommandContext) -> Optional[BaseResult]:
        """
        명령어 실행 (기본 구현)
        하위 클래스에서 오버라이드하여 구현
        """
        self.logger.warning(f"기본 execute 메서드 호출됨: {self.get_name()}")
        return None
    
    def _enable_implementation(self):
        """플러그인 활성화 구현"""
        # 명령어 등록
        from .command_registry import command_registry
        command_registry.register_plugin_command(self)
        self.logger.info(f"명령어 플러그인 등록: {self.get_name()}")
    
    def _disable_implementation(self):
        """플러그인 비활성화 구현"""
        # 명령어 등록 해제
        from .command_registry import command_registry
        command_registry.unregister_plugin_command(self)
        self.logger.info(f"명령어 플러그인 등록 해제: {self.get_name()}")
    
    def _load_implementation(self):
        """플러그인 로드 구현"""
        # 명령어 패턴 및 도움말 초기화
        self.logger.info(f"CommandPlugin._load_implementation() 시작: {self.get_name()}")
        self.logger.info(f"초기화 전 패턴: {self.command_patterns}")
        
        # 이미 초기화되었는지 확인
        if not self.command_patterns:
            self._initialize_command_info()
        
        # 초기화 후 로깅
        self.logger.info(f"초기화 후 패턴: {self.command_patterns}")
        self.logger.info(f"명령어 정보 초기화 완료: {self.command_patterns}")
        self.logger.info(f"도움말 초기화 완료: {self.help_text}")
    
    def _unload_implementation(self):
        """플러그인 언로드 구현"""
        # 리소스 정리
        self.command_patterns.clear()
        self.help_text = ""
        self.permissions.clear()
    
    def _initialize_command_info(self):
        """명령어 정보 초기화 (하위 클래스에서 오버라이드 가능)"""
        self.logger.info(f"CommandPlugin._initialize_command_info() 기본 구현 호출됨: {self.get_name()}")
        pass
    
    def get_command_info(self) -> Dict[str, Any]:
        """명령어 정보 반환"""
        return {
            'name': self.get_name(),
            'patterns': self.command_patterns,
            'help_text': self.help_text,
            'permissions': self.permissions,
            'enabled': self.is_enabled(),
            'loaded': self.is_loaded()
        } 