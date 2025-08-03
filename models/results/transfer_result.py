"""
Transfer result class
"""

from dataclasses import dataclass
from typing import Dict, Any
from ..base.base_result import BaseResult
from ..base.registry import AutoRegister
from ..enums.command_type import CommandType


@AutoRegister(CommandType.TRANSFER)
@dataclass
class TransferResult(BaseResult):
    """양도 결과 (조사 처리 자동화)"""
    success: bool
    message: str
    giver_name: str
    giver_id: str
    receiver_name: str 
    receiver_id: str
    item_name: str
    dm_sent: bool = False
    dm_message: str = ""
    
    def get_result_text(self) -> str:
        """결과 텍스트 반환 (자동 조사 처리)"""
        try:
            from ..utils.korean_particles import detect_korean_particle
            item_particle = detect_korean_particle(self.item_name, 'object')
            return f"{self.receiver_name}에게 {self.item_name}{item_particle} 양도했습니다."
        except Exception:
            # 폴백: 기본 조사
            return f"{self.receiver_name}에게 {self.item_name}을 양도했습니다."
    
    def get_dm_message(self) -> str:
        """DM용 메시지 생성 (자동 조사 처리)"""
        try:
            from ..utils.korean_particles import detect_korean_particle
            giver_particle = detect_korean_particle(self.giver_name, 'subject')
            item_particle = detect_korean_particle(self.item_name, 'object')
            
            return f"{self.giver_name}{giver_particle} 당신에게 {self.item_name}{item_particle} 양도했습니다."
        except Exception:
            # 폴백: 기본 조사
            return f"{self.giver_name}이 당신에게 {self.item_name}을 양도했습니다."
    
    def get_detailed_result_text(self) -> str:
        """상세한 양도 결과 텍스트"""
        try:
            from ..utils.korean_particles import detect_korean_particle
            giver_particle = detect_korean_particle(self.giver_name, 'subject')
            receiver_particle = detect_korean_particle(self.receiver_name, 'topic')
            item_particle = detect_korean_particle(self.item_name, 'object')
            
            return (f"양도 완료!\n"
                   f"양도자: {self.giver_name}{giver_particle}\n"
                   f"수령자: {self.receiver_name}{receiver_particle}\n"
                   f"아이템: {self.item_name}{item_particle}")
        except Exception:
            # 폴백
            return (f"양도 완료!\n"
                   f"양도자: {self.giver_name}이\n"
                   f"수령자: {self.receiver_name}은\n"
                   f"아이템: {self.item_name}을")
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'success': self.success,
            'message': self.message,
            'giver_name': self.giver_name,
            'giver_id': self.giver_id,
            'receiver_name': self.receiver_name,
            'receiver_id': self.receiver_id,
            'item_name': self.item_name,
            'dm_sent': self.dm_sent,
            'dm_message': self.dm_message
        }
    
    def validate(self) -> bool:
        """유효성 검사"""
        return bool(
            self.giver_name and self.giver_id and 
            self.receiver_name and self.receiver_id and 
            self.item_name and self.message
        ) 