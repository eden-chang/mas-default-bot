"""
Fortune result class
"""

from dataclasses import dataclass
from typing import Dict, Any
from ..base.base_result import BaseResult
from ..base.registry import AutoRegister
from ..enums.command_type import CommandType


@AutoRegister(CommandType.FORTUNE)
@dataclass
class FortuneResult(BaseResult):
    """운세 결과 (조사 처리 적용)"""
    
    fortune_text: str                       # 운세 문구
    user_name: str                          # 사용자 이름
    
    def get_result_text(self) -> str:
        """결과 텍스트 반환 (올바른 조사 적용)"""
        try:
            from ..utils.korean_particles import detect_korean_particle
            user_particle = detect_korean_particle(self.user_name, 'topic')
            return f"{self.user_name}{user_particle} 오늘의 운세:\n{self.fortune_text}"
        except Exception:
            # 폴백: 기존 방식
            return f"{self.user_name}의 오늘의 운세:\n{self.fortune_text}"
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'fortune_text': self.fortune_text,
            'user_name': self.user_name
        }
    
    def validate(self) -> bool:
        """유효성 검사"""
        return bool(self.fortune_text and self.user_name) 