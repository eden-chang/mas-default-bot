"""
Base result class for all result types
"""

from dataclasses import dataclass
from abc import ABC
from typing import Dict, Any


@dataclass
class BaseResult(ABC):
    """모든 결과 클래스의 기본 클래스"""
    
    def get_result_text(self) -> str:
        """결과 텍스트 반환 (기본 구현)"""
        return str(self)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (기본 구현)"""
        return {
            'type': self.__class__.__name__,
            'data': self.__dict__
        }
    
    def validate(self) -> bool:
        """유효성 검사 (기본 구현)"""
        return True
    
    def get_summary(self) -> Dict[str, Any]:
        """요약 정보 반환"""
        return {
            'type': self.__class__.__name__,
            'text': self.get_result_text(),
            'valid': self.validate()
        } 