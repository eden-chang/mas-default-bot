"""
Google Sheets 작업 모듈 (리팩토링된 버전)
기존 코드와의 호환성을 위한 브리지 모듈
"""

# 새로운 모듈 구조로 리다이렉트
from .sheets import (
    SheetsManager,
    get_sheets_manager
)

# 편의 함수들
def get_real_time_user_data(user_id: str):
    """실시간 사용자 데이터 조회"""
    manager = get_sheets_manager()
    return manager.find_user_by_id_real_time(user_id)


def get_real_time_worksheet_data(worksheet_name: str):
    """실시간 워크시트 데이터 조회"""
    manager = get_sheets_manager()
    return manager.read_worksheet_real_time(worksheet_name)


def log_real_time_action(user_name: str, command: str, message: str, success: bool = True) -> bool:
    """실시간 로그 기록"""
    manager = get_sheets_manager()
    return manager.log_action_real_time(user_name, command, message, success)


def batch_read_multiple_sheets(worksheet_names):
    """여러 시트 배치 읽기"""
    manager = get_sheets_manager()
    return manager.batch_read_worksheets(worksheet_names)


def invalidate_sheet_cache(content_type: str = None) -> bool:
    """시트 관련 캐시 무효화"""
    manager = get_sheets_manager()
    return manager.invalidate_cached_content(content_type)

# 기존 코드와의 호환성을 위한 별칭
def connect_to_sheet(sheet_name: str = None, credentials_file: str = None):
    """기존 connect_to_sheet 함수 호환성 유지"""
    manager = get_sheets_manager()
    return manager.connection.connect()


def user_id_check(sheet, user_id: str) -> bool:
    """기존 user_id_check 함수 호환성 유지"""
    try:
        if isinstance(sheet, SheetsManager):
            return sheet.user_exists_real_time(user_id)
        
        manager = get_sheets_manager()
        return manager.user_exists_real_time(user_id)
    except Exception:
        return False


def get_user_data_safe(sheet, user_id: str):
    """기존 get_user_data_safe 함수 호환성 유지"""
    try:
        if isinstance(sheet, SheetsManager):
            return sheet.find_user_by_id_real_time(user_id)
        
        manager = get_sheets_manager()
        return manager.find_user_by_id_real_time(user_id)
    except Exception:
        return None


def get_worksheet_data_safe(sheet, worksheet_name: str):
    """기존 get_worksheet_data_safe 함수 호환성 유지"""
    try:
        if isinstance(sheet, SheetsManager):
            return sheet.read_worksheet_real_time(worksheet_name)
        
        manager = get_sheets_manager()
        return manager.read_worksheet_real_time(worksheet_name)
    except Exception:
        return []


def log_action(sheet, user_name: str, command: str, message: str, success: bool = True) -> bool:
    """기존 log_action 함수 호환성 유지"""
    try:
        if isinstance(sheet, SheetsManager):
            return sheet.log_action_real_time(user_name, command, message, success)
        
        manager = get_sheets_manager()
        return manager.log_action_real_time(user_name, command, message, success)
    except Exception:
        from utils.logging_config import logger
        logger.warning(f"시트 로그 실패: {user_name} | {command} | {message[:50]}... | {'성공' if success else '실패'}")
        return False


def find_worksheet_safe(sheet, worksheet_name: str):
    """기존 find_worksheet_safe 함수 호환성 유지"""
    try:
        if isinstance(sheet, SheetsManager):
            return sheet.find_worksheet(worksheet_name)
        
        manager = get_sheets_manager()
        return manager.find_worksheet(worksheet_name)
    except Exception:
        return None


def read_sheet_data(worksheet_name: str):
    """시트 데이터 읽기 (백워드 호환성)"""
    try:
        manager = get_sheets_manager()
        return manager.read_worksheet_real_time(worksheet_name)
    except Exception as e:
        from utils.logging_config import logger
        logger.error(f"시트 데이터 읽기 실패: {worksheet_name} - {e}")
        return []


def write_sheet_data(worksheet_name: str, data):
    """시트 데이터 쓰기 (백워드 호환성)"""
    try:
        manager = get_sheets_manager()
        return manager.write_worksheet_real_time(worksheet_name, data)
    except Exception as e:
        from utils.logging_config import logger
        logger.error(f"시트 데이터 쓰기 실패: {worksheet_name} - {e}")
        return False


def update_sheet_data(worksheet_name: str, data):
    """시트 데이터 업데이트 (백워드 호환성)"""
    try:
        manager = get_sheets_manager()
        return manager.update_worksheet_real_time(worksheet_name, data)
    except Exception as e:
        from utils.logging_config import logger
        logger.error(f"시트 데이터 업데이트 실패: {worksheet_name} - {e}")
        return False
    try:
        if isinstance(sheet, SheetsManager):
            return sheet.connection.get_worksheet(worksheet_name)
        manager = get_sheets_manager()
        return manager.connection.get_worksheet(worksheet_name)
    except Exception:
        return None


# 성능 모니터링 함수들
def get_sheets_performance_report() -> str:
    """시트 성능 리포트 생성"""
    manager = get_sheets_manager()
    return manager.get_performance_report()


def test_sheets_operations():
    """시트 작업 테스트"""
    print("=== 리팩토링된 Google Sheets 작업 테스트 ===")
    
    try:
        manager = get_sheets_manager()
        
        # 연결 테스트
        print("1. 스프레드시트 연결 테스트...")
        spreadsheet = manager.connection.connect()
        print(f"   ✅ 연결 성공: {spreadsheet.title}")
        
        # 실시간 데이터 조회 테스트
        print("\n2. 실시간 데이터 조회 테스트...")
        roster_data = manager.read_worksheet_real_time("명단")
        print(f"   ✅ 사용자 데이터: {len(roster_data)}개")
        
        # 캐시된 데이터 조회 테스트
        print("\n3. 캐시된 데이터 조회 테스트...")
        help_items = manager.get_help_items_with_cache()
        print(f"   ✅ 도움말 항목: {len(help_items)}개")
        
        fortune_phrases = manager.get_fortune_phrases_with_cache()
        print(f"   ✅ 운세 문구: {len(fortune_phrases)}개")
        
        # 성능 통계
        print("\n4. 성능 통계:")
        stats = manager.get_performance_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        # 상태 확인
        print("\n5. 상태 확인:")
        health = manager.health_check()
        print(f"   상태: {health['status']}")
        if health['warnings']:
            print(f"   경고: {', '.join(health['warnings'])}")
        
        print("\n✅ 모든 테스트 완료")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
    
    print("=" * 50)


def validate_real_time_data_consistency():
    """실시간 데이터 일관성 검증"""
    print("=== 실시간 데이터 일관성 검증 ===")
    
    try:
        manager = get_sheets_manager()
        
        # 여러 번 조회하여 일관성 확인
        print("1. 데이터 일관성 테스트...")
        
        # 첫 번째 조회
        data1 = manager.read_worksheet_real_time("명단")
        print(f"   첫 번째 조회: {len(data1)}개 사용자")
        
        # 두 번째 조회 (즉시)
        data2 = manager.read_worksheet_real_time("명단")
        print(f"   두 번째 조회: {len(data2)}개 사용자")
        
        # 일관성 확인
        if len(data1) == len(data2):
            print("   ✅ 데이터 일관성 유지됨")
        else:
            print("   ❌ 데이터 불일치 발생")
        
        # 캐시 vs 실시간 비교
        print("\n2. 캐시 vs 실시간 데이터 비교...")
        
        # 캐시된 도움말 (첫 번째 호출)
        help1 = manager.get_help_items_with_cache()
        print(f"   캐시된 도움말 (첫 호출): {len(help1)}개")
        
        # 캐시된 도움말 (두 번째 호출, 캐시에서 가져옴)
        help2 = manager.get_help_items_with_cache()
        print(f"   캐시된 도움말 (두 번째): {len(help2)}개")
        
        if help1 == help2:
            print("   ✅ 캐시 일관성 유지됨")
        else:
            print("   ❌ 캐시 불일치 발생")
        
        print("\n✅ 일관성 검증 완료")
        
    except Exception as e:
        print(f"❌ 검증 실패: {e}")
    
    print("=" * 50)


# 모듈 초기화
if __name__ == "__main__":
    test_sheets_operations()
    validate_real_time_data_consistency()