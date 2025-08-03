"""
명령어 라우터 (완전 수정 버전)
들어온 키워드를 분석하여 적절한 명령어 클래스로 라우팅하는 모듈입니다.
안정성과 단순함에 중점을 둔 완전한 재설계
"""

import os
import sys
import re
import time
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass

# 경로 설정 (VM 환경 대응)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

try:
    from config.settings import config
    from utils.logging_config import logger, bot_logger, LogContext
    # SheetsManager를 선택적으로 import
    try:
        from utils.sheets import SheetsManager
        SHEETS_AVAILABLE = True
    except ImportError:
        SheetsManager = None
        SHEETS_AVAILABLE = False
    
    from utils.text_processing import extract_commands_from_text, parse_command_keywords
    from commands.base_command import BaseCommand, command_registry
    from models.user import User, create_empty_user
    
    # 플러그인 시스템 import (선택적)
    try:
        from plugins.commands.command_registry import command_registry as plugin_command_registry
        PLUGIN_SYSTEM_AVAILABLE = True
    except ImportError:
        plugin_command_registry = None
        PLUGIN_SYSTEM_AVAILABLE = False
    
    IMPORTS_SUCCESS = True
    
except ImportError as e:
    # VM 환경에서 임포트 실패 시 폴백
    import logging
    logger = logging.getLogger('command_router')
    logger.error(f"임포트 실패: {e}")
    IMPORTS_SUCCESS = False
    
    # 기본 클래스들 정의
    class BaseCommand:
        def __init__(self, sheets_manager=None):
            self.sheets_manager = sheets_manager
        
        def execute(self, user, keywords):
            return "명령어를 실행했습니다."
    
    # User 폴백
    class User:
        def __init__(self, id: str, name: str = ""):
            self.id = id
            self.name = name
        
        def is_valid(self):
            return bool(self.id and self.id.strip() and self.name and self.name.strip())
    
    # create_empty_user 폴백
    def create_empty_user(user_id: str):
        return User(user_id, "")
    
    # LogContext 폴백
    class LogContext:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
        
        def __enter__(self):
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
    
    # 플러그인 시스템 폴백
    plugin_command_registry = None
    PLUGIN_SYSTEM_AVAILABLE = False
    
    # SheetsManager 대체
    SheetsManager = None
    SHEETS_AVAILABLE = False
    
    # command_registry 폴백
    command_registry = {}


@dataclass
class CommandMatch:
    """명령어 매칭 결과"""
    command_type: Optional[str]
    command_instance: Optional[BaseCommand]
    confidence: float  # 0.0 ~ 1.0
    matched_keyword: str
    is_exact_match: bool


class CommandRouter:
    """
    완전히 수정된 명령어 라우팅 클래스
    
    안정성과 단순함에 중점:
    - 모든 결과를 문자열로 처리
    - 강화된 에러 처리
    - 단순화된 명령어 매칭
    - 안전한 사용자 객체 관리
    """
    
    def __init__(self, sheets_manager=None):
        """
        CommandRouter 초기화
        
        Args:
            sheets_manager: Google Sheets 관리자
        """
        self.sheets_manager = sheets_manager
        self._command_instances = {}
        self._command_mapping = {}
        self._initialize_commands()
        
        # 성능 통계 (최소화)
        self._stats = {
            'total_routes': 0,
            'successful_routes': 0,
            'failed_routes': 0,
            'cache_hits': 0,
            'unknown_commands': 0,
            'start_time': time.time()
        }
        
        logger.info("수정된 CommandRouter 초기화 완료")
    
    def _initialize_commands(self) -> None:
        """명령어 인스턴스들 초기화 (안전한 버전)"""
        try:
            # 명령어 매핑 테이블 (단순화)
            self._command_mapping = {
                # 기본 명령어
                '다이스': 'dice',
                'd': 'dice',
                '주사위': 'dice',
                
                '카드뽑기': 'card',
                '카드': 'card',
                '카드 뽑기': 'card',
                'card': 'card',
                
                '운세': 'fortune',
                'fortune': 'fortune',
                
                '도움말': 'help',
                '도움': 'help',
                'help': 'help',
                
                # 확장 명령어 (선택적)
                '소지금': 'money',
                '돈': 'money',
                '재화': 'money',
                '금액': 'money',
                'money': 'money',
                
                '인벤토리': 'inventory',
                '소지품': 'inventory',
                '가방': 'inventory',
                '아이템': 'inventory',
                'inventory': 'inventory',
                'inv': 'inventory',
                
                '상점': 'shop',
                '가게': 'shop',
                '상가': 'shop',
                'shop': 'shop',
                'store': 'shop',
                
                '구매': 'buy',
                '구입': 'buy',
                '사기': 'buy',
                'buy': 'buy',
                'purchase': 'buy',
                
                '양도': 'transfer',
                '전달': 'transfer',
                '주기': 'transfer',
                '넘기기': 'transfer',
                'transfer': 'transfer',
                'give': 'transfer',
                
                '송금': 'money_transfer',
                '돈주기': 'money_transfer',
                '재화양도': 'money_transfer',
                'send_money': 'money_transfer',
                'money_transfer': 'money_transfer',
                
                '설명': 'item_description',
                '정보': 'item_description',
                '상세': 'item_description',
                'info': 'item_description',
                'desc': 'item_description',
                'description': 'item_description'
            }
            
            logger.info(f"명령어 매핑 테이블 초기화 완료: {len(self._command_mapping)}개")
            
        except Exception as e:
            logger.error(f"명령어 초기화 실패: {e}")
            self._command_mapping = {
                '다이스': 'dice',
                '카드뽑기': 'card',
                '운세': 'fortune',
                '도움말': 'help'
            }
    
    def route_command(self, user_id: str, keywords: List[str]) -> str:
        """
        사용자 명령어를 분석하여 적절한 명령어를 실행 (단순화된 버전)
        
        Args:
            user_id: 사용자 ID
            keywords: 명령어 키워드들
            
        Returns:
            str: 명령어 실행 결과 (항상 문자열)
        """
        start_time = time.time()
        self._stats['total_routes'] += 1
        
        if not keywords:
            self._stats['failed_routes'] += 1
            return "명령어가 없습니다."
        
        # 플러그인 명령어 먼저 확인 (선택적)
        if PLUGIN_SYSTEM_AVAILABLE and plugin_command_registry:
            try:
                message = " ".join(keywords)
                plugin_result = self._try_plugin_command(message, user_id)
                if plugin_result:
                    self._stats['successful_routes'] += 1
                    return plugin_result
            except Exception as e:
                logger.debug(f"플러그인 명령어 실행 중 오류: {e}")
        
        # 키워드 정규화
        normalized_keywords = self._normalize_keywords_safe(keywords)
        first_keyword = normalized_keywords[0].strip().lower()
        
        try:
            # 명령어 매칭
            match_result = self._match_command_safe(first_keyword, normalized_keywords)
            
            if not match_result.command_instance:
                self._stats['unknown_commands'] += 1
                return self._create_not_found_message(user_id, first_keyword)
            
            # User 객체 생성
            user = self._get_user_safe(user_id)
            
            # 명령어 실행
            logger.debug(f"라우팅: {first_keyword} -> {match_result.command_type}")
            
            with LogContext(
                operation="명령어 라우팅",
                user_id=user_id,
                command=first_keyword,
                confidence=match_result.confidence
            ):
                result = match_result.command_instance.execute(user, normalized_keywords)
                
                # 결과를 문자열로 변환
                result_str = self._convert_to_string(result)
                
                self._stats['successful_routes'] += 1
                return result_str
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"명령어 라우팅 중 오류: {e}")
            self._stats['failed_routes'] += 1
            return self._create_execution_error_message(user_id, first_keyword, e)
    
    def _normalize_keywords_safe(self, keywords: List[str]) -> List[str]:
        """
        키워드 정규화 (안전한 버전)
        
        Args:
            keywords: 원본 키워드 리스트
            
        Returns:
            List[str]: 정규화된 키워드 리스트
        """
        normalized = []
        
        # 빠른 정규화 매핑
        quick_normalize = {
            '카드 뽑기': '카드뽑기',
            '카드  뽑기': '카드뽑기',
            '주사위': '다이스',
            '운세보기': '운세',
            '도움': '도움말'
        }
        
        for keyword in keywords:
            if not keyword:
                continue
                
            try:
                # 공백 제거
                clean_keyword = str(keyword).strip()
                if not clean_keyword:
                    continue
                
                # 빠른 매핑 확인
                if clean_keyword in quick_normalize:
                    normalized.append(quick_normalize[clean_keyword])
                else:
                    # 기본 정규화
                    normalized.append(clean_keyword)
                    
            except Exception as e:
                logger.debug(f"키워드 정규화 실패: {keyword} - {e}")
                continue
        
        return normalized if normalized else ['도움말']  # 폴백
    
    def _match_command_safe(self, first_keyword: str, keywords: List[str]) -> CommandMatch:
        """
        안전한 명령어 매칭
        
        Args:
            first_keyword: 첫 번째 키워드
            keywords: 전체 키워드 리스트
            
        Returns:
            CommandMatch: 매칭 결과
        """
        try:
            # 1. 직접 매핑 확인 (가장 빠름)
            if first_keyword in self._command_mapping:
                command_type = self._command_mapping[first_keyword]
                command_instance = self._get_command_instance_safe(command_type)
                
                return CommandMatch(
                    command_type=command_type,
                    command_instance=command_instance,
                    confidence=1.0,
                    matched_keyword=first_keyword,
                    is_exact_match=True
                )
            
            # 2. 다이스 표현식 직접 확인
            if self._is_dice_expression_safe(first_keyword):
                command_instance = self._get_command_instance_safe('dice')
                return CommandMatch(
                    command_type='dice',
                    command_instance=command_instance,
                    confidence=0.9,
                    matched_keyword=first_keyword,
                    is_exact_match=False
                )
            
            # 3. 커스텀 명령어 확인 (마지막에)
            if self._is_custom_command_safe(first_keyword):
                command_instance = self._get_command_instance_safe('custom')
                return CommandMatch(
                    command_type='custom',
                    command_instance=command_instance,
                    confidence=0.8,
                    matched_keyword=first_keyword,
                    is_exact_match=False
                )
            
            # 4. 매칭 실패
            return CommandMatch(
                command_type=None,
                command_instance=None,
                confidence=0.0,
                matched_keyword=first_keyword,
                is_exact_match=False
            )
            
        except Exception as e:
            logger.error(f"명령어 매칭 중 오류: {e}")
            return CommandMatch(
                command_type=None,
                command_instance=None,
                confidence=0.0,
                matched_keyword=first_keyword,
                is_exact_match=False
            )
    
    def _get_command_instance_safe(self, command_type: str) -> Optional[BaseCommand]:
        """
        명령어 인스턴스 안전한 조회
        
        Args:
            command_type: 명령어 타입
            
        Returns:
            Optional[BaseCommand]: 명령어 인스턴스
        """
        try:
            # 캐시된 인스턴스 확인
            if command_type in self._command_instances:
                self._stats['cache_hits'] += 1
                return self._command_instances[command_type]
            
            # 새 인스턴스 생성
            command_instance = self._create_command_instance_safe(command_type)
            if command_instance:
                self._command_instances[command_type] = command_instance
                logger.debug(f"명령어 인스턴스 생성: {command_type}")
            return command_instance
            
        except Exception as e:
            logger.error(f"명령어 인스턴스 조회 실패: {command_type} - {e}")
            return None
    
    def _create_command_instance_safe(self, command_type: str) -> Optional[BaseCommand]:
        """
        명령어 타입에 따른 인스턴스 안전한 생성
        
        Args:
            command_type: 명령어 타입
            
        Returns:
            Optional[BaseCommand]: 생성된 인스턴스
        """
        try:
            # 동적 임포트 (안전한 버전)
            if command_type == 'dice':
                try:
                    from commands.dice_command import DiceCommand
                    return DiceCommand(self.sheets_manager)
                except ImportError:
                    logger.warning("DiceCommand 임포트 실패")
                    return self._create_fallback_command('dice')
            
            elif command_type == 'card':
                try:
                    from commands.card_command import CardCommand
                    return CardCommand(self.sheets_manager)
                except ImportError:
                    logger.warning("CardCommand 임포트 실패")
                    return self._create_fallback_command('card')
            
            elif command_type == 'fortune':
                try:
                    from commands.fortune_command import FortuneCommand
                    return FortuneCommand(self.sheets_manager)
                except ImportError:
                    logger.warning("FortuneCommand 임포트 실패")
                    return self._create_fallback_command('fortune')
            
            elif command_type == 'help':
                try:
                    from commands.help_command import HelpCommand
                    return HelpCommand(self.sheets_manager)
                except ImportError:
                    logger.warning("HelpCommand 임포트 실패")
                    return self._create_fallback_command('help')
            
            elif command_type == 'custom':
                try:
                    from commands.custom_command import CustomCommand
                    return CustomCommand(self.sheets_manager)
                except ImportError:
                    logger.warning("CustomCommand 임포트 실패")
                    return self._create_fallback_command('custom')
            
            # 게임 시스템 명령어들 (안전한 임포트)
            elif command_type in ['money', 'inventory', 'shop', 'buy', 'transfer', 'money_transfer', 'item_description']:
                return self._safe_import_extended_command(command_type)
            
            else:
                logger.warning(f"알 수 없는 명령어 타입: {command_type}")
                return self._create_fallback_command(command_type)
                
        except Exception as e:
            logger.error(f"명령어 인스턴스 생성 중 오류: {command_type} - {e}")
            return self._create_fallback_command(command_type)
    
    def _safe_import_extended_command(self, command_type: str) -> BaseCommand:
        """
        확장 명령어 안전한 임포트
        
        Args:
            command_type: 명령어 타입
            
        Returns:
            BaseCommand: 명령어 인스턴스 (폴백 포함)
        """
        try:
            # 모듈명과 클래스명 매핑
            command_mapping = {
                'money': ('MoneyCommand', 'money_command'),
                'inventory': ('InventoryCommand', 'inventory_command'),
                'shop': ('ShopCommand', 'shop_command'),
                'buy': ('BuyCommand', 'buy_command'),
                'transfer': ('TransferCommand', 'transfer_command'),
                'money_transfer': ('MoneyTransferCommand', 'money_transfer_command'),
                'item_description': ('ItemDescriptionCommand', 'item_description_command')
            }
            
            if command_type not in command_mapping:
                return self._create_fallback_command(command_type)
            
            class_name, module_name = command_mapping[command_type]
            
            # 동적 임포트 시도
            try:
                module = __import__(f"commands.{module_name}", fromlist=[class_name])
                command_class = getattr(module, class_name)
                return command_class(self.sheets_manager)
            except (ImportError, AttributeError) as e:
                logger.warning(f"{class_name} 임포트 실패: {e}")
                return self._create_fallback_command(command_type)
            
        except Exception as e:
            logger.error(f"확장 명령어 임포트 실패: {command_type} - {e}")
            return self._create_fallback_command(command_type)
    
    def _create_fallback_command(self, command_type: str) -> BaseCommand:
        """
        폴백 명령어 생성
        
        Args:
            command_type: 명령어 타입
            
        Returns:
            BaseCommand: 폴백 명령어 인스턴스
        """
        class FallbackCommand(BaseCommand):
            def __init__(self, sheets_manager, cmd_type):
                super().__init__(sheets_manager)
                self.cmd_type = cmd_type
            
            def execute(self, user, keywords):
                return f"[{'/'.join(keywords)}] 명령어는 현재 사용할 수 없습니다."
            
            def _get_command_type(self):
                return self.cmd_type
            
            def _get_command_name(self):
                return self.cmd_type
        
        return FallbackCommand(self.sheets_manager, command_type)
    
    def _get_user_safe(self, user_id: str) -> User:
        """
        안전한 User 객체 생성
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            User: 사용자 객체 (항상 반환)
        """
        try:
            # 실시간 사용자 로드 시도
            if self.sheets_manager:
                try:
                    user_data = self.sheets_manager.find_user_by_id_real_time(user_id)
                    if user_data:
                        if hasattr(User, 'from_sheet_data'):
                            user = User.from_sheet_data(user_data)
                            if user.is_valid():
                                return user
                        else:
                            # from_sheet_data 메서드가 없는 경우
                            name = user_data.get('이름', user_data.get('name', ''))
                            return User(user_id, name)
                except Exception as e:
                    logger.debug(f"사용자 로드 실패: {user_id} - {e}")
            
            # 실패하거나 시트 매니저가 없으면 빈 객체 반환
            return create_empty_user(user_id)
            
        except Exception as e:
            logger.debug(f"사용자 객체 생성 실패: {user_id} - {e}")
            return User(user_id, user_id)  # 최종 폴백
    
    def _is_dice_expression_safe(self, keyword: str) -> bool:
        """
        다이스 표현식 여부 안전한 확인
        
        Args:
            keyword: 확인할 키워드
            
        Returns:
            bool: 다이스 표현식 여부
        """
        try:
            # 빠른 패턴 매칭
            if 'd' not in keyword.lower():
                return False
            
            # 정규식 검사
            dice_pattern = r'^\d+d\d+([+\-]\d+)?([<>]\d+)?$'
            return bool(re.match(dice_pattern, keyword.lower()))
            
        except Exception as e:
            logger.debug(f"다이스 표현식 확인 실패: {keyword} - {e}")
            return False
    
    def _is_custom_command_safe(self, keyword: str) -> bool:
        """
        커스텀 명령어 여부 안전한 확인
        
        Args:
            keyword: 확인할 키워드
            
        Returns:
            bool: 커스텀 명령어 여부
        """
        try:
            # 시스템 키워드는 제외
            if keyword in self._command_mapping:
                return False
            
            # 시트에서 확인 (안전한 버전)
            if not self.sheets_manager:
                return False
            
            try:
                if hasattr(self.sheets_manager, 'get_custom_commands_cached'):
                    custom_commands = self.sheets_manager.get_custom_commands_cached()
                    return keyword in custom_commands
                else:
                    # 메서드가 없는 경우 간단히 False 반환
                    return False
                    
            except Exception as e:
                logger.debug(f"커스텀 명령어 확인 실패: {keyword} - {e}")
                return False
                
        except Exception as e:
            logger.debug(f"커스텀 명령어 확인 중 오류: {keyword} - {e}")
            return False
    
    def _convert_to_string(self, result) -> str:
        """
        결과를 문자열로 안전하게 변환
        
        Args:
            result: 변환할 결과
            
        Returns:
            str: 문자열로 변환된 결과
        """
        try:
            # 1. 이미 문자열인 경우
            if isinstance(result, str):
                return result
            
            # 2. get_user_message 메서드가 있는 경우
            if hasattr(result, 'get_user_message') and callable(result.get_user_message):
                return str(result.get_user_message())
            
            # 3. message 속성이 있는 경우
            if hasattr(result, 'message'):
                return str(result.message)
            
            # 4. 튜플인 경우 (일부 명령어에서 반환)
            if isinstance(result, tuple) and len(result) > 0:
                return str(result[0])
            
            # 5. 리스트인 경우
            if isinstance(result, list) and len(result) > 0:
                return str(result[0])
            
            # 6. 기타 경우
            return str(result)
            
        except Exception as e:
            logger.error(f"결과 문자열 변환 실패: {e}")
            return "명령어를 처리했습니다."
    
    def _create_not_found_message(self, user_id: str, keyword: str) -> str:
        """명령어를 찾을 수 없을 때의 친절한 오류 메시지"""
        try:
            # 조사 처리 (안전한 방식)
            try:
                from utils.text_processing import detect_korean_particle
                keyword_particle = detect_korean_particle(keyword, 'object')
            except ImportError:
                keyword_particle = '을'  # 기본값
            
            error_message = (
                f"[{keyword}] 명령어{keyword_particle} 찾을 수 없습니다.\n"
                f"사용 가능한 명령어는 [도움말]을 입력해서 확인해주세요."
            )
            
        except Exception as e:
            logger.debug(f"오류 메시지 생성 실패: {e}")
            error_message = (
                f"[{keyword}] 명령어를 찾을 수 없습니다.\n"
                f"사용 가능한 명령어는 [도움말]을 입력해서 확인해주세요."
            )
        
        return error_message
    
    def _create_execution_error_message(self, user_id: str, keyword: str, error: Exception) -> str:
        """명령어 실행 오류 메시지 생성"""
        try:
            try:
                from utils.text_processing import detect_korean_particle
                keyword_particle = detect_korean_particle(keyword, 'subject')
            except ImportError:
                keyword_particle = '이'  # 기본값
            
            error_message = f"[{keyword}] 명령어{keyword_particle} 실행 중 오류가 발생했습니다."
            
        except Exception as e:
            logger.debug(f"실행 오류 메시지 생성 실패: {e}")
            error_message = f"[{keyword}] 명령어 실행 중 오류가 발생했습니다."
        
        return error_message
    
    def _try_plugin_command(self, message: str, user_id: str) -> Optional[str]:
        """
        플러그인 명령어 실행 시도 (안전한 버전)
        
        Args:
            message: 원본 메시지
            user_id: 사용자 ID
            
        Returns:
            Optional[str]: 플러그인 실행 결과 또는 None
        """
        try:
            # 플러그인 시스템이 사용 가능한지 확인
            if not plugin_command_registry or not PLUGIN_SYSTEM_AVAILABLE:
                return None
            
            # 플러그인 명령어 레지스트리에서 명령어 찾기
            if hasattr(plugin_command_registry, 'find_command'):
                result = plugin_command_registry.find_command(message)
                if not result:
                    return None
                
                handler, match_info = result
                
                # 사용자 정보 가져오기
                user = self._get_user_safe(user_id)
                
                # 플러그인 명령어 실행
                plugin_result = handler.plugin.execute(match_info)
                
                if plugin_result:
                    return self._convert_to_string(plugin_result)
            
            return None
            
        except Exception as e:
            logger.debug(f"플러그인 명령어 실행 오류: {e}")
            return None
    
    def get_command_statistics(self) -> Dict[str, Any]:
        """
        명령어 라우터 통계 반환
        
        Returns:
            Dict: 라우터 통계 정보
        """
        try:
            current_time = time.time()
            uptime = current_time - self._stats['start_time']
            
            stats = self._stats.copy()
            stats.update({
                'uptime_seconds': uptime,
                'uptime_hours': uptime / 3600,
                'initialized_commands': len(self._command_instances),
                'mapped_keywords': len(self._command_mapping),
                'success_rate': (
                    (self._stats['successful_routes'] / self._stats['total_routes'] * 100)
                    if self._stats['total_routes'] > 0 else 0
                ),
                'cache_hit_rate': (
                    (self._stats['cache_hits'] / self._stats['total_routes'] * 100)
                    if self._stats['total_routes'] > 0 else 0
                )
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"통계 조회 실패: {e}")
            return {
                'total_routes': 0,
                'successful_routes': 0,
                'failed_routes': 0,
                'cache_hits': 0,
                'unknown_commands': 0,
                'uptime_seconds': 0,
                'uptime_hours': 0,
                'initialized_commands': 0,
                'mapped_keywords': 0,
                'success_rate': 0,
                'cache_hit_rate': 0
            }
    
    def get_command_mapping_info(self) -> Dict[str, Any]:
        """
        명령어 매핑 정보 반환
        
        Returns:
            Dict: 매핑 정보
        """
        try:
            # 타입별 키워드 그룹화
            type_groups = {}
            for keyword, cmd_type in self._command_mapping.items():
                if cmd_type not in type_groups:
                    type_groups[cmd_type] = []
                type_groups[cmd_type].append(keyword)
            
            return {
                'total_mappings': len(self._command_mapping),
                'type_groups': type_groups,
                'initialized_instances': list(self._command_instances.keys())
            }
            
        except Exception as e:
            logger.error(f"매핑 정보 조회 실패: {e}")
            return {
                'total_mappings': 0,
                'type_groups': {},
                'initialized_instances': []
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        라우터 상태 확인
        
        Returns:
            Dict: 상태 정보
        """
        health_status = {
            'status': 'healthy',
            'errors': [],
            'warnings': [],
            'details': {}
        }
        
        try:
            # 기본 상태 확인
            if not self._command_mapping:
                health_status['errors'].append("명령어 매핑이 없습니다")
                health_status['status'] = 'error'
            
            # Sheets Manager 확인
            if not self.sheets_manager:
                health_status['warnings'].append("Sheets Manager가 연결되지 않았습니다")
                if health_status['status'] == 'healthy':
                    health_status['status'] = 'warning'
            
            # 통계 확인
            stats = self.get_command_statistics()
            health_status['details']['statistics'] = stats
            
            # 성능 지표 확인
            if stats['total_routes'] > 0:
                if stats['success_rate'] < 80:  # 80% 미만 성공률
                    health_status['warnings'].append(f"낮은 성공률: {stats['success_rate']:.1f}%")
                    if health_status['status'] == 'healthy':
                        health_status['status'] = 'warning'
                
                if stats['unknown_commands'] / stats['total_routes'] > 0.3:  # 30% 이상 알 수 없는 명령어
                    health_status['warnings'].append("알 수 없는 명령어 비율이 높습니다")
                    if health_status['status'] == 'healthy':
                        health_status['status'] = 'warning'
            
            # 인스턴스 상태 확인
            health_status['details']['instance_health'] = {}
            for type_key, instance in self._command_instances.items():
                try:
                    if hasattr(instance, 'health_check'):
                        instance_health = instance.health_check()
                        health_status['details']['instance_health'][type_key] = instance_health
                        
                        if instance_health.get('status') != 'healthy':
                            health_status['warnings'].append(f"{type_key} 명령어에 문제가 있습니다")
                            if health_status['status'] == 'healthy':
                                health_status['status'] = 'warning'
                except Exception as e:
                    health_status['warnings'].append(f"{type_key} 상태 확인 실패: {str(e)}")
            
            # 매핑 정보 추가
            health_status['details']['mapping_info'] = self.get_command_mapping_info()
            
        except Exception as e:
            health_status['errors'].append(f"상태 확인 중 오류: {str(e)}")
            health_status['status'] = 'error'
        
        return health_status
    
    def reset_stats(self) -> None:
        """통계 초기화"""
        try:
            self._stats = {
                'total_routes': 0,
                'successful_routes': 0,
                'failed_routes': 0,
                'cache_hits': 0,
                'unknown_commands': 0,
                'start_time': time.time()
            }
            logger.info("라우터 통계 초기화")
        except Exception as e:
            logger.error(f"통계 초기화 실패: {e}")
    
    def clear_command_cache(self) -> int:
        """명령어 인스턴스 캐시 정리"""
        try:
            count = len(self._command_instances)
            self._command_instances.clear()
            logger.info(f"명령어 인스턴스 캐시 정리: {count}개")
            return count
        except Exception as e:
            logger.error(f"캐시 정리 실패: {e}")
            return 0
    
    def validate_all_commands(self) -> Dict[str, Any]:
        """
        모든 명령어 유효성 검증
        
        Returns:
            Dict: 검증 결과
        """
        validation_result = {
            'overall_valid': True,
            'errors': [],
            'warnings': [],
            'command_results': {}
        }
        
        try:
            # 기본 명령어들 검증
            basic_commands = ['dice', 'card', 'fortune', 'help']
            
            for cmd_type in basic_commands:
                try:
                    instance = self._get_command_instance_safe(cmd_type)
                    if instance:
                        validation_result['command_results'][cmd_type] = {
                            'status': 'valid',
                            'instance_created': True
                        }
                    else:
                        validation_result['command_results'][cmd_type] = {
                            'status': 'invalid',
                            'instance_created': False
                        }
                        validation_result['errors'].append(f"{cmd_type} 명령어 인스턴스 생성 실패")
                        validation_result['overall_valid'] = False
                        
                except Exception as e:
                    validation_result['command_results'][cmd_type] = {
                        'status': 'error',
                        'error': str(e)
                    }
                    validation_result['errors'].append(f"{cmd_type} 명령어 검증 중 오류: {str(e)}")
                    validation_result['overall_valid'] = False
            
            # 매핑 테이블 검증
            if not self._command_mapping:
                validation_result['errors'].append("명령어 매핑 테이블이 비어있습니다")
                validation_result['overall_valid'] = False
            
            # Sheets Manager 검증
            if not self.sheets_manager:
                validation_result['warnings'].append("Sheets Manager가 없습니다")
            
        except Exception as e:
            validation_result['errors'].append(f"검증 중 오류: {str(e)}")
            validation_result['overall_valid'] = False
        
        return validation_result
    
    def get_status(self) -> Dict[str, Any]:
        """
        현재 상태 반환
        
        Returns:
            Dict: 상태 정보
        """
        return {
            'router_type': 'CommandRouter',
            'sheets_connected': self.sheets_manager is not None,
            'plugin_system_available': PLUGIN_SYSTEM_AVAILABLE,
            'imports_successful': IMPORTS_SUCCESS,
            'statistics': self.get_command_statistics(),
            'health': self.health_check(),
            'mapping_info': self.get_command_mapping_info()
        }


class SimpleCommandRouter:
    """
    간단한 명령어 라우터 (기존 코드와의 호환성용)
    """
    
    def __init__(self, sheets_manager=None):
        """SimpleCommandRouter 초기화"""
        try:
            self.router = CommandRouter(sheets_manager)
        except Exception as e:
            logger.error(f"SimpleCommandRouter 초기화 실패: {e}")
            self.router = None
    
    def check_keyword(self, keywords: List[str], user_id: str) -> Tuple[str, Optional[Any]]:
        """
        기존 check_keyword 함수와 호환되는 인터페이스
        
        Args:
            keywords: 키워드 리스트
            user_id: 사용자 ID
            
        Returns:
            Tuple[str, Any]: (결과 메시지, 미디어 ID)
        """
        try:
            if not self.router:
                return "명령어 처리 시스템을 사용할 수 없습니다.", None
            
            result = self.router.route_command(user_id, keywords)
            return str(result), None
                
        except Exception as e:
            logger.error(f"SimpleCommandRouter 오류: {e}")
            return "명령어 처리 중 오류가 발생했습니다.", None


# 전역 라우터 인스턴스
_global_router: Optional[CommandRouter] = None


def get_command_router() -> Optional[CommandRouter]:
    """전역 명령어 라우터 반환"""
    global _global_router
    if _global_router is None:
        try:
            _global_router = CommandRouter()
        except Exception as e:
            logger.error(f"전역 라우터 생성 실패: {e}")
            _global_router = None
    return _global_router


def initialize_command_router(sheets_manager=None) -> CommandRouter:
    """
    명령어 라우터 초기화
    
    Args:
        sheets_manager: Google Sheets 관리자
        
    Returns:
        CommandRouter: 초기화된 라우터
    """
    global _global_router
    try:
        _global_router = CommandRouter(sheets_manager)
        logger.info("전역 명령어 라우터 초기화 완료")
        return _global_router
    except Exception as e:
        logger.error(f"명령어 라우터 초기화 실패: {e}")
        # 폴백 라우터 생성
        _global_router = CommandRouter(None)
        return _global_router


def route_command(user_id: str, keywords: List[str]) -> str:
    """
    편의 함수: 명령어 라우팅 실행
    
    Args:
        user_id: 사용자 ID
        keywords: 키워드 리스트
        
    Returns:
        str: 실행 결과
    """
    try:
        router = get_command_router()
        if router:
            return router.route_command(user_id, keywords)
        else:
            return "명령어 처리 시스템을 사용할 수 없습니다."
    except Exception as e:
        logger.error(f"명령어 라우팅 실패: {e}")
        return "명령어 처리 중 오류가 발생했습니다."


def parse_command_from_text(text: str) -> List[str]:
    """
    텍스트에서 명령어 키워드 추출 (안전한 버전)
    
    Args:
        text: 분석할 텍스트 (예: "[다이스/2d6] 안녕하세요")
        
    Returns:
        List[str]: 추출된 키워드들 (예: ['다이스', '2d6'])
    """
    if not text:
        return []
    
    try:
        # 빠른 패턴 매칭
        match = re.search(r'\[([^\]]+)\]', text)
        if not match:
            return []
        
        keywords_str = match.group(1)
        if not keywords_str:
            return []
        
        # 키워드 분할
        keywords = []
        for keyword in keywords_str.split('/'):
            clean_keyword = str(keyword).strip()
            if clean_keyword:
                keywords.append(clean_keyword)
        
        return keywords
        
    except Exception as e:
        logger.debug(f"명령어 파싱 실패: {text} - {e}")
        return []


def validate_command_format(text: str) -> Tuple[bool, str]:
    """
    명령어 형식 유효성 검사 (안전한 버전)
    
    Args:
        text: 검사할 텍스트
        
    Returns:
        Tuple[bool, str]: (유효성, 메시지)
    """
    if not text:
        return False, "텍스트가 비어있습니다."
    
    try:
        # 기본 형식 확인
        if '[' not in text or ']' not in text:
            return False, "명령어는 [명령어] 형식으로 입력해야 합니다."
        
        start_pos = text.find('[')
        end_pos = text.find(']')
        
        if start_pos >= end_pos:
            return False, "명령어 형식이 올바르지 않습니다. [명령어] 순서를 확인해주세요."
        
        # 키워드 추출 및 확인
        keywords = parse_command_from_text(text)
        if not keywords:
            return False, "명령어가 비어있습니다."
        
        return True, "올바른 명령어 형식입니다."
        
    except Exception as e:
        logger.debug(f"명령어 형식 검증 실패: {text} - {e}")
        return False, f"명령어 형식 검증 중 오류가 발생했습니다."


# 성능 모니터링 및 최적화 함수들
def get_router_performance_report() -> str:
    """
    라우터 성능 리포트 생성
    
    Returns:
        str: 성능 리포트
    """
    try:
        router = get_command_router()
        if not router:
            return "라우터를 사용할 수 없습니다."
        
        stats = router.get_command_statistics()
        health = router.health_check()
        mapping_info = router.get_command_mapping_info()
        
        report_lines = ["=== 수정된 명령어 라우터 성능 리포트 ==="]
        
        # 기본 통계
        report_lines.append(f"\n📊 라우팅 통계:")
        report_lines.append(f"  총 라우팅: {stats['total_routes']:,}회")
        report_lines.append(f"  성공: {stats['successful_routes']:,}회 ({stats['success_rate']:.1f}%)")
        report_lines.append(f"  실패: {stats['failed_routes']:,}회")
        report_lines.append(f"  알 수 없는 명령어: {stats['unknown_commands']:,}회")
        report_lines.append(f"  캐시 히트: {stats['cache_hits']:,}회 ({stats['cache_hit_rate']:.1f}%)")
        
        # 성능 지표
        report_lines.append(f"\n🚀 성능 지표:")
        report_lines.append(f"  가동 시간: {stats['uptime_hours']:.1f}시간")
        report_lines.append(f"  초기화된 명령어: {stats['initialized_commands']}개")
        report_lines.append(f"  매핑된 키워드: {stats['mapped_keywords']}개")
        
        # 명령어 타입별 매핑
        report_lines.append(f"\n🗂️ 명령어 타입별 키워드:")
        for type_name, keywords in mapping_info['type_groups'].items():
            report_lines.append(f"  {type_name}: {len(keywords)}개 키워드")
            # 상위 5개만 표시
            sample_keywords = keywords[:5]
            if len(keywords) > 5:
                sample_keywords.append(f"... 외 {len(keywords)-5}개")
            report_lines.append(f"    {', '.join(sample_keywords)}")
        
        # 상태 확인
        report_lines.append(f"\n🏥 상태: {health['status']}")
        if health['warnings']:
            report_lines.append(f"⚠️ 경고:")
            for warning in health['warnings']:
                report_lines.append(f"  - {warning}")
        
        if health['errors']:
            report_lines.append(f"❌ 오류:")
            for error in health['errors']:
                report_lines.append(f"  - {error}")
        
        # 수정 사항
        report_lines.append(f"\n✅ 주요 수정 사항:")
        report_lines.append(f"  - 모든 결과를 문자열로 통일")
        report_lines.append(f"  - 안전한 명령어 인스턴스 생성")
        report_lines.append(f"  - 폴백 명령어 시스템")
        report_lines.append(f"  - 강화된 예외 처리")
        report_lines.append(f"  - 단순화된 사용자 객체 관리")
        
        return "\n".join(report_lines)
        
    except Exception as e:
        return f"라우터 성능 리포트 생성 실패: {e}"


def optimize_router_performance():
    """라우터 성능 최적화 실행"""
    try:
        router = get_command_router()
        if not router:
            logger.warning("라우터가 없어 최적화를 수행할 수 없습니다")
            return
        
        # 사용하지 않는 명령어 인스턴스 정리
        cleared = router.clear_command_cache()
        
        # 통계 초기화 (선택적)
        stats = router.get_command_statistics()
        if stats['total_routes'] > 100000:  # 10만회 이상일 때
            router.reset_stats()
            logger.info("라우터 통계 초기화 완료")
        
        logger.info(f"라우터 성능 최적화 완료: {cleared}개 인스턴스 정리")
        
    except Exception as e:
        logger.error(f"라우터 성능 최적화 실패: {e}")


def benchmark_router_performance(iterations: int = 1000) -> Dict[str, Any]:
    """
    라우터 성능 벤치마크
    
    Args:
        iterations: 반복 횟수
        
    Returns:
        Dict: 벤치마크 결과
    """
    try:
        router = get_command_router()
        if not router:
            return {'error': '라우터를 사용할 수 없습니다'}
        
        # 테스트 케이스들
        test_cases = [
            (['다이스', '2d6'], '다이스 명령어'),
            (['카드뽑기', '5장'], '카드 명령어'),
            (['운세'], '운세 명령어'),
            (['도움말'], '도움말 명령어'),
            (['2d20'], '다이스 표현식'),
            (['unknown_command'], '알 수 없는 명령어'),
        ]
        
        results = {}
        
        for keywords, description in test_cases:
            start_time = time.time()
            
            for i in range(iterations):
                try:
                    router.route_command(f"bench_user_{i}", keywords)
                except Exception:
                    pass  # 벤치마크이므로 오류 무시
            
            end_time = time.time()
            total_time = end_time - start_time
            avg_time = total_time / iterations
            
            results[description] = {
                'total_time': total_time,
                'avg_time': avg_time,
                'ops_per_second': iterations / total_time if total_time > 0 else 0
            }
        
        return results
        
    except Exception as e:
        logger.error(f"벤치마크 실행 실패: {e}")
        return {'error': str(e)}


# 라우터 테스트 함수
def test_command_routing():
    """명령어 라우팅 테스트"""
    print("=== 수정된 명령어 라우팅 테스트 ===")
    
    test_cases = [
        (['다이스', '2d6'], 'dice'),
        (['2d6'], 'dice'),
        (['카드뽑기', '5장'], 'card'),
        (['카드 뽑기', '3장'], 'card'),
        (['운세'], 'fortune'),
        (['도움말'], 'help'),
        (['소지금'], 'money'),
        (['인벤토리'], 'inventory'),
        (['상점'], 'shop'),
        (['구매', '포션', '5개'], 'buy'),
        (['양도', '검', '@user2'], 'transfer'),
        (['unknown'], None),
    ]
    
    try:
        router = CommandRouter()
        
        for keywords, expected_type in test_cases:
            try:
                start_time = time.time()
                match_result = router._match_command_safe(keywords[0], keywords)
                end_time = time.time()
                
                actual_type = match_result.command_type
                confidence = match_result.confidence
                execution_time = (end_time - start_time) * 1000  # ms
                
                if expected_type is None:
                    status = "✅" if actual_type is None else "❌"
                    expected_display = "UNKNOWN"
                else:
                    status = "✅" if actual_type == expected_type else "❌"
                    expected_display = expected_type
                
                actual_display = actual_type if actual_type else "UNKNOWN"
                
                print(f"{status} {keywords} -> {actual_display} (예상: {expected_display}) "
                      f"신뢰도: {confidence:.2f}, 시간: {execution_time:.3f}ms")
                
            except Exception as e:
                print(f"❌ {keywords} -> 오류: {e}")
        
        # 성능 통계
        stats = router.get_command_statistics()
        print(f"\n📊 테스트 통계:")
        print(f"  총 라우팅: {stats['total_routes']}회")
        print(f"  성공률: {stats['success_rate']:.1f}%")
        print(f"  캐시 히트율: {stats['cache_hit_rate']:.1f}%")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
    
    print("=" * 60)


def test_korean_particles_in_router():
    """라우터에서 한글 조사 처리 테스트"""
    print("\n=== 라우터 한글 조사 처리 테스트 ===")
    
    try:
        router = CommandRouter()
        test_user = "test_user"
        
        # 존재하지 않는 명령어들로 테스트
        unknown_commands = ['검', '방패', '포션', '마법', '물약']
        
        for command in unknown_commands:
            try:
                result = router._create_not_found_message(test_user, command)
                print(f"'{command}' -> {result}")
            except Exception as e:
                print(f"'{command}' -> 오류: {e}")
                
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
    
    print("=" * 60)


def test_performance_optimization():
    """성능 최적화 테스트"""
    print("\n=== 성능 최적화 테스트 ===")
    
    try:
        # 벤치마크 실행
        print("1. 라우터 벤치마크 실행 중...")
        benchmark_results = benchmark_router_performance(100)  # 100회로 축소
        
        if 'error' in benchmark_results:
            print(f"❌ 벤치마크 실패: {benchmark_results['error']}")
        else:
            print("2. 벤치마크 결과:")
            for test_name, result in benchmark_results.items():
                print(f"   {test_name}:")
                print(f"     평균 시간: {result['avg_time']*1000:.3f}ms")
                print(f"     초당 처리: {result['ops_per_second']:.0f}회")
        
        # 성능 최적화 실행
        print("\n3. 성능 최적화 실행...")
        optimize_router_performance()
        
        # 최적화 후 상태
        print("\n4. 최적화 후 상태:")
        router = get_command_router()
        if router:
            health = router.health_check()
            print(f"   상태: {health['status']}")
            print(f"   경고: {len(health['warnings'])}개")
            print(f"   오류: {len(health['errors'])}개")
        
        print("\n✅ 성능 최적화 테스트 완료")
        
    except Exception as e:
        print(f"❌ 성능 테스트 실패: {e}")
    
    print("=" * 60)


# 모듈 로드 완료 로깅
logger.info("완전히 수정된 명령어 라우터 모듈 로드 완료")


# 테스트 실행 (개발 환경에서만)
if __name__ == "__main__":
    test_command_routing()
    test_korean_particles_in_router()
    test_performance_optimization()
    
    # 성능 리포트 출력
    print("\n" + get_router_performance_report())