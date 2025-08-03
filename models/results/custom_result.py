"""
Custom result class
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from ..base.base_result import BaseResult
from ..base.registry import AutoRegister
from ..enums.command_type import CommandType


@AutoRegister(CommandType.CUSTOM)
@dataclass
class CustomResult(BaseResult):
    """커스텀 명령어 결과"""
    
    command: str                            # 명령어
    original_phrase: str                    # 원본 문구
    processed_phrase: str                   # 처리된 문구 (다이스 치환 후)
    dice_results: List = field(default_factory=list)  # 포함된 다이스 결과들
    
    def get_result_text(self) -> str:
        """결과 텍스트 반환"""
        return self.processed_phrase
    
    def has_dice(self) -> bool:
        """다이스가 포함되어 있는지 확인"""
        return len(self.dice_results) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'command': self.command,
            'original_phrase': self.original_phrase,
            'processed_phrase': self.processed_phrase,
            'dice_results': [dice.to_dict() for dice in self.dice_results],
            'has_dice': self.has_dice()
        }
    
    def validate(self) -> bool:
        """유효성 검사"""
        return bool(self.command and self.processed_phrase) 