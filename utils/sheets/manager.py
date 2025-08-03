"""
Google Sheets 통합 관리자 모듈
모든 컴포넌트를 조율하는 메인 관리자입니다.
"""

import time
from typing import List, Dict, Any, Optional
from config.settings import config

from .interfaces import SheetsConnection, SheetsCache, SheetsOperations, PerformanceMonitor
from .connection import GoogleSheetsConnection
from .cache import SheetsCacheManager, TimeBasedCacheStrategy, NoCacheStrategy
from .operations import GoogleSheetsOperations
from .performance import SheetsPerformanceMonitor
from utils.logging_config import logger


class SheetsManager:
    """Google Sheets 통합 관리자"""
    
    _instance = None
    
    def __init__(self, sheet_name: str = None, credentials_path: str = None):
        # 설정 초기화
        self.sheet_name = sheet_name or config.SHEET_NAME
        self.credentials_path = credentials_path or config.get_credentials_path()
        
        # 컴포넌트 초기화
        self.connection = GoogleSheetsConnection(self.sheet_name, self.credentials_path)
        self.operations = GoogleSheetsOperations(self.connection)
        self.performance = SheetsPerformanceMonitor()
        
        # 캐시 전략 선택 (실시간 데이터를 위해 NoCache 기본 사용)
        cache_strategy = NoCacheStrategy()
        self.cache = SheetsCacheManager(cache_strategy)
        
        logger.info("SheetsManager 초기화 완료")
    
    @classmethod
    def get_instance(cls, **kwargs) -> 'SheetsManager':
        """싱글톤 인스턴스 반환"""
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance
    
    def read_worksheet_real_time(self, name: str) -> List[Dict[str, Any]]:
        """실시간 워크시트 읽기 (캐시 없음)"""
        start_time = time.time()
        
        try:
            result = self.operations.read_worksheet(name)
            duration = time.time() - start_time
            self.performance.record_operation("read_worksheet", duration)
            return result
        except Exception as e:
            self.performance.record_error()
            # 워크시트가 존재하지 않는 경우
            if "워크시트" in str(e) and "찾을 수 없습니다" in str(e):
                logger.warning(f"워크시트 '{name}'이 존재하지 않습니다.")
                return []
            else:
                logger.error(f"워크시트 읽기 실패: {name} - {e}")
                return []
    
    def append_row_real_time(self, worksheet_name: str, values: List[Any]) -> bool:
        """실시간 행 추가"""
        start_time = time.time()
        
        try:
            result = self.operations.append_row(worksheet_name, values)
            duration = time.time() - start_time
            self.performance.record_operation("append_row", duration)
            return result
        except Exception as e:
            self.performance.record_error()
            logger.error(f"행 추가 실패: {worksheet_name} - {e}")
            return False
    
    def update_cell_real_time(self, worksheet_name: str, row: int, col: int, value: Any) -> bool:
        """실시간 셀 업데이트"""
        start_time = time.time()
        
        try:
            result = self.operations.update_cell(worksheet_name, row, col, value)
            duration = time.time() - start_time
            self.performance.record_operation("update_cell", duration)
            return result
        except Exception as e:
            self.performance.record_error()
            logger.error(f"셀 업데이트 실패: {worksheet_name} - {e}")
            return False
    
    def find_user_by_id_real_time(self, user_id: str) -> Optional[Dict[str, Any]]:
        """실시간 사용자 조회"""
        return self.operations.find_user_by_id(user_id, config.get_worksheet_name('ROSTER'))
    
    def user_exists_real_time(self, user_id: str) -> bool:
        """실시간 사용자 존재 확인"""
        return self.operations.user_exists(user_id, config.get_worksheet_name('ROSTER'))
    
    def log_action_real_time(self, user_name: str, command: str, message: str, success: bool = True) -> bool:
        """실시간 로그 기록"""
        try:
            return self.operations.log_action(
                config.get_worksheet_name('LOG'),
                user_name, command, message, success
            )
        except Exception as e:
            # 로그 워크시트가 없거나 접근할 수 없는 경우
            logger.warning(f"로그 기록 실패 (워크시트 접근 불가): {e}")
            return True  # 로그 실패해도 봇 동작에는 영향 없음
    
    def get_custom_commands_cached(self) -> Dict[str, List[str]]:
        """커스텀 명령어 조회 (캐시 적용)"""
        cache_key = "custom_commands"
        cached = self.cache.get(cache_key)
        
        if cached is not None:
            return cached
        
        # 실시간 데이터 조회
        custom_data = self.read_worksheet_real_time(config.get_worksheet_name('CUSTOM'))
        commands = {}
        
        for row in custom_data:
            command = str(row.get('명령어', '')).strip()
            phrase = str(row.get('문구', '')).strip()
            
            if command and phrase:
                if command not in commands:
                    commands[command] = []
                commands[command].append(phrase)
        
        # 1시간 캐시
        self.cache.set(cache_key, commands, ttl=3600)
        return commands
    
    def get_help_items_with_cache(self) -> List[Dict[str, str]]:
        """도움말 항목 조회 (캐시 적용)"""
        cache_key = "help_items"
        cached = self.cache.get(cache_key)
        
        if cached is not None:
            return cached
        
        # 실시간 데이터 조회
        help_data = self.read_worksheet_real_time(config.get_worksheet_name('HELP'))
        help_items = []
        
        for row in help_data:
            command = str(row.get('명령어', '')).strip()
            description = str(row.get('설명', '')).strip()
            
            if command and description:
                help_items.append({'명령어': command, '설명': description})
        
        # 1시간 캐시
        self.cache.set(cache_key, help_items, ttl=3600)
        return help_items
    
    def get_fortune_phrases_with_cache(self) -> List[str]:
        """운세 문구 조회 (캐시 적용)"""
        cache_key = "fortune_phrases"
        cached = self.cache.get(cache_key)
        
        if cached is not None:
            return cached
        
        # 실시간 데이터 조회
        fortune_data = self.read_worksheet_real_time(config.get_worksheet_name('FORTUNE'))
        phrases = []
        
        for row in fortune_data:
            phrase = str(row.get('문구', '')).strip()
            if phrase:
                phrases.append(phrase)
        
        # 1시간 캐시
        self.cache.set(cache_key, phrases, ttl=3600)
        return phrases
    
    def invalidate_cached_content(self, content_type: str = None) -> bool:
        """캐시 무효화"""
        if content_type == 'fortune' or content_type is None:
            self.cache.invalidate("fortune_phrases")
        
        if content_type == 'help' or content_type is None:
            self.cache.invalidate("help_items")
        
        if content_type == 'custom' or content_type is None:
            self.cache.invalidate("custom_commands")
        
        logger.info(f"캐시 무효화 완료: {content_type or '전체'}")
        return True
    
    def get_fortune_phrases(self) -> List[str]:
        """운세 문구 목록 조회 (실시간)"""
        try:
            worksheet_name = config.get_worksheet_name('FORTUNE')
            data = self.read_worksheet_real_time(worksheet_name)
            
            if not data:
                return []
            
            # 운세 문구 추출
            fortune_phrases = []
            for row in data:
                if isinstance(row, dict):
                    phrase = str(row.get('문구', '')).strip()
                else:
                    # 리스트 형태인 경우 첫 번째 요소 사용
                    phrase = str(row[0] if len(row) > 0 else '').strip()
                
                if phrase:
                    fortune_phrases.append(phrase)
            
            return fortune_phrases
            
        except Exception as e:
            logger.error(f"운세 문구 조회 실패: {e}")
            return []
    
    def get_help_items(self) -> List[Dict[str, str]]:
        """도움말 항목 조회 (실시간)"""
        try:
            worksheet_name = config.get_worksheet_name('HELP')
            data = self.read_worksheet_real_time(worksheet_name)
            
            if not data:
                return []
            
            # 도움말 항목 추출
            help_items = []
            for row in data:
                if isinstance(row, dict):
                    command = str(row.get('명령어', '')).strip()
                    description = str(row.get('설명', '')).strip()
                else:
                    # 리스트 형태인 경우 첫 번째와 두 번째 요소 사용
                    command = str(row[0] if len(row) > 0 else '').strip()
                    description = str(row[1] if len(row) > 1 else '').strip()
                
                if command and description:
                    help_items.append({
                        'command': command,
                        'description': description
                    })
            
            return help_items
            
        except Exception as e:
            logger.error(f"도움말 항목 조회 실패: {e}")
            return []
    
    def batch_read_worksheets(self, worksheet_names: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """여러 워크시트 배치 읽기"""
        start_time = time.time()
        results = {}
        
        try:
            for worksheet_name in worksheet_names:
                try:
                    data = self.read_worksheet_real_time(worksheet_name)
                    results[worksheet_name] = data
                except Exception as e:
                    logger.warning(f"배치 읽기 실패: {worksheet_name} - {e}")
                    results[worksheet_name] = []
            
            duration = time.time() - start_time
            self.performance.record_operation("batch_read", duration)
            
            logger.info(f"배치 읽기 완료: {len(worksheet_names)}개 시트")
            return results
            
        except Exception as e:
            self.performance.record_error()
            logger.error(f"배치 읽기 실패: {e}")
            return {}
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        perf_stats = self.performance.get_stats()
        cache_stats = self.cache.get_stats()
        connection_health = self.connection.health_check()
        
        return {
            **perf_stats,
            **cache_stats,
            'connection_status': connection_health['status'],
            'connection_title': connection_health.get('title', 'N/A')
        }
    
    def health_check(self) -> Dict[str, Any]:
        """전체 상태 확인"""
        perf_health = self.performance.health_check()
        connection_health = self.connection.health_check()
        cache_stats = self.cache.get_stats()
        
        health_status = {
            'status': 'healthy',
            'warnings': [],
            'errors': [],
            'details': {
                'performance': perf_health,
                'connection': connection_health,
                'cache': cache_stats
            }
        }
        
        # 상태 통합
        if perf_health['status'] != 'healthy':
            health_status['status'] = perf_health['status']
            health_status['warnings'].extend(perf_health['warnings'])
        
        if connection_health['status'] != 'connected':
            health_status['status'] = 'error'
            health_status['errors'].append(f"연결 오류: {connection_health.get('error', 'Unknown')}")
        
        return health_status
    
    def cleanup(self) -> None:
        """정리 작업"""
        # 캐시 정리
        expired_count = self.cache.cleanup()
        if expired_count > 0:
            logger.info(f"만료된 캐시 {expired_count}개 정리")
        
        # 성능 통계 리셋 (선택사항)
        stats = self.performance.get_stats()
        if stats['api_calls_total'] > 10000:
            self.performance.reset_stats()
            logger.info("성능 통계 리셋 완료")
    
    def get_performance_report(self) -> str:
        """성능 리포트 생성"""
        return self.performance.get_performance_report()
    
    def validate_sheet_structure(self) -> Dict[str, Any]:
        """시트 구조 검증"""
        try:
            result = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'worksheets_found': []
            }
            
            # 기본 워크시트 목록 확인
            expected_worksheets = [
                config.get_worksheet_name('ROSTER'),
                config.get_worksheet_name('FORTUNE'),
                config.get_worksheet_name('HELP'),
                config.get_worksheet_name('CUSTOM')
            ]
            
            # 선택사항 워크시트 (없어도 오류 아님)
            optional_worksheets = [
                config.get_worksheet_name('LOG')
            ]
            
            # 필수 워크시트 확인
            for worksheet_name in expected_worksheets:
                try:
                    # 워크시트 읽기 시도
                    data = self.read_worksheet_real_time(worksheet_name)
                    if data is not None:
                        result['worksheets_found'].append(worksheet_name)
                    else:
                        result['warnings'].append(f"워크시트 '{worksheet_name}'이 비어있습니다")
                except Exception as e:
                    result['errors'].append(f"워크시트 '{worksheet_name}' 접근 실패: {str(e)}")
                    result['valid'] = False
            
            # 선택사항 워크시트 확인
            for worksheet_name in optional_worksheets:
                try:
                    # 워크시트 읽기 시도
                    data = self.read_worksheet_real_time(worksheet_name)
                    if data is not None:
                        result['worksheets_found'].append(worksheet_name)
                    else:
                        result['warnings'].append(f"선택사항 워크시트 '{worksheet_name}'이 비어있습니다")
                except Exception as e:
                    result['warnings'].append(f"선택사항 워크시트 '{worksheet_name}' 접근 실패: {str(e)}")
                    # 선택사항이므로 오류로 처리하지 않음
            
            # 최소 필수 워크시트 확인
            if len(result['worksheets_found']) < 2:
                result['errors'].append("최소 2개 이상의 워크시트가 필요합니다")
                result['valid'] = False
            
            return result
            
        except Exception as e:
            return {
                'valid': False,
                'errors': [f"시트 구조 검증 중 오류 발생: {str(e)}"],
                'warnings': [],
                'worksheets_found': []
            }


# 편의 함수들 (기존 코드와의 호환성)
def get_sheets_manager() -> SheetsManager:
    """전역 SheetsManager 인스턴스 반환"""
    return SheetsManager.get_instance()


def get_real_time_user_data(user_id: str) -> Optional[Dict[str, Any]]:
    """실시간 사용자 데이터 조회"""
    manager = get_sheets_manager()
    return manager.find_user_by_id_real_time(user_id)


def get_real_time_worksheet_data(worksheet_name: str) -> List[Dict[str, Any]]:
    """실시간 워크시트 데이터 조회"""
    manager = get_sheets_manager()
    return manager.read_worksheet_real_time(worksheet_name)


def log_real_time_action(user_name: str, command: str, message: str, success: bool = True) -> bool:
    """실시간 로그 기록"""
    manager = get_sheets_manager()
    return manager.log_action_real_time(user_name, command, message, success)


def batch_read_multiple_sheets(worksheet_names: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """여러 시트 배치 읽기"""
    manager = get_sheets_manager()
    return manager.batch_read_worksheets(worksheet_names)


def invalidate_sheet_cache(content_type: str = None) -> bool:
    """시트 관련 캐시 무효화"""
    manager = get_sheets_manager()
    return manager.invalidate_cached_content(content_type) 