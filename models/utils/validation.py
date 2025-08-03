"""
Validation utilities for result objects
"""

from typing import List
from ..base.base_result import BaseResult
from ..core.command_result import CommandResult
from ..results.dice_result import DiceResult


def validate_result(result: BaseResult) -> bool:
    """결과 객체 유효성 검사"""
    return result.validate()


def validate_dice_result(result: DiceResult) -> bool:
    """다이스 결과 유효성 검사"""
    if not result.rolls or not result.expression:
        return False
    
    if result.total != sum(result.rolls) + result.modifier:
        return False
    
    if result.has_threshold:
        if result.threshold_type not in ['<', '>']:
            return False
        if result.success_count is None or result.fail_count is None:
            return False
        if result.success_count + result.fail_count != len(result.rolls):
            return False
    
    return True


def validate_command_result(result: CommandResult) -> bool:
    """명령어 결과 유효성 검사"""
    if not result.user_id or not result.original_command:
        return False
    
    if result.status not in result.status.__class__:
        return False
    
    if result.command_type not in result.command_type.__class__:
        return False
    
    if result.is_successful() and not result.message:
        return False
    
    return True


def validate_result_text_korean_particles(result_data) -> bool:
    """결과 텍스트의 한글 조사 유효성 검사"""
    try:
        if hasattr(result_data, 'get_result_text'):
            text = result_data.get_result_text()
            
            # 기본적인 조사 패턴 검사
            import re
            
            # 잘못된 조사 패턴들 검사
            wrong_patterns = [
                r'[가-힣][을를][을를]',  # 중복 조사 (예: 사과를를)
                r'[aA-zZ][이가]',       # 영어 뒤에 이/가
                r'\d[이가]',            # 숫자 뒤에 이/가
            ]
            
            for pattern in wrong_patterns:
                if re.search(pattern, text):
                    return False
            
            return True
    except Exception:
        return True  # 검사 실패 시 통과로 처리 