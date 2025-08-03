"""
다이스 명령어 구현 - 최적화된 버전
주사위 굴리기 기능을 제공하는 명령어 클래스입니다.
새로운 BaseCommand 구조와 최적화된 에러 핸들링을 적용합니다.
"""

import os
import sys
import random
import re
from typing import List, Tuple, Any, Optional, Dict

# 경로 설정 (VM 환경 대응)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

try:
    from config.settings import config
    from utils.logging_config import logger, bot_logger
    from utils.error_handling.exceptions import DiceError
    from utils.error_handling.handler import ErrorHandler, get_error_handler
    from commands.base_command import BaseCommand
    from models.user import User
    from models.command_result import CommandType, CommandStatus, DiceResult, create_dice_result
except ImportError as e:
    # VM 환경에서 임포트 실패 시 폴백
    import logging
    logger = logging.getLogger('dice_command')
    
    # 기본 클래스들 정의
    class DiceError(Exception):
        pass
    
    class BaseCommand:
        pass
    
    class User:
        def __init__(self, id: str, name: str = ""):
            self.id = id
            self.name = name
        
        def get_display_name(self):
            return self.name or self.id
    
    class CommandType:
        DICE = "dice"
    
    class CommandStatus:
        SUCCESS = "success"
        ERROR = "error"
    
    class DiceResult:
        def __init__(self, expression: str, rolls: list, total: int, **kwargs):
            self.expression = expression
            self.rolls = rolls
            self.total = total
            for key, value in kwargs.items():
                setattr(self, key, value)


class DiceCommand(BaseCommand):
    """
    최적화된 다이스 굴리기 명령어 클래스
    
    지원하는 형식:
    - [다이스/1d100] : 100면체 주사위 1개
    - [다이스/2d6] : 6면체 주사위 2개
    - [다이스/3d6<4] : 6면체 주사위 3개, 4 이하면 성공
    - [다이스/1d20>15] : 20면체 주사위 1개, 15 이상이면 성공
    - [1d6] : 직접 다이스 표현식 (다이스 키워드 없이)
    """
    
    def _get_command_type(self) -> CommandType:
        """명령어 타입 반환"""
        return CommandType.DICE
    
    def _get_command_name(self) -> str:
        """명령어 이름 반환"""
        return "다이스"
    
    def _execute_command(self, user: User, keywords: List[str]) -> Tuple[str, DiceResult]:
        """
        다이스 명령어 실행
        
        Args:
            user: 사용자 객체
            keywords: 키워드 리스트 ([다이스, 2d6] 또는 [2d6])
            
        Returns:
            Tuple[str, DiceResult]: (결과 메시지, 다이스 결과 객체)
            
        Raises:
            DiceError: 다이스 표현식 오류 또는 제한 초과
        """
        # 키워드에서 다이스 표현식 추출
        dice_expression = self._extract_dice_expression(keywords)
        
        # 다이스 표현식 파싱
        dice_config = self._parse_dice_expression(dice_expression)
        
        # 제한 검증
        self._validate_dice_limits(dice_config)
        
        # 주사위 굴리기
        rolls = self._roll_dice(dice_config['num_dice'], dice_config['dice_sides'])
        
        # 결과 계산
        dice_result = self._calculate_result(dice_expression, rolls, dice_config)
        
        # 결과 메시지 생성
        message = self._format_result_message(dice_result)
        
        return message, dice_result
    
    def _extract_dice_expression(self, keywords: List[str]) -> str:
        """
        키워드에서 다이스 표현식 추출
        
        Args:
            keywords: 키워드 리스트
            
        Returns:
            str: 다이스 표현식
            
        Raises:
            DiceError: 표현식이 없거나 잘못된 경우
        """
        if not keywords:
            raise DiceError("주사위와 개수를 지정해 주세요.")
        
        # 첫 번째 키워드가 '다이스'인 경우
        if len(keywords) >= 2 and keywords[0].lower() == '다이스':
            return keywords[1].replace(" ", "")
        
        # 첫 번째 키워드가 다이스 표현식인 경우 (예: [2d6])
        elif len(keywords) >= 1:
            potential_expr = keywords[0].replace(" ", "")
            if self._is_dice_expression(potential_expr):
                return potential_expr
        
        # 다이스 키워드만 있고 표현식이 없는 경우
        if len(keywords) == 1 and keywords[0].lower() == '다이스':
            raise DiceError(
                "주사위와 개수를 지정해 주세요.\n"
                "예시:\n"
                "[다이스/1d100] - 100면체 주사위 1개\n"
                "[다이스/2d6] - 6면체 주사위 2개\n"
                "[다이스/3d6<4] - 6면체 주사위 3개, 4 이하면 성공"
            )
        
        # 표현식이 잘못된 경우
        raise DiceError(f"'{keywords[0] if keywords else ''}'은(는) 올바른 다이스 표현식이 아닙니다.")
    
    def _is_dice_expression(self, expression: str) -> bool:
        """
        문자열이 다이스 표현식인지 확인
        
        Args:
            expression: 확인할 문자열
            
        Returns:
            bool: 다이스 표현식 여부
        """
        # 기본 다이스 패턴: 숫자d숫자[</>숫자]
        dice_pattern = re.compile(r'^\d+[dD]\d+([<>]\d+)?$')
        return bool(dice_pattern.match(expression))
    
    def _parse_dice_expression(self, dice_expression: str) -> Dict[str, Any]:
        """
        다이스 표현식 파싱
        
        Args:
            dice_expression: 다이스 표현식 (예: "2d6", "3d6<4")
            
        Returns:
            Dict: 파싱된 다이스 설정
            
        Raises:
            DiceError: 파싱 실패
        """
        if not dice_expression:
            raise DiceError("주사위와 개수를 지정해 주세요.")
        
        # 성공/실패 조건 파싱
        threshold = None
        threshold_type = None
        
        if '<' in dice_expression:
            dice_part, threshold_str = dice_expression.split('<')
            threshold = int(threshold_str)
            threshold_type = '<'
        elif '>' in dice_expression:
            dice_part, threshold_str = dice_expression.split('>')
            threshold = int(threshold_str)
            threshold_type = '>'
        else:
            dice_part = dice_expression
        
        # 기본 다이스 표현식 파싱 (예: 2d6)
        match = re.match(r'(\d+)[dD](\d+)', dice_part.lower())
        if not match:
            raise DiceError(f"'{dice_expression}'은(는) 올바른 다이스 표현식이 아닙니다.")
        
        try:
            num_dice = int(match.group(1))
            dice_sides = int(match.group(2))
        except ValueError:
            raise DiceError(f"'{dice_expression}'은(는) 올바른 다이스 표현식이 아닙니다.")
        
        return {
            'num_dice': num_dice,
            'dice_sides': dice_sides,
            'threshold': threshold,
            'threshold_type': threshold_type,
            'original_expression': dice_expression
        }
    
    def _validate_dice_limits(self, dice_config: Dict[str, Any]) -> None:
        """
        다이스 제한 검증
        
        Args:
            dice_config: 다이스 설정
            
        Raises:
            DiceError: 제한 초과
        """
        num_dice = dice_config['num_dice']
        dice_sides = dice_config['dice_sides']
        
        # 주사위 개수 제한
        if num_dice < 1:
            raise DiceError("주사위 개수는 1개 이상이어야 합니다.")
        
        if num_dice > config.MAX_DICE_COUNT:
            raise DiceError(f"주사위 개수는 최대 {config.MAX_DICE_COUNT}개까지만 가능합니다.")
        
        # 주사위 면수 제한
        if dice_sides < 2:
            raise DiceError("주사위 면수는 2면 이상이어야 합니다.")
        
        if dice_sides > config.MAX_DICE_SIDES:
            raise DiceError(f"주사위 면수는 최대 {config.MAX_DICE_SIDES}면까지만 가능합니다.")
        
        # 임계값 검증
        threshold = dice_config.get('threshold')
        if threshold is not None:
            if threshold < 1 or threshold > dice_sides:
                raise DiceError(f"임계값은 1과 {dice_sides} 사이여야 합니다.")
    
    def _roll_dice(self, num_dice: int, dice_sides: int) -> List[int]:
        """
        주사위 굴리기
        
        Args:
            num_dice: 주사위 개수
            dice_sides: 주사위 면수
            
        Returns:
            List[int]: 각 주사위 결과
        """
        rolls = []
        for _ in range(num_dice):
            roll = random.randint(1, dice_sides)
            rolls.append(roll)
        
        logger.debug(f"주사위 굴리기: {num_dice}d{dice_sides} = {rolls}")
        return rolls
    
    def _calculate_result(self, expression: str, rolls: List[int], dice_config: Dict[str, Any]) -> DiceResult:
        """
        다이스 결과 계산
        
        Args:
            expression: 원본 다이스 표현식
            rolls: 주사위 결과들
            dice_config: 다이스 설정
            
        Returns:
            DiceResult: 계산된 결과
        """
        threshold = dice_config.get('threshold')
        threshold_type = dice_config.get('threshold_type')
        
        # 성공/실패 개수 계산
        success_count = None
        fail_count = None
        
        if threshold is not None and threshold_type:
            success_count = 0
            for roll in rolls:
                if threshold_type == '<' and roll <= threshold:
                    success_count += 1
                elif threshold_type == '>' and roll >= threshold:
                    success_count += 1
            
            fail_count = len(rolls) - success_count
        
        # DiceResult 객체 생성
        return create_dice_result(
            expression=expression,
            rolls=rolls,
            modifier=0,  # 현재 버전에서는 보정값 미지원
            threshold=threshold,
            threshold_type=threshold_type
        )
    
    def _format_result_message(self, dice_result: DiceResult) -> str:
        """
        결과 메시지 포맷팅
        
        Args:
            dice_result: 다이스 결과
            
        Returns:
            str: 포맷된 결과 메시지
        """
        if len(dice_result.rolls) == 1:
            # 단일 주사위
            if dice_result.has_threshold:
                # 성공/실패 조건이 있는 경우
                success = dice_result.is_success
                if success is not None:
                    return f"{dice_result.rolls[0]}"
                else:
                    return f"{dice_result.rolls[0]}"
            else:
                # 일반 단일 주사위
                return f"{dice_result.rolls[0]}"
        else:
            # 복수 주사위
            rolls_str = ", ".join(str(roll) for roll in dice_result.rolls)
            
            if dice_result.has_threshold:
                # 성공/실패 조건이 있는 경우
                return f"{rolls_str}\n성공 주사위: {dice_result.success_count}개\n실패 주사위: {dice_result.fail_count}개입니다."
            else:
                # 일반 복수 주사위
                return f"{rolls_str}\n합계: {dice_result.total}"
    
    def get_help_text(self) -> str:
        """도움말 텍스트 반환"""
        return (
            "[다이스/NdM] - M면체 주사위를 N개 굴립니다.\n"
            "[다이스/NdM<k] - M면체 주사위를 N개 굴리고, k 이하의 숫자가 나오면 성공합니다.\n"
            "[다이스/NdM>k] - M면체 주사위를 N개 굴리고, k 이상의 숫자가 나오면 성공합니다."
        )
    
    def get_extended_help(self) -> str:
        """확장 도움말 반환"""
        return (
            f"{self.get_help_text()}\n\n"
            f"📋 사용 예시:\n"
            f"[다이스/1d100] - 100면체 주사위 1개\n"
            f"[다이스/2d6] - 6면체 주사위 2개\n"
            f"[다이스/3d6<4] - 6면체 주사위 3개, 4 이하면 성공\n"
            f"[다이스/1d20>15] - 20면체 주사위 1개, 15 이상이면 성공\n"
            f"[2d6] - 다이스 키워드 없이 직접 사용 가능\n\n"
            f"⚙️ 제한사항:\n"
            f"• 최대 주사위 개수: {config.MAX_DICE_COUNT}개\n"
            f"• 최대 주사위 면수: {config.MAX_DICE_SIDES}면\n"
            f"• 최소 주사위 면수: 2면"
        )
    
    def validate_dice_expression_format(self, expression: str) -> Tuple[bool, Optional[str]]:
        """
        다이스 표현식 형식 검증 (미리 검증용)
        
        Args:
            expression: 검증할 표현식
            
        Returns:
            Tuple[bool, Optional[str]]: (유효성, 오류 메시지)
        """
        try:
            dice_config = self._parse_dice_expression(expression)
            self._validate_dice_limits(dice_config)
            return True, None
        except DiceError as e:
            return False, str(e)
        except Exception as e:
            return False, f"표현식 검증 오류: {str(e)}"
    
    def get_random_example(self) -> str:
        """랜덤한 다이스 예시 반환"""
        examples = [
            "1d100",
            "2d6", 
            "3d6",
            "1d20",
            "4d6",
            "1d12",
            "2d10",
            "3d6<4",
            "1d20>10",
            "2d6>7"
        ]
        return random.choice(examples)
    
    def simulate_dice_roll(self, expression: str, iterations: int = 1000) -> Dict[str, Any]:
        """
        다이스 굴리기 시뮬레이션 (통계용)
        
        Args:
            expression: 다이스 표현식
            iterations: 시뮬레이션 횟수
            
        Returns:
            Dict: 시뮬레이션 결과 통계
        """
        if iterations > 10000:  # 과도한 시뮬레이션 방지
            iterations = 10000
        
        try:
            dice_config = self._parse_dice_expression(expression)
            self._validate_dice_limits(dice_config)
            
            results = []
            success_counts = []
            
            for _ in range(iterations):
                rolls = self._roll_dice(dice_config['num_dice'], dice_config['dice_sides'])
                dice_result = self._calculate_result(expression, rolls, dice_config)
                
                results.append(dice_result.total)
                if dice_result.has_threshold and dice_result.success_count is not None:
                    success_counts.append(dice_result.success_count)
            
            stats = {
                'expression': expression,
                'iterations': iterations,
                'min_result': min(results),
                'max_result': max(results),
                'average': sum(results) / len(results),
                'most_common': max(set(results), key=results.count)
            }
            
            if success_counts:
                stats['average_successes'] = sum(success_counts) / len(success_counts)
                stats['success_rate'] = (sum(1 for s in success_counts if s > 0) / len(success_counts)) * 100
            
            return stats
            
        except Exception as e:
            return {'error': str(e)}


# 다이스 표현식 직접 검증 함수들 (유틸리티)
def is_dice_command(keyword: str) -> bool:
    """
    키워드가 다이스 명령어인지 확인
    
    Args:
        keyword: 확인할 키워드
        
    Returns:
        bool: 다이스 명령어 여부
    """
    if not keyword:
        return False
    
    keyword = keyword.lower().strip()
    
    # '다이스' 키워드
    if keyword == '다이스':
        return True
    
    # 직접 다이스 표현식 (예: "2d6", "1d100<50")
    dice_pattern = re.compile(r'^\d+[dD]\d+([<>]\d+)?$')
    return bool(dice_pattern.match(keyword))


def extract_dice_from_text(text: str) -> List[str]:
    """
    텍스트에서 다이스 표현식들 추출
    
    Args:
        text: 분석할 텍스트
        
    Returns:
        List[str]: 발견된 다이스 표현식들
    """
    dice_pattern = re.compile(r'\b\d+[dD]\d+([<>]\d+)?\b')
    return dice_pattern.findall(text)


def validate_dice_expression(expression: str) -> Tuple[bool, str]:
    """
    다이스 표현식 유효성 검사 (독립 함수)
    
    Args:
        expression: 검증할 표현식
        
    Returns:
        Tuple[bool, str]: (유효성, 메시지)
    """
    try:
        dice_command = DiceCommand()
        return dice_command.validate_dice_expression_format(expression)
    except Exception as e:
        return False, f"검증 오류: {str(e)}"


# 다이스 명령어 인스턴스 생성 함수
def create_dice_command(sheets_manager=None) -> DiceCommand:
    """
    다이스 명령어 인스턴스 생성
    
    Args:
        sheets_manager: Google Sheets 관리자
        
    Returns:
        DiceCommand: 다이스 명령어 인스턴스
    """
    return DiceCommand(sheets_manager)