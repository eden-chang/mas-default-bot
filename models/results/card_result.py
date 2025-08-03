"""
Card result class
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from ..base.base_result import BaseResult
from ..base.registry import AutoRegister
from ..enums.command_type import CommandType


@AutoRegister(CommandType.CARD)
@dataclass
class CardResult(BaseResult):
    """카드 뽑기 결과"""
    
    cards: List[str]                        # 뽑힌 카드들
    count: int                              # 요청한 카드 개수
    
    def get_result_text(self) -> str:
        """결과 텍스트 반환"""
        return ", ".join(self.cards)
    
    def get_suits_summary(self) -> Dict[str, int]:
        """무늬별 개수 요약"""
        suits = {'♠': 0, '♥': 0, '♦': 0, '♣': 0}
        for card in self.cards:
            if card and len(card) > 0:
                suit = card[0]
                if suit in suits:
                    suits[suit] += 1
        return suits
    
    def get_ranks_summary(self) -> Dict[str, int]:
        """숫자별 개수 요약"""
        ranks = {}
        for card in self.cards:
            if card and len(card) > 1:
                rank = card[1:]
                ranks[rank] = ranks.get(rank, 0) + 1
        return ranks
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'cards': self.cards,
            'count': self.count,
            'suits_summary': self.get_suits_summary(),
            'ranks_summary': self.get_ranks_summary()
        }
    
    def validate(self) -> bool:
        """유효성 검사"""
        return bool(self.cards and len(self.cards) == self.count) 