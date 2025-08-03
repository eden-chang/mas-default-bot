"""
명령어 레지스트리
플러그인 명령어들을 관리하고 기존 명령어 시스템과 통합
"""

import re
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass

from .command_plugin import CommandPlugin, CommandContext
from models.base.base_result import BaseResult


@dataclass
class CommandHandler:
    """명령어 핸들러"""
    plugin: CommandPlugin
    patterns: List[str]
    help_text: str
    permissions: List[str]
    enabled: bool = True


class CommandRegistry:
    """명령어 레지스트리"""
    
    def __init__(self):
        self.plugin_commands: Dict[str, CommandHandler] = {}
        self.logger = logging.getLogger("command_registry")
        
        # 기존 명령어 시스템과의 통합을 위한 콜백
        self._on_command_registered = None
        self._on_command_unregistered = None
    
    def set_event_callbacks(self, on_registered=None, on_unregistered=None):
        """이벤트 콜백 설정"""
        self._on_command_registered = on_registered
        self._on_command_unregistered = on_unregistered
    
    def register_plugin_command(self, plugin: CommandPlugin):
        """플러그인 명령어 등록"""
        if not plugin.is_loaded():
            self.logger.error(f"로드되지 않은 플러그인 명령어 등록 시도: {plugin.get_name()}")
            return False
        
        command_name = plugin.get_name()
        patterns = plugin.get_command_patterns()
        help_text = plugin.get_help_text()
        permissions = plugin.get_permissions()
        
        handler = CommandHandler(
            plugin=plugin,
            patterns=patterns,
            help_text=help_text,
            permissions=permissions,
            enabled=plugin.is_enabled()
        )
        
        self.plugin_commands[command_name] = handler
        self.logger.info(f"플러그인 명령어 등록: {command_name} (패턴: {patterns})")
        
        # 이벤트 콜백 호출
        if self._on_command_registered:
            self._on_command_registered(command_name, handler)
        
        return True
    
    def unregister_plugin_command(self, plugin: CommandPlugin):
        """플러그인 명령어 등록 해제"""
        command_name = plugin.get_name()
        
        if command_name in self.plugin_commands:
            handler = self.plugin_commands[command_name]
            del self.plugin_commands[command_name]
            
            self.logger.info(f"플러그인 명령어 등록 해제: {command_name}")
            
            # 이벤트 콜백 호출
            if self._on_command_unregistered:
                self._on_command_unregistered(command_name, handler)
            
            return True
        
        return False
    
    def find_command(self, message: str) -> Optional[tuple[CommandHandler, Dict[str, Any]]]:
        """메시지에 해당하는 명령어 찾기"""
        for command_name, handler in self.plugin_commands.items():
            if not handler.enabled:
                continue
            
            for pattern in handler.patterns:
                match = self._match_pattern(pattern, message)
                if match:
                    return handler, match
        
        return None
    
    def _match_pattern(self, pattern: str, message: str) -> Optional[Dict[str, Any]]:
        """패턴 매칭"""
        try:
            # 정규식 패턴으로 변환
            regex_pattern = self._convert_to_regex(pattern)
            match = re.match(regex_pattern, message, re.IGNORECASE)
            
            if match:
                return {
                    'command': pattern,
                    'args': match.groups(),
                    'full_match': match.group(0)
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"패턴 매칭 오류: {pattern} - {e}")
            return None
    
    def _convert_to_regex(self, pattern: str) -> str:
        """패턴을 정규식으로 변환"""
        # 간단한 패턴 변환 (예: "hello {name}" -> r"hello\s+(\w+)")
        regex_pattern = pattern
        
        # {변수명} 형태를 캡처 그룹으로 변환
        regex_pattern = re.sub(r'\{(\w+)\}', r'(\S+)', regex_pattern)
        
        # 공백을 \s+로 변환
        regex_pattern = re.sub(r'\s+', r'\\s+', regex_pattern)
        
        # 시작과 끝 앵커 추가
        regex_pattern = f"^{regex_pattern}$"
        
        self.logger.debug(f"패턴 변환: '{pattern}' -> '{regex_pattern}'")
        return regex_pattern
    
    def execute_command(self, message: str, user_name: str, user_id: str, 
                       timestamp: float = None) -> Optional[BaseResult]:
        """명령어 실행"""
        if timestamp is None:
            import time
            timestamp = time.time()
        
        # 명령어 찾기
        result = self.find_command(message)
        if not result:
            return None
        
        handler, match_info = result
        
        # 컨텍스트 생성
        context = CommandContext(
            user_name=user_name,
            user_id=user_id,
            message=message,
            command=match_info['command'],
            args=match_info['args'],
            raw_message=message,
            timestamp=timestamp,
            additional_data=match_info
        )
        
        # 실행 권한 확인
        if not handler.plugin.can_execute(context):
            self.logger.warning(f"명령어 실행 권한 없음: {user_name} -> {handler.plugin.get_name()}")
            return None
        
        # 명령어 실행
        try:
            result = handler.plugin.execute(context)
            if result:
                self.logger.info(f"플러그인 명령어 실행 성공: {user_name} -> {handler.plugin.get_name()}")
            return result
            
        except Exception as e:
            self.logger.error(f"플러그인 명령어 실행 실패: {handler.plugin.get_name()} - {e}")
            return None
    
    def get_all_commands(self) -> Dict[str, CommandHandler]:
        """모든 플러그인 명령어 반환"""
        return self.plugin_commands.copy()
    
    def get_enabled_commands(self) -> Dict[str, CommandHandler]:
        """활성화된 플러그인 명령어 반환"""
        return {name: handler for name, handler in self.plugin_commands.items() 
                if handler.enabled}
    
    def get_command_info(self, command_name: str) -> Optional[Dict[str, Any]]:
        """명령어 정보 반환"""
        if command_name in self.plugin_commands:
            handler = self.plugin_commands[command_name]
            return {
                'name': command_name,
                'patterns': handler.patterns,
                'help_text': handler.help_text,
                'permissions': handler.permissions,
                'enabled': handler.enabled,
                'plugin_name': handler.plugin.get_name(),
                'plugin_version': handler.plugin.get_version()
            }
        return None
    
    def get_all_command_info(self) -> Dict[str, Dict[str, Any]]:
        """모든 명령어 정보 반환"""
        return {name: self.get_command_info(name) 
                for name in self.plugin_commands.keys()}
    
    def update_command_status(self, command_name: str, enabled: bool):
        """명령어 상태 업데이트"""
        if command_name in self.plugin_commands:
            self.plugin_commands[command_name].enabled = enabled
            self.logger.info(f"명령어 상태 업데이트: {command_name} -> {'활성화' if enabled else '비활성화'}")


# 전역 명령어 레지스트리 인스턴스
command_registry = CommandRegistry() 