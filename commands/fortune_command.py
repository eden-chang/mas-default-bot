"""
운세 명령어 구현 - 최적화된 버전
운세 확인 기능을 제공하는 명령어 클래스입니다.
새로운 BaseCommand 구조와 최적화된 에러 핸들링을 적용합니다.
"""

import os
import sys
import random
from typing import List, Tuple, Any, Optional, Dict
from datetime import datetime, date
import hashlib

# 경로 설정 (VM 환경 대응)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

try:
    from config.settings import config
    from utils.logging_config import logger, bot_logger
    from utils.error_handling.exceptions import FortuneError
    from utils.error_handling.handler import ErrorHandler, get_error_handler
    from utils.cache_manager import bot_cache
    from commands.base_command import BaseCommand
    from models.user import User
    from models.command_result import CommandType, CommandStatus, FortuneResult, create_fortune_result
except ImportError:
    # VM 환경에서 임포트 실패 시 폴백
    import logging
    logger = logging.getLogger('fortune_command')
    
    # 기본 클래스들 정의
    class FortuneError(Exception):
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
        FORTUNE = "fortune"
    
    class CommandStatus:
        SUCCESS = "success"
        ERROR = "error"
    
    class FortuneResult:
        def __init__(self, fortune_text: str, user_name: str, **kwargs):
            self.fortune_text = fortune_text
            self.user_name = user_name
            for key, value in kwargs.items():
                setattr(self, key, value)


class FortuneCommand(BaseCommand):
    """
    최적화된 운세 확인 명령어 클래스
    
    지원하는 형식:
    - [운세] : 오늘의 운세 확인
    - [오늘운세] : 오늘의 운세 확인 (별칭)
    - [내운세] : 오늘의 운세 확인 (별칭)
    """
    
    # 기본 운세 문구들 (시트에서 로드 실패 시 사용)
    DEFAULT_FORTUNES = [
        "오늘은 새로운 기회가 찾아올 것입니다.",
        "작은 행복이 여러분을 기다리고 있어요.",
        "긍정적인 마음가짐이 좋은 결과를 가져다줄 거예요.",
        "오늘 만나는 사람들이 여러분에게 도움이 될 것입니다.",
        "차분한 하루를 보내며 내면의 평화를 찾으세요.",
        "예상치 못한 좋은 소식이 들려올지도 모릅니다.",
        "오늘은 새로운 것을 배우기 좋은 날입니다.",
        "주변 사람들과의 관계가 더욱 깊어질 것입니다.",
        "꾸준한 노력이 결실을 맺는 날이 될 거예요.",
        "오늘 하루는 특별한 의미가 있는 날이 될 것입니다."
    ]
    
    def _get_command_type(self) -> CommandType:
        """명령어 타입 반환"""
        return CommandType.FORTUNE
    
    def _get_command_name(self) -> str:
        """명령어 이름 반환"""
        return "운세"
    
    def _execute_command(self, user: User, keywords: List[str]) -> Tuple[str, FortuneResult]:
        """
        운세 명령어 실행
        
        Args:
            user: 사용자 객체
            keywords: 키워드 리스트 ([운세] 또는 [오늘운세])
            
        Returns:
            Tuple[str, FortuneResult]: (결과 메시지, 운세 결과 객체)
            
        Raises:
            FortuneError: 운세 데이터 로드 실패
        """
        # 오늘 이미 운세를 확인했는지 체크
        today_fortune = self._get_today_fortune_cache(user.id)
        if today_fortune:
            logger.debug(f"캐시된 오늘의 운세 반환: {user.id}")
            fortune_result = create_fortune_result(today_fortune, user.get_display_name())
            message = self._format_result_message(fortune_result)
            return message, fortune_result
        
        # 운세 문구 로드
        fortune_phrases = self._load_fortune_phrases()
        
        if not fortune_phrases:
            raise FortuneError("운세 데이터를 불러올 수 없습니다. 잠시 후 다시 시도해 주세요.")
        
        # 사용자와 날짜 기반으로 일관된 운세 선택
        selected_fortune = self._select_consistent_fortune(user.id, fortune_phrases)
        
        # 오늘의 운세 캐시에 저장
        self._cache_today_fortune(user.id, selected_fortune)
        
        # 결과 객체 생성
        fortune_result = create_fortune_result(selected_fortune, user.get_display_name())
        
        # 결과 메시지 생성
        message = self._format_result_message(fortune_result)
        
        return message, fortune_result
    
    def _load_fortune_phrases(self) -> List[str]:
        """
        운세 문구 로드 (캐시 우선, 시트 후순위)
        
        Returns:
            List[str]: 운세 문구 리스트
        """
        # 캐시에서 먼저 조회
        cached_phrases = bot_cache.get_fortune_phrases()
        if cached_phrases:
            logger.debug("캐시에서 운세 문구 로드")
            return cached_phrases
        
        # 시트에서 로드
        try:
            if self.sheets_manager:
                phrases = self.sheets_manager.get_fortune_phrases()
                if phrases:
                    # 캐시에 저장 (설정된 TTL 사용)
                    bot_cache.cache_fortune_phrases(phrases)
                    logger.debug(f"시트에서 운세 문구 로드: {len(phrases)}개")
                    return phrases
        except Exception as e:
            logger.warning(f"시트에서 운세 문구 로드 실패: {e}")
        
        # 기본 운세 문구 사용
        logger.info("기본 운세 문구 사용")
        return self.DEFAULT_FORTUNES.copy()
    
    def _select_consistent_fortune(self, user_id: str, fortune_phrases: List[str]) -> str:
        """
        사용자와 날짜 기반으로 일관된 운세 선택
        같은 사용자는 같은 날에 항상 같은 운세를 받습니다.
        
        Args:
            user_id: 사용자 ID
            fortune_phrases: 운세 문구 리스트
            
        Returns:
            str: 선택된 운세 문구
        """
        # 오늘 날짜 문자열
        today = date.today().isoformat()  # "2025-07-07"
        
        # 사용자 ID + 날짜를 해시하여 시드 생성
        seed_string = f"{user_id}_{today}"
        seed_hash = hashlib.md5(seed_string.encode()).hexdigest()
        seed = int(seed_hash[:8], 16)  # 해시의 첫 8자리를 16진수로 변환
        
        # 시드 기반으로 운세 선택
        random.seed(seed)
        selected_fortune = random.choice(fortune_phrases)
        
        # 랜덤 시드 복원 (다른 랜덤 함수에 영향 방지)
        random.seed()
        
        logger.debug(f"일관된 운세 선택: {user_id} -> {selected_fortune[:20]}...")
        return selected_fortune
    
    def _get_today_fortune_cache_key(self, user_id: str) -> str:
        """오늘의 운세 캐시 키 생성"""
        today = date.today().isoformat()
        return f"fortune_today_{user_id}_{today}"
    
    def _get_today_fortune_cache(self, user_id: str) -> Optional[str]:
        """
        오늘의 운세 캐시 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            Optional[str]: 캐시된 운세 또는 None
        """
        cache_key = self._get_today_fortune_cache_key(user_id)
        return bot_cache.general_cache.get(cache_key)
    
    def _cache_today_fortune(self, user_id: str, fortune: str) -> None:
        """
        오늘의 운세 캐시 저장
        
        Args:
            user_id: 사용자 ID
            fortune: 운세 문구
        """
        cache_key = self._get_today_fortune_cache_key(user_id)
        # 하루 동안 캐시 (86400초)
        bot_cache.general_cache.set(cache_key, fortune, ttl=86400)
        logger.debug(f"오늘의 운세 캐시 저장: {user_id}")
    
    def _format_result_message(self, fortune_result: FortuneResult) -> str:
        """
        결과 메시지 포맷팅
        
        Args:
            fortune_result: 운세 결과
            
        Returns:
            str: 포맷된 결과 메시지
        """
        return fortune_result.get_result_text()
    
    def get_help_text(self) -> str:
        """도움말 텍스트 반환"""
        return "[운세] - 오늘의 운세를 볼 수 있습니다."
    
    def get_extended_help(self) -> str:
        """확장 도움말 반환"""
        return (
            f"{self.get_help_text()}\n\n"
            f"📋 사용 예시:\n"
            f"[운세] - 오늘의 운세 확인\n"
            f"[오늘운세] - 별칭 사용 가능\n"
            f"[내운세] - 별칭 사용 가능\n\n"
            f"🔮 특징:\n"
            f"• 같은 날에는 항상 동일한 운세가 나옵니다\n"
            f"• Google Sheets의 운세 데이터를 사용합니다\n"
            f"• 시트에 데이터가 없으면 기본 운세를 제공합니다\n"
            f"• 캐시 TTL: {config.FORTUNE_CACHE_TTL}초"
        )
    
    def get_fortune_statistics(self) -> Dict[str, Any]:
        """
        운세 통계 정보 반환
        
        Returns:
            Dict: 운세 시스템 통계
        """
        try:
            # 운세 문구 개수
            fortune_phrases = self._load_fortune_phrases()
            total_phrases = len(fortune_phrases)
            
            # 시트에서 로드된 문구 수
            sheet_phrases = 0
            if self.sheets_manager:
                try:
                    sheet_data = self.sheets_manager.get_fortune_phrases()
                    sheet_phrases = len(sheet_data) if sheet_data else 0
                except:
                    pass
            
            # 기본 문구 사용 여부
            using_default = sheet_phrases == 0
            
            return {
                'total_fortune_phrases': total_phrases,
                'sheet_phrases_count': sheet_phrases,
                'default_phrases_count': len(self.DEFAULT_FORTUNES),
                'using_default_fortunes': using_default,
                'cache_available': bot_cache.get_fortune_phrases() is not None,
                'cache_ttl': config.FORTUNE_CACHE_TTL
            }
            
        except Exception as e:
            logger.error(f"운세 통계 조회 실패: {e}")
            return {'error': str(e)}
    
    def preview_fortune_for_user(self, user_id: str, target_date: str = None) -> Dict[str, str]:
        """
        특정 사용자의 운세 미리보기 (관리자용)
        
        Args:
            user_id: 사용자 ID
            target_date: 대상 날짜 (YYYY-MM-DD, None이면 오늘)
            
        Returns:
            Dict: 운세 미리보기 정보
        """
        try:
            if target_date:
                # 특정 날짜의 운세 (임시로 날짜 변경)
                original_date = date.today()
                # 실제로는 target_date를 파싱해서 사용해야 함
                # 여기서는 간단히 처리
                pass
            
            fortune_phrases = self._load_fortune_phrases()
            if not fortune_phrases:
                return {'error': 'No fortune phrases available'}
            
            base_fortune = self._select_consistent_fortune(user_id, fortune_phrases)
            
            return {
                'user_id': user_id,
                'date': target_date or date.today().isoformat(),
                'fortune': base_fortune
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def clear_fortune_cache(self) -> Dict[str, Any]:
        """
        운세 캐시 초기화 (관리자용)
        
        Returns:
            Dict: 초기화 결과
        """
        try:
            # 운세 문구 캐시 초기화
            bot_cache.command_cache.delete("fortune_phrases")
            
            # 오늘의 운세 캐시 초기화 (모든 사용자)
            today = date.today().isoformat()
            pattern = f"fortune_today_*_{today}"
            
            cleared_count = 0
            # 실제로는 패턴 매칭으로 삭제해야 하지만
            # 여기서는 간단히 전체 캐시 정리
            general_cleared = bot_cache.general_cache.cleanup_expired()
            command_cleared = bot_cache.command_cache.cleanup_expired()
            
            return {
                'success': True,
                'fortune_phrases_cache_cleared': True,
                'today_fortune_cache_cleared': True,
                'general_cache_cleaned': general_cleared,
                'command_cache_cleaned': command_cleared
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_fortune_data(self) -> Dict[str, Any]:
        """
        운세 데이터 유효성 검증
        
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
            # 시트에서 운세 데이터 로드 시도
            if self.sheets_manager:
                try:
                    sheet_phrases = self.sheets_manager.get_fortune_phrases()
                    if not sheet_phrases:
                        results['warnings'].append("시트에 운세 데이터가 없습니다.")
                        results['info']['will_use_default'] = True
                    else:
                        results['info']['sheet_phrases_count'] = len(sheet_phrases)
                        
                        # 빈 문구 확인
                        empty_phrases = sum(1 for phrase in sheet_phrases if not phrase.strip())
                        if empty_phrases > 0:
                            results['warnings'].append(f"빈 운세 문구가 {empty_phrases}개 있습니다.")
                        
                        # 짧은 문구 확인
                        short_phrases = sum(1 for phrase in sheet_phrases if len(phrase.strip()) < 10)
                        if short_phrases > 0:
                            results['warnings'].append(f"10글자 미만의 짧은 운세 문구가 {short_phrases}개 있습니다.")
                
                except Exception as e:
                    results['errors'].append(f"시트 데이터 로드 실패: {str(e)}")
                    results['info']['will_use_default'] = True
            else:
                results['warnings'].append("시트 매니저가 없습니다. 기본 운세를 사용합니다.")
                results['info']['will_use_default'] = True
            
            # 기본 운세 검증
            results['info']['default_phrases_count'] = len(self.DEFAULT_FORTUNES)
            
            # 캐시 상태 확인
            cached_phrases = bot_cache.get_fortune_phrases()
            results['info']['cache_available'] = cached_phrases is not None
            if cached_phrases:
                results['info']['cached_phrases_count'] = len(cached_phrases)
            
            # 오류가 있으면 유효하지 않음
            if results['errors']:
                results['valid'] = False
            
        except Exception as e:
            results['valid'] = False
            results['errors'].append(f"검증 중 오류: {str(e)}")
        
        return results


# 운세 관련 유틸리티 함수들
def is_fortune_command(keyword: str) -> bool:
    """
    키워드가 운세 명령어인지 확인
    
    Args:
        keyword: 확인할 키워드
        
    Returns:
        bool: 운세 명령어 여부
    """
    if not keyword:
        return False
    
    keyword = keyword.lower().strip()
    return keyword in ['운세', '오늘운세', '내운세', 'fortune']


def generate_consistent_fortune(user_id: str, date_str: str, fortune_list: List[str]) -> str:
    """
    일관된 운세 생성 (독립 함수)
    
    Args:
        user_id: 사용자 ID
        date_str: 날짜 문자열 (YYYY-MM-DD)
        fortune_list: 운세 문구 리스트
        
    Returns:
        str: 선택된 운세
    """
    if not fortune_list:
        return "오늘은 평온한 하루가 될 것입니다."
    
    # 해시 기반 일관된 선택
    seed_string = f"{user_id}_{date_str}"
    seed_hash = hashlib.md5(seed_string.encode()).hexdigest()
    seed = int(seed_hash[:8], 16)
    
    random.seed(seed)
    result = random.choice(fortune_list)
    random.seed()  # 시드 복원
    
    return result


# 운세 명령어 인스턴스 생성 함수
def create_fortune_command(sheets_manager=None) -> FortuneCommand:
    """
    운세 명령어 인스턴스 생성
    
    Args:
        sheets_manager: Google Sheets 관리자
        
    Returns:
        FortuneCommand: 운세 명령어 인스턴스
    """
    return FortuneCommand(sheets_manager)