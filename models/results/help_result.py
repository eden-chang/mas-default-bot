"""
Help result class
"""

from dataclasses import dataclass
from typing import Dict, Any
from ..base.base_result import BaseResult
from ..base.registry import AutoRegister
from ..enums.command_type import CommandType


@AutoRegister(CommandType.HELP)
@dataclass
class HelpResult(BaseResult):
    """도움말 결과"""
    
    help_text: str                          # 도움말 텍스트
    command_count: int                      # 총 명령어 개수
    
    def get_result_text(self) -> str:
        """결과 텍스트 반환"""
        return self.help_text
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'help_text': self.help_text,
            'command_count': self.command_count
        }
    
    def validate(self) -> bool:
        """유효성 검사"""
        return bool(self.help_text and self.command_count >= 0) 