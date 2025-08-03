"""
명령어 라우터 (실시간 데이터 반영 최적화)
들어온 키워드를 분석하여 적절한 명령어 클래스로 라우팅하는 모듈입니다.
캐시 의존성 제거 및 성능 최적화 적용
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
    from models.command_result import CommandResult
    from models.enums.command_type import CommandType
    from models.user import User, create_empty_user
    # 플러그인 시스템 import
    try:
        from plugins.commands.command_registry import command_registry as plugin_command_registry
        PLUGIN_SYSTEM_AVAILABLE = True
    except ImportError:
        plugin_command_registry = None
        PLUGIN_SYSTEM_AVAILABLE = False
except ImportError:
    # VM 환경에서 임포트 실패 시 폴백
    import logging
    logger = logging.getLogger('command_router')
    
    # 기본 클래스들 정의
    class BaseCommand:
        pass
    
    class CommandResult:
        @staticmethod
        def error(**kwargs):
            return None
        
        @staticmethod
        def failure(**kwargs):
            return None
    
    # CommandType 폴백 - 더 완전한 정의
    class CommandType:
        DICE = "dice"
        CARD = "card"
        FORTUNE = "fortune"
        HELP = "help"
        CUSTOM = "custom"
        MONEY = "money"
        INVENTORY = "inventory"
        SHOP = "shop"
        BUY = "buy"
        TRANSFER = "transfer"
        ITEM_DESCRIPTION = "item_description"
        MONEY_TRANSFER = "money_transfer"
        UNKNOWN = "unknown"
    
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


@dataclass
class CommandMatch:
    """명령어 매칭 결과"""
    command_type: Optional[CommandType]
    command_instance: Optional[BaseCommand]
    confidence: float  # 0.0 ~ 1.0
    matched_keyword: str
    is_exact_match: bool


class CommandRouter:
    """
    최적화된 명령어 라우팅 클래스
    
    실시간 데이터 반영과 성능 최적화를 위해:
    - 캐시 의존성 제거
    - 효율적인 명령어 매칭
    - 스마트한 사용자 객체 관리
    - 최소한의 메모리 사용
    """
    
    def __init__(self, sheets_manager: Optional[SheetsManager] = None):
        """
        CommandRouter 초기화
        
        Args:
            sheets_manager: 최적화된 Google Sheets 관리자
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
        
        logger.info("최적화된 CommandRouter 초기화 완료")
    
    def _initialize_commands(self) -> None:
        """명령어 인스턴스들 초기화 (지연 로딩)"""
        try:
            # 명령어 매핑 테이블 (성능 최적화)
            self._command_mapping = {
                # 시스템 명령어
                '다이스': CommandType.DICE,
                'd': CommandType.DICE,
                '카드뽑기': CommandType.CARD,
                '카드': CommandType.CARD,
                '카드 뽑기': CommandType.CARD,
                'card': CommandType.CARD,
                '운세': CommandType.FORTUNE,
                'fortune': CommandType.FORTUNE,
                '도움말': CommandType.HELP,
                '도움': CommandType.HELP,
                'help': CommandType.HELP,
                
                # 게임 시스템 명령어
                '소지금': CommandType.MONEY,
                '돈': CommandType.MONEY,
                '재화': CommandType.MONEY,
                '금액': CommandType.MONEY,
                'money': CommandType.MONEY,
                
                '인벤토리': CommandType.INVENTORY,
                '소지품': CommandType.INVENTORY,
                '가방': CommandType.INVENTORY,
                '아이템': CommandType.INVENTORY,
                'inventory': CommandType.INVENTORY,
                'inv': CommandType.INVENTORY,
                
                '상점': CommandType.SHOP,
                '가게': CommandType.SHOP,
                '상가': CommandType.SHOP,
                'shop': CommandType.SHOP,
                'store': CommandType.SHOP,
                
                '구매': CommandType.BUY,
                '구입': CommandType.BUY,
                '사기': CommandType.BUY,
                'buy': CommandType.BUY,
                'purchase': CommandType.BUY,
                
                '양도': CommandType.TRANSFER,
                '전달': CommandType.TRANSFER,
                '주기': CommandType.TRANSFER,
                '넘기기': CommandType.TRANSFER,
                'transfer': CommandType.TRANSFER,
                'give': CommandType.TRANSFER,
                
                '송금': CommandType.MONEY_TRANSFER,
                '돈주기': CommandType.MONEY_TRANSFER,
                '재화양도': CommandType.MONEY_TRANSFER,
                'send_money': CommandType.MONEY_TRANSFER,
                'money_transfer': CommandType.MONEY_TRANSFER,
                
                '설명': CommandType.ITEM_DESCRIPTION,
                '정보': CommandType.ITEM_DESCRIPTION,
                '상세': CommandType.ITEM_DESCRIPTION,
                'info': CommandType.ITEM_DESCRIPTION,
                'desc': CommandType.ITEM_DESCRIPTION,
                'description': CommandType.ITEM_DESCRIPTION
            }
            
            logger.info(f"명령어 매핑 테이블 초기화 완료: {len(self._command_mapping)}개")
            
        except Exception as e:
            logger.error(f"명령어 초기화 실패: {e}")
            self._command_mapping = {}
    
    def route_command(self, user_id: str, keywords: List[str]) -> CommandResult:
        """
        사용자 명령어를 분석하여 적절한 명령어를 실행 (최적화)
        
        Args:
            user_id: 사용자 ID
            keywords: 명령어 키워드들
            
        Returns:
            CommandResult: 명령어 실행 결과
        """
        start_time = time.time()
        self._stats['total_routes'] += 1
        
        if not keywords:
            self._stats['failed_routes'] += 1
            return self._create_error_result(user_id, "명령어가 없습니다.")
        
        # 메시지 생성 (플러그인 명령어 매칭용)
        message = " ".join(keywords)
        
        # 플러그인 명령어 먼저 확인
        try:
            plugin_result = self._try_plugin_command(message, user_id)
            if plugin_result:
                self._stats['successful_routes'] += 1
                return plugin_result
        except Exception as e:
            logger.warning(f"플러그인 명령어 실행 중 오류: {e}")
        
        # 키워드 정규화 (최적화)
        normalized_keywords = self._normalize_keywords_fast(keywords)
        first_keyword = normalized_keywords[0].strip().lower()
        
        try:
            # 명령어 매칭 (최적화된 방식)
            match_result = self._match_command_fast(first_keyword, normalized_keywords)
            
            if not match_result.command_instance:
                self._stats['unknown_commands'] += 1
                return self._create_not_found_result(user_id, first_keyword)
            
            # User 객체 생성 (지연 로딩)
            user = self._get_user_lazy(user_id)
            
            # 명령어 실행
            logger.debug(f"라우팅: {first_keyword} -> {match_result.command_type}")
            
            with LogContext(
                operation="명령어 라우팅",
                user_id=user_id,
                command=first_keyword,
                confidence=match_result.confidence
            ):
                result = match_result.command_instance.execute(user, normalized_keywords)
                
                # 실행 시간 추가
                execution_time = time.time() - start_time
                if hasattr(result, 'execution_time') and result.execution_time:
                    result.execution_time += execution_time
                
                self._stats['successful_routes'] += 1
                return result
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"명령어 라우팅 중 오류: {e}")
            self._stats['failed_routes'] += 1
            return self._create_execution_error_result(user_id, first_keyword, e, execution_time)
    
    def _normalize_keywords_fast(self, keywords: List[str]) -> List[str]:
        """
        키워드 정규화 (성능 최적화)
        
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
                
            # 공백 제거
            clean_keyword = keyword.strip()
            if not clean_keyword:
                continue
            
            # 빠른 매핑 확인
            if clean_keyword in quick_normalize:
                normalized.append(quick_normalize[clean_keyword])
            else:
                # 기본 정규화
                normalized.append(clean_keyword)
        
        return normalized
    
    def _match_command_fast(self, first_keyword: str, keywords: List[str]) -> CommandMatch:
        """
        빠른 명령어 매칭 (최적화)
        
        Args:
            first_keyword: 첫 번째 키워드
            keywords: 전체 키워드 리스트
            
        Returns:
            CommandMatch: 매칭 결과
        """
        # 1. 직접 매핑 확인 (가장 빠름)
        if first_keyword in self._command_mapping:
            command_type = self._command_mapping[first_keyword]
            command_instance = self._get_command_instance(command_type)
            
            return CommandMatch(
                command_type=command_type,
                command_instance=command_instance,
                confidence=1.0,
                matched_keyword=first_keyword,
                is_exact_match=True
            )
        
        # 2. 다이스 표현식 직접 확인
        if self._is_dice_expression(first_keyword):
            command_instance = self._get_command_instance(CommandType.DICE)
            return CommandMatch(
                command_type=CommandType.DICE,
                command_instance=command_instance,
                confidence=0.9,
                matched_keyword=first_keyword,
                is_exact_match=False
            )
        
        # 3. 커스텀 명령어 확인 (마지막에)
        if self._is_custom_command_fast(first_keyword):
            command_instance = self._get_command_instance(CommandType.CUSTOM)
            return CommandMatch(
                command_type=CommandType.CUSTOM,
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
    
    def _get_command_instance(self, command_type: CommandType) -> Optional[BaseCommand]:
        """
        명령어 인스턴스 조회 (지연 로딩)
        
        Args:
            command_type: 명령어 타입
            
        Returns:
            Optional[BaseCommand]: 명령어 인스턴스
        """
        type_key = command_type
        
        # 캐시된 인스턴스 확인
        if type_key in self._command_instances:
            self._stats['cache_hits'] += 1
            return self._command_instances[type_key]
        
        # 새 인스턴스 생성 (지연 로딩)
        try:
            command_instance = self._create_command_instance(command_type)
            if command_instance:
                self._command_instances[type_key] = command_instance
                logger.debug(f"명령어 인스턴스 생성: {type_key}")
            return command_instance
            
        except Exception as e:
            logger.error(f"명령어 인스턴스 생성 실패: {type_key} - {e}")
            return None
    
    def _create_command_instance(self, command_type: CommandType) -> Optional[BaseCommand]:
        """
        명령어 타입에 따른 인스턴스 생성
        
        Args:
            command_type: 명령어 타입
            
        Returns:
            Optional[BaseCommand]: 생성된 인스턴스
        """
        try:
            # 동적 임포트 (필요할 때만)
            if command_type == CommandType.DICE:
                from commands.dice_command import DiceCommand
                return DiceCommand(self.sheets_manager)
            
            elif command_type == CommandType.CARD:
                from commands.card_command import CardCommand
                return CardCommand(self.sheets_manager)
            
            elif command_type == CommandType.FORTUNE:
                from commands.fortune_command import FortuneCommand
                return FortuneCommand(self.sheets_manager)
            
            elif command_type == CommandType.HELP:
                from commands.help_command import HelpCommand
                return HelpCommand(self.sheets_manager)
            
            elif command_type == CommandType.CUSTOM:
                from commands.custom_command import CustomCommand
                return CustomCommand(self.sheets_manager)
            
            # 게임 시스템 명령어들 (안전한 임포트)
            elif command_type == CommandType.MONEY:
                return self._safe_import_command('MoneyCommand')
            
            elif command_type == CommandType.INVENTORY:
                return self._safe_import_command('InventoryCommand')
            
            elif command_type == CommandType.SHOP:
                return self._safe_import_command('ShopCommand')
            
            elif command_type == CommandType.BUY:
                return self._safe_import_command('BuyCommand')
            
            elif command_type == CommandType.TRANSFER:
                return self._safe_import_command('TransferCommand')
            
            elif command_type == CommandType.MONEY_TRANSFER:
                return self._safe_import_command('MoneyTransferCommand')
            
            elif command_type == CommandType.ITEM_DESCRIPTION:
                return self._safe_import_command('ItemDescriptionCommand')
            
            else:
                logger.warning(f"알 수 없는 명령어 타입: {command_type}")
                return None
                
        except Exception as e:
            logger.error(f"명령어 인스턴스 생성 중 오류: {command_type} - {e}")
            return None
    
    def _safe_import_command(self, command_class_name: str) -> Optional[BaseCommand]:
        """
        안전한 명령어 클래스 임포트
        
        Args:
            command_class_name: 명령어 클래스 이름
            
        Returns:
            Optional[BaseCommand]: 명령어 인스턴스
        """
        try:
            # 모듈명 생성
            module_name = f"commands.{command_class_name.lower().replace('command', '_command')}"
            
            # 동적 임포트
            module = __import__(module_name, fromlist=[command_class_name])
            command_class = getattr(module, command_class_name)
            
            return command_class(self.sheets_manager)
            
        except (ImportError, AttributeError) as e:
            logger.warning(f"{command_class_name} 임포트 실패: {e}")
            return None
        except Exception as e:
            logger.error(f"{command_class_name} 인스턴스 생성 실패: {e}")
            return None
    
    def _get_user_lazy(self, user_id: str) -> User:
        """
        지연 로딩 방식으로 User 객체 생성
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            User: 사용자 객체 (항상 반환)
        """
        # 실시간 사용자 로드 (캐시 없음)
        if self.sheets_manager:
            try:
                user_data = self.sheets_manager.find_user_by_id_real_time(user_id)
                if user_data:
                    user = User.from_sheet_data(user_data)
                    if user.is_valid():
                        return user
            except Exception as e:
                logger.debug(f"사용자 로드 실패: {user_id} - {e}")
        
        # 실패하거나 시트 매니저가 없으면 빈 객체 반환
        return create_empty_user(user_id)
    
    def _is_dice_expression(self, keyword: str) -> bool:
        """
        다이스 표현식 여부 확인 (최적화)
        
        Args:
            keyword: 확인할 키워드
            
        Returns:
            bool: 다이스 표현식 여부
        """
        # 빠른 패턴 매칭
        if 'd' not in keyword.lower():
            return False
        
        # 정규식 검사 (최소화)
        dice_pattern = r'^\d+d\d+([+\-]\d+)?([<>]\d+)?$'
        return bool(re.match(dice_pattern, keyword.lower()))
    
    def _is_custom_command_fast(self, keyword: str) -> bool:
        """
        커스텀 명령어 여부 빠른 확인
        
        Args:
            keyword: 확인할 키워드
            
        Returns:
            bool: 커스텀 명령어 여부
        """
        # 시스템 키워드는 제외
        if keyword in self._command_mapping:
            return False
        
        # 시트에서 실시간 확인 (최소화)
        if not self.sheets_manager:
            return False
        
        try:
            # 간단한 확인만 수행
            custom_commands = self.sheets_manager.get_custom_commands_cached()
            return keyword in custom_commands
            
        except Exception as e:
            logger.debug(f"커스텀 명령어 확인 실패: {keyword} - {e}")
            return False
    
    def _create_error_result(self, user_id: str, error_message: str) -> CommandResult:
        """에러 결과 생성 (최적화)"""
        try:
            return CommandResult.error(
                command_type=CommandType.UNKNOWN,
                user_id=user_id,
                user_name=user_id,
                original_command="[알 수 없는 명령어]",
                error=Exception(error_message)
            )
        except Exception:
            # CommandResult 사용 불가 시 더미 반환
            class DummyResult:
                def __init__(self, message):
                    self.message = message
                def is_successful(self):
                    return False
                def get_user_message(self):
                    return self.message
            return DummyResult(error_message)
    
    def _create_not_found_result(self, user_id: str, keyword: str) -> CommandResult:
        """명령어를 찾을 수 없을 때의 친절한 오류 메시지"""
        try:
            # 조사 처리 (간단한 방식)
            from utils.text_processing import detect_korean_particle
            keyword_particle = detect_korean_particle(keyword, 'object')
            
            error_message = (
                f"[{keyword}] 명령어{keyword_particle} 찾을 수 없습니다.\n"
                f"사용 가능한 명령어는 [도움말]{detect_korean_particle('도움말', 'object')} "
                f"입력해서 확인해주세요."
            )
            
        except ImportError:
            # 텍스트 처리 모듈이 없는 경우
            error_message = (
                f"[{keyword}] 명령어를 찾을 수 없습니다.\n"
                f"사용 가능한 명령어는 [도움말]을 입력해서 확인해주세요."
            )
        
        return self._create_error_result(user_id, error_message)
    
    def _try_plugin_command(self, message: str, user_id: str) -> Optional[CommandResult]:
        """
        플러그인 명령어 실행 시도
        
        Args:
            message: 원본 메시지
            user_id: 사용자 ID
            
        Returns:
            CommandResult 또는 None (플러그인 명령어가 아닌 경우)
        """
        try:
            # 플러그인 시스템이 사용 가능한지 확인
            if not plugin_command_registry or not PLUGIN_SYSTEM_AVAILABLE:
                return None
            
            # 플러그인 명령어 레지스트리에서 명령어 찾기
            result = plugin_command_registry.find_command(message)
            if not result:
                return None
            
            handler, match_info = result
            
            # 사용자 정보 가져오기
            user = self._get_user_lazy(user_id)
            
            # 플러그인 명령어 실행
            plugin_result = handler.plugin.execute(match_info)
            
            if plugin_result:
                # CommandResult로 변환
                return CommandResult.success(
                    user_id=user_id,
                    command_type=CommandType.CUSTOM,  # 플러그인은 CUSTOM으로 분류
                    result=plugin_result,
                    execution_time=0.0  # 플러그인에서 처리
                )
            
            return None
            
        except Exception as e:
            logger.error(f"플러그인 명령어 실행 오류: {e}")
            return None
    
    def _create_execution_error_result(self, user_id: str, keyword: str, error: Exception, 
                                     execution_time: float) -> CommandResult:
        """명령어 실행 오류 결과 생성"""
        try:
            from utils.text_processing import detect_korean_particle
            keyword_particle = detect_korean_particle(keyword, 'subject')
            error_message = f"[{keyword}] 명령어{keyword_particle} 실행 중 오류가 발생했습니다."
            
        except ImportError:
            error_message = f"[{keyword}] 명령어 실행 중 오류가 발생했습니다."
        
        try:
            return CommandResult.error(
                command_type=CommandType.UNKNOWN,
                user_id=user_id,
                user_name=user_id,
                original_command=f"[{keyword}]",
                error=Exception(error_message),
                execution_time=execution_time
            )
        except Exception:
            return self._create_error_result(user_id, error_message)
    
    def get_command_statistics(self) -> Dict[str, Any]:
        """
        명령어 라우터 통계 반환 (최적화)
        
        Returns:
            Dict: 라우터 통계 정보
        """
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
    
    def get_command_mapping_info(self) -> Dict[str, Any]:
        """
        명령어 매핑 정보 반환
        
        Returns:
            Dict: 매핑 정보
        """
        # 타입별 키워드 그룹화
        type_groups = {}
        for keyword, cmd_type in self._command_mapping.items():
            type_name = cmd_type
            if type_name not in type_groups:
                type_groups[type_name] = []
            type_groups[type_name].append(keyword)
        
        return {
            'total_mappings': len(self._command_mapping),
            'type_groups': type_groups,
            'initialized_instances': list(self._command_instances.keys())
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
                health_status['status'] = 'warning' if health_status['status'] == 'healthy' else health_status['status']
            
            # 통계 확인
            stats = self.get_command_statistics()
            health_status['details']['statistics'] = stats
            
            # 성능 지표 확인
            if stats['total_routes'] > 0:
                if stats['success_rate'] < 80:  # 80% 미만 성공률
                    health_status['warnings'].append(f"낮은 성공률: {stats['success_rate']:.1f}%")
                    health_status['status'] = 'warning' if health_status['status'] == 'healthy' else health_status['status']
                
                if stats['unknown_commands'] / stats['total_routes'] > 0.3:  # 30% 이상 알 수 없는 명령어
                    health_status['warnings'].append("알 수 없는 명령어 비율이 높습니다")
                    health_status['status'] = 'warning' if health_status['status'] == 'healthy' else health_status['status']
            
            # 인스턴스 상태 확인
            health_status['details']['instance_health'] = {}
            for type_key, instance in self._command_instances.items():
                try:
                    if hasattr(instance, 'health_check'):
                        instance_health = instance.health_check()
                        health_status['details']['instance_health'][type_key] = instance_health
                        
                        if instance_health['status'] != 'healthy':
                            health_status['warnings'].append(f"{type_key} 명령어에 문제가 있습니다")
                            health_status['status'] = 'warning' if health_status['status'] == 'healthy' else health_status['status']
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
        self._stats = {
            'total_routes': 0,
            'successful_routes': 0,
            'failed_routes': 0,
            'cache_hits': 0,
            'unknown_commands': 0,
            'start_time': time.time()
        }
        logger.info("라우터 통계 초기화")
    
    def clear_command_cache(self) -> int:
        """명령어 인스턴스 캐시 정리"""
        count = len(self._command_instances)
        self._command_instances.clear()
        logger.info(f"명령어 인스턴스 캐시 정리: {count}개")
        return count


class SimpleCommandRouter:
    """
    간단한 명령어 라우터 (기존 코드와의 호환성용)
    """
    
    def __init__(self, sheets_manager: Optional[SheetsManager] = None):
        """SimpleCommandRouter 초기화"""
        self.router = CommandRouter(sheets_manager)
    
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
            result = self.router.route_command(user_id, keywords)
            
            if result and hasattr(result, 'is_successful') and hasattr(result, 'get_user_message'):
                return result.get_user_message(), None
            else:
                return "명령어 처리 중 오류가 발생했습니다.", None
                
        except Exception as e:
            logger.error(f"SimpleCommandRouter 오류: {e}")
            return "명령어 처리 중 오류가 발생했습니다.", None


# 전역 라우터 인스턴스
_global_router: Optional[CommandRouter] = None


def get_command_router() -> CommandRouter:
    """전역 명령어 라우터 반환"""
    global _global_router
    if _global_router is None:
        _global_router = CommandRouter()
    return _global_router


def initialize_command_router(sheets_manager: Optional[SheetsManager]) -> CommandRouter:
    """
    명령어 라우터 초기화
    
    Args:
        sheets_manager: 최적화된 Google Sheets 관리자
        
    Returns:
        CommandRouter: 초기화된 라우터
    """
    global _global_router
    _global_router = CommandRouter(sheets_manager)
    logger.info("전역 명령어 라우터 초기화 완료")
    return _global_router


def route_command(user_id: str, keywords: List[str]) -> CommandResult:
    """
    편의 함수: 명령어 라우팅 실행
    
    Args:
        user_id: 사용자 ID
        keywords: 키워드 리스트
        
    Returns:
        CommandResult: 실행 결과
    """
    router = get_command_router()
    return router.route_command(user_id, keywords)


def parse_command_from_text(text: str) -> List[str]:
    """
    텍스트에서 명령어 키워드 추출 (최적화)
    
    Args:
        text: 분석할 텍스트 (예: "[다이스/2d6] 안녕하세요")
        
    Returns:
        List[str]: 추출된 키워드들 (예: ['다이스', '2d6'])
    """
    if not text:
        return []
    
    # 빠른 패턴 매칭
    match = re.search(r'\[([^\]]+)\]', text)
    if not match:
        return []
    
    keywords_str = match.group(1)
    if not keywords_str:
        return []
    
    # 키워드 분할 (최적화)
    keywords = []
    for keyword in keywords_str.split('/'):
        clean_keyword = keyword.strip()
        if clean_keyword:
            keywords.append(clean_keyword)
    
    return keywords


def validate_command_format(text: str) -> Tuple[bool, str]:
    """
    명령어 형식 유효성 검사 (최적화)
    
    Args:
        text: 검사할 텍스트
        
    Returns:
        Tuple[bool, str]: (유효성, 메시지)
    """
    if not text:
        return False, "텍스트가 비어있습니다."
    
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


# 성능 모니터링 및 최적화 함수들
def get_router_performance_report() -> str:
    """
    라우터 성능 리포트 생성
    
    Returns:
        str: 성능 리포트
    """
    try:
        router = get_command_router()
        stats = router.get_command_statistics()
        health = router.health_check()
        mapping_info = router.get_command_mapping_info()
        
        report_lines = ["=== 명령어 라우터 성능 리포트 ==="]
        
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
        
        # 최적화 정보
        report_lines.append(f"\n✅ 적용된 최적화:")
        report_lines.append(f"  - 빠른 키워드 매핑 테이블")
        report_lines.append(f"  - 지연 로딩 명령어 인스턴스")
        report_lines.append(f"  - 효율적인 다이스 표현식 검사")
        report_lines.append(f"  - 실시간 사용자 로드")
        report_lines.append(f"  - 최소화된 통계 수집")
        
        return "\n".join(report_lines)
        
    except Exception as e:
        return f"라우터 성능 리포트 생성 실패: {e}"


def optimize_router_performance():
    """라우터 성능 최적화 실행"""
    try:
        router = get_command_router()
        
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


def benchmark_router_performance(iterations: int = 1000) -> Dict[str, float]:
    """
    라우터 성능 벤치마크
    
    Args:
        iterations: 반복 횟수
        
    Returns:
        Dict: 벤치마크 결과
    """
    router = get_command_router()
    
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


# 라우터 테스트 함수
def test_command_routing():
    """명령어 라우팅 테스트"""
    print("=== 최적화된 명령어 라우팅 테스트 ===")
    
    test_cases = [
        (['다이스', '2d6'], 'DICE'),
        (['2d6'], 'DICE'),
        (['카드뽑기', '5장'], 'CARD'),
        (['카드 뽑기', '3장'], 'CARD'),
        (['운세'], 'FORTUNE'),
        (['도움말'], 'HELP'),
        (['소지금'], 'MONEY'),
        (['인벤토리'], 'INVENTORY'),
        (['상점'], 'SHOP'),
        (['구매', '포션', '5개'], 'BUY'),
        (['양도', '검', '@user2'], 'TRANSFER'),
        (['unknown'], 'UNKNOWN'),
    ]
    
    router = CommandRouter()
    
    for keywords, expected_type in test_cases:
        try:
            start_time = time.time()
            match_result = router._match_command_fast(keywords[0], keywords)
            end_time = time.time()
            
            actual_type = match_result.command_type if match_result.command_type else 'UNKNOWN'
            confidence = match_result.confidence
            execution_time = (end_time - start_time) * 1000  # ms
            
            status = "✅" if actual_type == expected_type else "❌"
            print(f"{status} {keywords} -> {actual_type} (예상: {expected_type}) "
                  f"신뢰도: {confidence:.2f}, 시간: {execution_time:.3f}ms")
            
        except Exception as e:
            print(f"❌ {keywords} -> 오류: {e}")
    
    # 성능 통계
    stats = router.get_command_statistics()
    print(f"\n📊 테스트 통계:")
    print(f"  총 라우팅: {stats['total_routes']}회")
    print(f"  성공률: {stats['success_rate']:.1f}%")
    print(f"  캐시 히트율: {stats['cache_hit_rate']:.1f}%")
    
    print("=" * 60)


def test_korean_particles_in_router():
    """라우터에서 한글 조사 처리 테스트"""
    print("\n=== 라우터 한글 조사 처리 테스트 ===")
    
    router = CommandRouter()
    test_user = "test_user"
    
    # 존재하지 않는 명령어들로 테스트
    unknown_commands = ['검', '방패', '포션', '마법', '물약']
    
    for command in unknown_commands:
        try:
            result = router._create_not_found_result(test_user, command)
            if hasattr(result, 'get_user_message'):
                print(f"'{command}' -> {result.get_user_message()}")
            else:
                print(f"'{command}' -> {result.message}")
        except Exception as e:
            print(f"'{command}' -> 오류: {e}")
    
    print("=" * 60)


def test_performance_optimization():
    """성능 최적화 테스트"""
    print("\n=== 성능 최적화 테스트 ===")
    
    try:
        # 벤치마크 실행
        print("1. 라우터 벤치마크 실행 중...")
        benchmark_results = benchmark_router_performance(100)  # 100회로 축소
        
        print("2. 벤치마크 결과:")
        for test_name, result in benchmark_results.items():
            print(f"   {test_name}:")
            print(f"     평균 시간: {result['avg_time']*1000:.3f}ms")
            print(f"     초당 처리: {result['ops_per_second']:.0f}회")
        
        # 성능 최적화 실행
        print("\n3. 성능 최적화 실행...")
        optimize_router_performance()
        
        # 최적화 후 성능 리포트
        print("\n4. 최적화 후 상태:")
        router = get_command_router()
        health = router.health_check()
        print(f"   상태: {health['status']}")
        print(f"   경고: {len(health['warnings'])}개")
        print(f"   오류: {len(health['errors'])}개")
        
        print("\n✅ 성능 최적화 테스트 완료")
        
    except Exception as e:
        print(f"❌ 성능 테스트 실패: {e}")
    
    print("=" * 60)


# 호환성을 위한 별칭
CommandRouter = CommandRouter


# 모듈 로드 완료 로깅
logger.info("최적화된 명령어 라우터 모듈 로드 완료")


# 테스트 실행 (개발 환경에서만)
if __name__ == "__main__":
    test_command_routing()
    test_korean_particles_in_router()
    test_performance_optimization()
    
    # 성능 리포트 출력
    print("\n" + get_router_performance_report())