"""
도움말 명령어 구현 - 최적화된 버전
Google Sheets에서 도움말 정보를 가져와 표시하는 명령어 클래스입니다.
새로운 BaseCommand 구조와 최적화된 에러 핸들링을 적용합니다.
"""

import os
import sys
from typing import List, Tuple, Any, Optional, Dict

# 경로 설정 (VM 환경 대응)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

try:
    from config.settings import config
    from utils.logging_config import logger, bot_logger
    # from utils.error_handling.exceptions import HelpError
    # from utils.error_handling.handler import ErrorHandler, get_error_handler
    from utils.cache_manager import bot_cache
    from commands.base_command import BaseCommand
    from models.user import User
    from models.command_result import CommandType, CommandStatus, HelpResult, create_help_result
except ImportError:
    # VM 환경에서 임포트 실패 시 폴백
    import logging
    logger = logging.getLogger('help_command')
    
    # 기본 클래스들 정의
    class HelpError(Exception):
        pass
    
    class BaseCommand:
        def __init__(self, sheets_manager=None):
            self.sheets_manager = sheets_manager
        
        def execute(self, user, keywords):
            # Fallback implementation
            return "도움말 명령어 실행 중..."
    
    class User:
        def __init__(self, id: str, name: str = ""):
            self.id = id
            self.name = name
        
        def get_display_name(self):
            return self.name or self.id
    
    class CommandType:
        HELP = "help"
    
    class CommandStatus:
        SUCCESS = "success"
        ERROR = "error"
    
    class HelpResult:
        def __init__(self, help_text: str, command_count: int = 0, **kwargs):
            self.help_text = help_text
            self.command_count = command_count
            for key, value in kwargs.items():
                setattr(self, key, value)


class HelpCommand(BaseCommand):
    """
    최적화된 도움말 명령어 클래스
    
    Google Sheets의 '도움말' 시트에서 명령어 정보를 가져와 표시합니다.
    
    지원하는 형식:
    - [도움말] : 모든 명령어 도움말 표시
    """
    
    # 기본 도움말 내용 (시트 로드 실패 시 사용)
    DEFAULT_HELP = """자동봇 답변의 공개 범위는 명령어를 포함한 멘션의 공개 범위를 따릅니다.

사용 가능한 명령어는 다음과 같습니다.
[nDm] - m면체 주사위를 n개 굴립니다.
[nDm<k] - m면체 주사위를 n개 굴리고, k 이하의 숫자가 나오면 성공합니다.
[nDm>k] - m면체 주사위를 n개 굴리고, k 이상의 숫자가 나오면 성공합니다.
[카드뽑기/n장] - 트럼프 카드를 n장 뽑습니다.
[운세] - 오늘의 운세를 볼 수 있습니다.
[도움말] - 도움말을 보여줍니다."""
    
    def _get_command_type(self) -> CommandType:
        """명령어 타입 반환"""
        return CommandType.HELP
    
    def _get_command_name(self) -> str:
        """명령어 이름 반환"""
        return "도움말"
    
    def _execute_command(self, user: User, keywords: List[str]) -> Tuple[str, HelpResult]:
        """
        도움말 명령어 실행
        
        Args:
            user: 사용자 객체
            keywords: 키워드 리스트 ([도움말])
            
        Returns:
            Tuple[str, HelpResult]: (결과 메시지, 도움말 결과 객체)
        """
        # 도움말 내용 생성
        help_text = self._generate_help_text()
        
        # 명령어 개수 계산
        command_count = self._count_commands_in_help(help_text)
        
        # 결과 객체 생성
        help_result = create_help_result(help_text, command_count)
        
        return help_text, help_result
    
    def _generate_help_text(self) -> str:
        """
        도움말 텍스트 생성
        
        Returns:
            str: 완성된 도움말 텍스트
        """
        # 도움말 항목 로드
        help_items = self._load_help_items()
        
        if not help_items:
            logger.info("시트 도움말 없음, 기본 도움말 사용")
            return self.DEFAULT_HELP
        
        # 도움말 텍스트 구성
        base_message = (
            "자동봇 답변의 공개 범위는 명령어를 포함한 멘션의 공개 범위를 따릅니다.\n"
            "사용 가능한 명령어는 다음과 같습니다.\n\n"
        )
        
        # 도움말 항목들을 문자열로 변환
        help_lines = []
        for item in help_items:
            command = item.get('명령어', '').strip()
            description = item.get('설명', '').strip()
            
            if command and description:
                help_lines.append(f"{command} - {description}")
        
        if not help_lines:
            logger.warning("유효한 도움말 항목 없음, 기본 도움말 사용")
            return self.DEFAULT_HELP
        
        help_content = "\n".join(help_lines)
        return base_message + help_content
    
    def _load_help_items(self) -> List[Dict[str, str]]:
        """
        도움말 항목 로드 (수정된 버전)
        """
        # 직접 캐시에서 조회 (fetch_func 없이)
        cached_items = bot_cache.get("help_items")
        if cached_items:
            logger.debug("캐시에서 도움말 항목 로드")
            return cached_items
        
        # 시트에서 로드
        try:
            if self.sheets_manager:
                items = self.sheets_manager.get_help_items()
                if items:
                    # 캐시에 저장 (1시간)
                    bot_cache.set("help_items", items, 3600)
                    logger.debug(f"시트에서 도움말 항목 로드: {len(items)}개")
                    return items
        except Exception as e:
            logger.warning(f"시트에서 도움말 항목 로드 실패: {e}")
        
        # 빈 리스트 반환
        logger.info("도움말 항목 없음")
        return []
    
    def _count_commands_in_help(self, help_text: str) -> int:
        """
        도움말 텍스트에서 명령어 개수 계산
        
        Args:
            help_text: 도움말 텍스트
            
        Returns:
            int: 명령어 개수
        """
        if not help_text:
            return 0
        
        # 줄바꿈으로 분할하여 명령어 라인 찾기
        lines = help_text.split('\n')
        command_count = 0
        
        for line in lines:
            line = line.strip()
            # '[' 로 시작하거나 ' - ' 를 포함하는 라인을 명령어로 간주
            if line.startswith('[') or ' - ' in line:
                command_count += 1
        
        return command_count
    
    def get_help_text(self) -> str:
        """도움말 텍스트 반환"""
        return "[도움말] - 도움말을 보여줍니다."
    
    def get_extended_help(self) -> str:
        """확장 도움말 반환"""
        return (
            f"{self.get_help_text()}\n\n"
            f"📋 기능:\n"
            f"• Google Sheets '도움말' 시트에서 명령어 정보 로드\n"
            f"• 모든 사용 가능한 명령어와 설명 표시\n"
            f"• 시트에 데이터가 없으면 기본 도움말 제공\n"
            f"• 캐시 TTL: {config.FORTUNE_CACHE_TTL}초\n\n"
            f"💡 시트 구조:\n"
            f"• 명령어 컬럼: 명령어 이름\n"
            f"• 설명 컬럼: 명령어 설명"
        )
    
    def get_help_statistics(self) -> Dict[str, Any]:
        """
        도움말 통계 정보 반환
        
        Returns:
            Dict: 도움말 시스템 통계
        """
        try:
            # 도움말 항목 개수
            help_items = self._load_help_items()
            total_items = len(help_items)
            
            # 시트에서 로드된 항목 수
            sheet_items = 0
            if self.sheets_manager:
                try:
                    sheet_data = self.sheets_manager.get_help_items()
                    sheet_items = len(sheet_data) if sheet_data else 0
                except:
                    pass
            
            # 기본 도움말 사용 여부
            using_default = sheet_items == 0
            
            return {
                'total_help_items': total_items,
                'sheet_items_count': sheet_items,
                'using_default_help': using_default,
                'cache_available': bot_cache.get_help_items() is not None,
                'cache_ttl': config.FORTUNE_CACHE_TTL
            }
            
        except Exception as e:
            logger.error(f"도움말 통계 조회 실패: {e}")
            return {'error': str(e)}
    
    def validate_help_data(self) -> Dict[str, Any]:
        """
        도움말 데이터 유효성 검증
        
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
            # 시트에서 도움말 데이터 로드 시도
            if self.sheets_manager:
                try:
                    help_items = self.sheets_manager.get_help_items()
                    if not help_items:
                        results['warnings'].append("시트에 도움말 데이터가 없습니다.")
                        results['info']['will_use_default'] = True
                    else:
                        results['info']['sheet_items_count'] = len(help_items)
                        
                        # 빈 항목 확인
                        empty_items = sum(1 for item in help_items 
                                        if not item.get('명령어', '').strip() or 
                                           not item.get('설명', '').strip())
                        if empty_items > 0:
                            results['warnings'].append(f"빈 도움말 항목이 {empty_items}개 있습니다.")
                        
                        # 중복 명령어 확인
                        commands = [item.get('명령어', '').strip() for item in help_items]
                        duplicates = [cmd for cmd in set(commands) if commands.count(cmd) > 1]
                        if duplicates:
                            results['warnings'].append(f"중복된 명령어: {', '.join(duplicates)}")
                
                except Exception as e:
                    results['errors'].append(f"시트 데이터 로드 실패: {str(e)}")
                    results['info']['will_use_default'] = True
            else:
                results['warnings'].append("시트 매니저가 없습니다. 기본 도움말을 사용합니다.")
                results['info']['will_use_default'] = True
            
            # 캐시 상태 확인
            cached_items = bot_cache.get_help_items()
            results['info']['cache_available'] = cached_items is not None
            if cached_items:
                results['info']['cached_items_count'] = len(cached_items)
            
            # 오류가 있으면 유효하지 않음
            if results['errors']:
                results['valid'] = False
            
        except Exception as e:
            results['valid'] = False
            results['errors'].append(f"검증 중 오류: {str(e)}")
        
        return results
    
    def clear_help_cache(self) -> Dict[str, Any]:
        """
        도움말 캐시 초기화 (관리자용)
        
        Returns:
            Dict: 초기화 결과
        """
        try:
            # 도움말 항목 캐시 초기화
            bot_cache.command_cache.delete("help_items")
            
            # 캐시 정리
            general_cleared = bot_cache.general_cache.cleanup_expired()
            command_cleared = bot_cache.command_cache.cleanup_expired()
            
            return {
                'success': True,
                'help_items_cache_cleared': True,
                'general_cache_cleaned': general_cleared,
                'command_cache_cleaned': command_cleared
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# 도움말 관련 유틸리티 함수들
def is_help_command(keyword: str) -> bool:
    """
    키워드가 도움말 명령어인지 확인
    
    Args:
        keyword: 확인할 키워드
        
    Returns:
        bool: 도움말 명령어 여부
    """
    if not keyword:
        return False
    
    keyword = keyword.lower().strip()
    return keyword in ['도움말', 'help', '헬프']


def generate_simple_help(commands_info: List[Dict[str, str]]) -> str:
    """
    간단한 도움말 텍스트 생성
    
    Args:
        commands_info: [{'command': str, 'description': str}] 형태의 명령어 정보
        
    Returns:
        str: 생성된 도움말 텍스트
    """
    if not commands_info:
        return "사용 가능한 명령어가 없습니다."
    
    help_lines = []
    for info in commands_info:
        command = info.get('command', '').strip()
        description = info.get('description', '').strip()
        
        if command and description:
            help_lines.append(f"{command} - {description}")
    
    if not help_lines:
        return "유효한 명령어 정보가 없습니다."
    
    return "사용 가능한 명령어:\n" + "\n".join(help_lines)


# 도움말 명령어 인스턴스 생성 함수
def create_help_command(sheets_manager=None) -> HelpCommand:
    """
    도움말 명령어 인스턴스 생성
    
    Args:
        sheets_manager: Google Sheets 관리자
        
    Returns:
        HelpCommand: 도움말 명령어 인스턴스
    """
    return HelpCommand(sheets_manager)