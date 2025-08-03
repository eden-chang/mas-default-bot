"""
커스텀 명령어 구현 - 최적화된 버전
사용자 정의 명령어와 다이스 치환 기능을 제공하는 명령어 클래스입니다.
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
    from utils.error_handling.exceptions import CustomCommandError
    from utils.error_handling.handler import ErrorHandler, get_error_handler
    from utils.cache_manager import bot_cache
    from commands.base_command import BaseCommand
    from models.user import User
    from models.command_result import CommandType, CommandStatus, CustomResult, create_custom_result
    from models.results.dice_result import DiceResult
except ImportError:
    # VM 환경에서 임포트 실패 시 폴백
    import logging
    logger = logging.getLogger('custom_command')
    
    # 기본 클래스들 정의
    class CustomCommandError(Exception):
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
        CUSTOM = "custom"
    
    class CommandStatus:
        SUCCESS = "success"
        ERROR = "error"
    
    class CustomResult:
        def __init__(self, command: str, original_phrase: str, processed_phrase: str, **kwargs):
            self.command = command
            self.original_phrase = original_phrase
            self.processed_phrase = processed_phrase
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    class DiceResult:
        def __init__(self, expression: str, rolls: list, total: int, **kwargs):
            self.expression = expression
            self.rolls = rolls
            self.total = total
            for key, value in kwargs.items():
                setattr(self, key, value)


class CustomCommand(BaseCommand):
    """
    최적화된 커스텀 명령어 클래스
    
    Google Sheets의 '커스텀' 시트에서 명령어와 문구를 조회하여
    사용자 정의 명령어를 처리합니다.
    
    지원하는 다이스 표현식:
    - {1d100} : 100면체 주사위 1개
    - {2d6} : 6면체 주사위 2개
    - {3d6+5} : 6면체 주사위 3개 + 5 보정값
    - {1d20<15} : 20면체 주사위 1개, 15 이하면 성공/실패
    """
    
    def __init__(self, sheets_manager=None):
        """CustomCommand 초기화"""
        self._command_name = "커스텀"
        super().__init__(sheets_manager)
    
    def _get_command_type(self) -> CommandType:
        """명령어 타입 반환"""
        return CommandType.CUSTOM
    
    def _get_command_name(self) -> str:
        """명령어 이름 반환"""
        return self._command_name
    
    def set_command_name(self, command_name: str) -> None:
        """명령어 이름 설정 (실행 시 동적 변경)"""
        self._command_name = command_name
    
    def execute_custom_command(self, user_id: str, command_keyword: str) -> Any:
        """
        특정 커스텀 명령어 실행
        
        Args:
            user_id: 사용자 ID
            command_keyword: 커스텀 명령어 키워드
            
        Returns:
            CommandResult: 실행 결과
        """
        # 명령어 이름 설정
        self.set_command_name(command_keyword)
        
        # 기본 execute 메서드 호출
        return self.execute(user_id, [command_keyword])
    
    def _execute_command(self, user: User, keywords: List[str]) -> Tuple[str, CustomResult]:
        """
        커스텀 명령어 실행
        
        Args:
            user: 사용자 객체
            keywords: 키워드 리스트 (첫 번째가 커스텀 명령어)
            
        Returns:
            Tuple[str, CustomResult]: (결과 메시지, 커스텀 결과 객체)
            
        Raises:
            CommandError: 명령어를 찾을 수 없거나 처리 실패
        """
        if not keywords:
            raise CustomCommandError("명령어가 지정되지 않았습니다.")
        
        command_keyword = keywords[0].strip()
        
        # 커스텀 명령어 데이터 로드
        custom_commands = self._load_custom_commands()
        
        # 해당 명령어의 문구들 조회
        phrases = custom_commands.get(command_keyword)
        if not phrases:
            raise CustomCommandError(
                f"[{command_keyword}] 명령어를 찾을 수 없습니다.\n"
                "사용 가능한 명령어는 도움말을 참고해 주세요."
            )
        
        # 랜덤하게 문구 선택
        selected_phrase = random.choice(phrases)
        
        # 다이스 표현식 처리
        processed_phrase, dice_results = self._process_dice_in_phrase(selected_phrase)
        
        # 결과 객체 생성
        custom_result = create_custom_result(
            command=command_keyword,
            original_phrase=selected_phrase,
            processed_phrase=processed_phrase,
            dice_results=dice_results
        )
        
        return processed_phrase, custom_result
    
    def _load_custom_commands(self) -> Dict[str, List[str]]:
        """
        커스텀 명령어 데이터 로드 (캐시 우선, 시트 후순위)
        
        Returns:
            Dict[str, List[str]]: {명령어: [문구들]} 형태의 딕셔너리
        """
        # 캐시에서 먼저 조회
        cached_commands = bot_cache.get_custom_commands()
        if cached_commands:
            logger.debug("캐시에서 커스텀 명령어 로드")
            return cached_commands
        
        # 시트에서 로드
        try:
            if self.sheets_manager:
                commands = self.sheets_manager.get_custom_commands()
                if commands:
                    # 캐시에 저장 (설정된 TTL 사용)
                    bot_cache.cache_custom_commands(commands)
                    logger.debug(f"시트에서 커스텀 명령어 로드: {len(commands)}개")
                    return commands
        except Exception as e:
            logger.warning(f"시트에서 커스텀 명령어 로드 실패: {e}")
        
        # 빈 딕셔너리 반환
        logger.info("커스텀 명령어 없음")
        return {}
    
    def _process_dice_in_phrase(self, phrase: str) -> Tuple[str, List[DiceResult]]:
        """
        문구에서 다이스 표현식을 찾아서 실제 주사위 결과로 치환
        
        Args:
            phrase: 처리할 문구
            
        Returns:
            Tuple[str, List[DiceResult]]: (처리된 문구, 다이스 결과들)
        """
        if not phrase:
            return phrase, []
        
        # 다이스 표현식 패턴: {숫자d숫자[+/-숫자][</>숫자]}
        dice_pattern = r'\{(\d+[dD]\d+(?:[+\-]\d+)?(?:[<>]\d+)?)\}'
        
        dice_results = []
        processed_phrase = phrase
        
        def replace_dice(match):
            dice_expr = match.group(1)
            try:
                # 다이스 굴리기 실행
                result = self._roll_single_dice(dice_expr)
                dice_results.append(result)
                return str(result.total)  # 최종 결과값으로 치환
            except Exception as e:
                logger.warning(f"다이스 처리 오류: {dice_expr} -> {e}")
                return f"[{dice_expr} 오류]"
        
        # 모든 다이스 표현식을 결과로 치환
        processed_phrase = re.sub(dice_pattern, replace_dice, processed_phrase)
        
        logger.debug(f"다이스 치환 완료: {len(dice_results)}개")
        return processed_phrase, dice_results
    
    def _roll_single_dice(self, dice_expr: str) -> DiceResult:
        """
        단일 다이스 표현식을 처리하여 결과 반환
        
        Args:
            dice_expr: 다이스 표현식 (예: "1d100", "2d6+5", "3d6<4")
            
        Returns:
            DiceResult: 다이스 결과
            
        Raises:
            ValueError: 잘못된 다이스 표현식
        """
        # 표현식 정규화
        dice_expr = dice_expr.strip().replace(' ', '')
        
        # 정규표현식으로 파싱: 숫자d숫자[+/-숫자][</>숫자]
        pattern = r'^(\d+)[dD](\d+)([+\-]\d+)?([<>]\d+)?$'
        match = re.match(pattern, dice_expr)
        
        if not match:
            raise ValueError(f"잘못된 다이스 표현식: {dice_expr}")
        
        # 기본 다이스 정보 추출
        num_dice = int(match.group(1))
        num_sides = int(match.group(2))
        modifier_str = match.group(3)  # +5, -3 등
        condition_str = match.group(4)  # <10, >15 등
        
        # 보정값 처리
        modifier = 0
        if modifier_str:
            if modifier_str.startswith('+'):
                modifier = int(modifier_str[1:])
            elif modifier_str.startswith('-'):
                modifier = -int(modifier_str[1:])
        
        # 성공/실패 조건 처리
        threshold = None
        threshold_type = None
        if condition_str:
            if condition_str.startswith('<'):
                threshold = int(condition_str[1:])
                threshold_type = '<'
            elif condition_str.startswith('>'):
                threshold = int(condition_str[1:])
                threshold_type = '>'
        
        # 유효성 검사
        if num_dice <= 0 or num_dice > config.MAX_DICE_COUNT:
            raise ValueError(f"주사위 개수 오류: {num_dice} (최대 {config.MAX_DICE_COUNT}개)")
        if num_sides <= 0 or num_sides > config.MAX_DICE_SIDES:
            raise ValueError(f"주사위 면수 오류: {num_sides} (최대 {config.MAX_DICE_SIDES}면)")
        
        # 주사위 굴리기
        rolls = []
        for _ in range(num_dice):
            roll = random.randint(1, num_sides)
            rolls.append(roll)
        
        # DiceResult 객체 생성
        return create_dice_result(
            expression=dice_expr,
            rolls=rolls,
            modifier=modifier,
            threshold=threshold,
            threshold_type=threshold_type
        )
    
    def get_help_text(self) -> str:
        """도움말 텍스트 반환"""
        return "Google Sheets에 정의된 사용자 커스텀 명령어를 실행합니다."
    
    def get_extended_help(self) -> str:
        """확장 도움말 반환"""
        return (
            f"{self.get_help_text()}\n\n"
            f"📋 사용법:\n"
            f"• Google Sheets '커스텀' 시트에 명령어와 문구를 등록\n"
            f"• [명령어] 형태로 사용\n"
            f"• 여러 문구가 있으면 랜덤 선택\n\n"
            f"🎲 다이스 표현식 지원:\n"
            f"• {{1d100}} - 100면체 주사위 1개\n"
            f"• {{2d6}} - 6면체 주사위 2개\n"
            f"• {{1d20+5}} - 20면체 주사위 1개 + 5\n"
            f"• {{3d6<4}} - 6면체 주사위 3개, 4 이하면 성공\n"
            f"• {{1d20>15}} - 20면체 주사위 1개, 15 이상이면 성공\n\n"
            f"💡 예시:\n"
            f"명령어: 점수\n"
            f"문구: 오늘의 점수는 {{1d100}}점입니다.\n"
            f"결과: 오늘의 점수는 73점입니다.\n\n"
            f"⚙️ 제한사항:\n"
            f"• 최대 주사위 개수: {config.MAX_DICE_COUNT}개\n"
            f"• 최대 주사위 면수: {config.MAX_DICE_SIDES}면\n"
            f"• 캐시 TTL: {config.FORTUNE_CACHE_TTL}초"
        )
    
    def get_available_commands(self) -> List[str]:
        """
        사용 가능한 커스텀 명령어 목록 반환
        
        Returns:
            List[str]: 커스텀 명령어 목록
        """
        try:
            custom_commands = self._load_custom_commands()
            return list(custom_commands.keys())
        except Exception as e:
            logger.error(f"커스텀 명령어 목록 조회 실패: {e}")
            return []
    
    def command_exists(self, command_keyword: str) -> bool:
        """
        특정 커스텀 명령어 존재 여부 확인
        
        Args:
            command_keyword: 확인할 명령어
            
        Returns:
            bool: 존재 여부
        """
        try:
            custom_commands = self._load_custom_commands()
            return command_keyword in custom_commands
        except Exception:
            return False
    
    def get_command_phrases(self, command_keyword: str) -> List[str]:
        """
        특정 명령어의 문구들 반환
        
        Args:
            command_keyword: 명령어
            
        Returns:
            List[str]: 해당 명령어의 문구들
        """
        try:
            custom_commands = self._load_custom_commands()
            return custom_commands.get(command_keyword, [])
        except Exception:
            return []
    
    def get_commands_count(self) -> int:
        """
        총 커스텀 명령어 개수 반환
        
        Returns:
            int: 명령어 개수
        """
        try:
            custom_commands = self._load_custom_commands()
            return len(custom_commands)
        except Exception:
            return 0
    
    def get_phrases_count(self) -> int:
        """
        총 문구 개수 반환
        
        Returns:
            int: 문구 개수
        """
        try:
            custom_commands = self._load_custom_commands()
            total_phrases = sum(len(phrases) for phrases in custom_commands.values())
            return total_phrases
        except Exception:
            return 0
    
    def validate_custom_data(self) -> Dict[str, Any]:
        """
        커스텀 명령어 데이터 유효성 검증
        
        Returns:
            Dict: 검증 결과
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'info': {}
        }
        
        try:
            # 시트에서 커스텀 데이터 로드 시도
            if self.sheets_manager:
                try:
                    custom_commands = self.sheets_manager.get_custom_commands()
                    if not custom_commands:
                        results['warnings'].append("커스텀 명령어가 없습니다.")
                        results['info']['commands_count'] = 0
                        results['info']['phrases_count'] = 0
                    else:
                        commands_count = len(custom_commands)
                        phrases_count = sum(len(phrases) for phrases in custom_commands.values())
                        
                        results['info']['commands_count'] = commands_count
                        results['info']['phrases_count'] = phrases_count
                        
                        # 빈 문구가 있는 명령어 확인
                        empty_commands = [cmd for cmd, phrases in custom_commands.items() if not phrases]
                        if empty_commands:
                            results['warnings'].append(f"문구가 없는 명령어: {', '.join(empty_commands)}")
                        
                        # 시스템 키워드와 중복 확인
                        system_conflicts = [cmd for cmd in custom_commands.keys() if cmd in config.SYSTEM_KEYWORDS]
                        if system_conflicts:
                            results['warnings'].append(f"시스템 키워드와 중복: {', '.join(system_conflicts)}")
                
                except Exception as e:
                    results['errors'].append(f"시트 데이터 로드 실패: {str(e)}")
                    results['info']['commands_count'] = 0
                    results['info']['phrases_count'] = 0
            else:
                results['warnings'].append("시트 매니저가 없습니다.")
                results['info']['commands_count'] = 0
                results['info']['phrases_count'] = 0
            
            # 캐시 상태 확인
            cached_commands = bot_cache.get_custom_commands()
            results['info']['cache_available'] = cached_commands is not None
            if cached_commands:
                results['info']['cached_commands_count'] = len(cached_commands)
            
            # 오류가 있으면 유효하지 않음
            if results['errors']:
                results['valid'] = False
            
        except Exception as e:
            results['valid'] = False
            results['errors'].append(f"검증 중 오류: {str(e)}")
        
        return results
    
    def clear_custom_cache(self) -> Dict[str, Any]:
        """
        커스텀 명령어 캐시 초기화 (관리자용)
        
        Returns:
            Dict: 초기화 결과
        """
        try:
            # 커스텀 명령어 캐시 초기화
            bot_cache.command_cache.delete("custom_commands")
            
            # 캐시 정리
            general_cleared = bot_cache.general_cache.cleanup_expired()
            command_cleared = bot_cache.command_cache.cleanup_expired()
            
            return {
                'success': True,
                'custom_commands_cache_cleared': True,
                'general_cache_cleaned': general_cleared,
                'command_cache_cleaned': command_cleared
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# 커스텀 명련어 관련 유틸리티 함수들
def is_custom_keyword(keyword: str, available_commands: List[str] = None) -> bool:
    """
    키워드가 커스텀 명령어인지 확인
    
    Args:
        keyword: 확인할 키워드
        available_commands: 사용 가능한 커스텀 명령어 목록 (None이면 시스템 키워드 제외 로직만)
        
    Returns:
        bool: 커스텀 명령어 여부
    """
    if not keyword:
        return False
    
    # 시스템 키워드가 아닌 경우
    if keyword not in config.SYSTEM_KEYWORDS:
        if available_commands is not None:
            return keyword in available_commands
        else:
            return True  # 시스템 키워드가 아니면 잠재적 커스텀 명령어
    
    return False


def extract_dice_expressions_from_text(text: str) -> List[str]:
    """
    텍스트에서 다이스 표현식들 추출
    
    Args:
        text: 분석할 텍스트
        
    Returns:
        List[str]: 발견된 다이스 표현식들
    """
    if not text:
        return []
    
    dice_pattern = r'\{(\d+[dD]\d+(?:[+\-]\d+)?(?:[<>]\d+)?)\}'
    matches = re.findall(dice_pattern, text)
    return matches


def validate_dice_expression_in_phrase(dice_expr: str) -> Tuple[bool, str]:
    """
    커스텀 문구의 다이스 표현식 유효성 검사
    
    Args:
        dice_expr: 다이스 표현식 (중괄호 제외)
        
    Returns:
        Tuple[bool, str]: (유효성, 메시지)
    """
    try:
        custom_command = CustomCommand()
        result = custom_command._roll_single_dice(dice_expr)
        return True, "유효한 다이스 표현식입니다."
    except ValueError as e:
        return False, str(e)
    except Exception as e:
        return False, f"검증 오류: {str(e)}"


def preview_phrase_with_dice(phrase: str) -> Dict[str, Any]:
    """
    다이스가 포함된 문구 미리보기
    
    Args:
        phrase: 미리볼 문구
        
    Returns:
        Dict: 미리보기 결과
    """
    try:
        custom_command = CustomCommand()
        processed_phrase, dice_results = custom_command._process_dice_in_phrase(phrase)
        
        return {
            'original_phrase': phrase,
            'processed_phrase': processed_phrase,
            'dice_count': len(dice_results),
            'dice_expressions': [result.expression for result in dice_results],
            'dice_totals': [result.total for result in dice_results]
        }
    except Exception as e:
        return {
            'original_phrase': phrase,
            'error': str(e)
        }


# 커스텀 명령어 인스턴스 생성 함수
def create_custom_command(sheets_manager=None) -> CustomCommand:
    """
    커스텀 명령어 인스턴스 생성
    
    Args:
        sheets_manager: Google Sheets 관리자
        
    Returns:
        CustomCommand: 커스텀 명령어 인스턴스
    """
    return CustomCommand(sheets_manager)