"""
Result protocol definition
"""

from typing import Protocol, Dict, Any


class ResultProtocol(Protocol):
    """결과 객체 프로토콜"""
    def get_result_text(self) -> str:
        """결과 텍스트 반환"""
        ...
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        ...
    
    def validate(self) -> bool:
        """유효성 검사"""
        ... 