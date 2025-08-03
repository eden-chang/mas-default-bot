"""
Dice result class
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from ..base.base_result import BaseResult
from ..base.registry import AutoRegister
from ..enums.command_type import CommandType


@AutoRegister(CommandType.DICE)
@dataclass
class DiceResult(BaseResult):
    """다이스 굴리기 결과"""
    
    expression: str                          # 다이스 표현식 (예: "2d6", "1d20+5")
    rolls: List[int]                        # 각 주사위 결과
    total: int                              # 총합
    modifier: int = 0                       # 보정값
    threshold: Optional[int] = None         # 성공/실패 임계값
    threshold_type: Optional[str] = None    # 임계값 타입 ('<' 또는 '>')
    success_count: Optional[int] = None     # 성공한 주사위 개수
    fail_count: Optional[int] = None        # 실패한 주사위 개수
    
    @property
    def base_total(self) -> int:
        """보정값 제외한 주사위 합계"""
        return sum(self.rolls)
    
    @property
    def has_threshold(self) -> bool:
        """성공/실패 조건 여부"""
        return self.threshold is not None and self.threshold_type is not None
    
    @property
    def is_success(self) -> Optional[bool]:
        """성공 여부 (단일 주사위 + 임계값인 경우)"""
        if not self.has_threshold or len(self.rolls) != 1:
            return None
        
        roll_value = self.rolls[0]
        if self.threshold_type == '<':
            return roll_value <= self.threshold
        elif self.threshold_type == '>':
            return roll_value >= self.threshold
        return None
    
    def get_detailed_result(self) -> str:
        """상세한 결과 문자열 반환"""
        if len(self.rolls) == 1:
            # 단일 주사위
            if self.has_threshold:
                success = self.is_success
                if success is not None:
                    result_text = "성공" if success else "실패"
                    return f"{self.rolls[0]} ({result_text})"
            return str(self.total)
        else:
            # 복수 주사위
            rolls_str = ", ".join(str(roll) for roll in self.rolls)
            if self.has_threshold:
                return f"{rolls_str}\n성공: {self.success_count}개, 실패: {self.fail_count}개"
            else:
                return f"{rolls_str}\n합계: {self.total}"
    
    def get_simple_result(self) -> str:
        """간단한 결과 문자열 반환"""
        if len(self.rolls) == 1:
            return str(self.rolls[0])
        return f"합계: {self.total}"
    
    def get_result_text(self) -> str:
        """결과 텍스트 반환"""
        return self.get_detailed_result()
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'expression': self.expression,
            'rolls': self.rolls,
            'total': self.total,
            'modifier': self.modifier,
            'threshold': self.threshold,
            'threshold_type': self.threshold_type,
            'success_count': self.success_count,
            'fail_count': self.fail_count,
            'base_total': self.base_total,
            'has_threshold': self.has_threshold,
            'is_success': self.is_success
        }
    
    def validate(self) -> bool:
        """유효성 검사"""
        if not self.rolls or not self.expression:
            return False
        
        if self.total != sum(self.rolls) + self.modifier:
            return False
        
        if self.has_threshold:
            if self.threshold_type not in ['<', '>']:
                return False
            if self.success_count is None or self.fail_count is None:
                return False
            if self.success_count + self.fail_count != len(self.rolls):
                return False
        
        return True 