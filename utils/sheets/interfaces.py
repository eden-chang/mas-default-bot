"""
Google Sheets 작업 인터페이스 정의
명확한 계약과 타입 안전성을 보장합니다.
"""

from abc import ABC, abstractmethod
from typing import Protocol, List, Dict, Any, Optional
import gspread


class SheetsConnection(Protocol):
    """스프레드시트 연결 인터페이스"""
    
    def connect(self) -> gspread.Spreadsheet:
        """스프레드시트에 연결"""
        ...
    
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        ...
    
    def disconnect(self) -> None:
        """연결 해제"""
        ...


class SheetsCache(Protocol):
    """캐시 관리 인터페이스"""
    
    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        ...
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """캐시에 값 저장"""
        ...
    
    def invalidate(self, key: str) -> None:
        """캐시 무효화"""
        ...
    
    def clear(self) -> None:
        """전체 캐시 정리"""
        ...


class SheetsOperations(Protocol):
    """시트 작업 인터페이스"""
    
    def read_worksheet(self, name: str) -> List[Dict[str, Any]]:
        """워크시트 읽기"""
        ...
    
    def write_worksheet(self, name: str, data: List[Dict[str, Any]]) -> bool:
        """워크시트 쓰기"""
        ...
    
    def update_cell(self, worksheet_name: str, row: int, col: int, value: Any) -> bool:
        """셀 업데이트"""
        ...
    
    def append_row(self, worksheet_name: str, values: List[Any]) -> bool:
        """행 추가"""
        ...


class PerformanceMonitor(Protocol):
    """성능 모니터링 인터페이스"""
    
    def record_operation(self, operation_type: str, duration: float) -> None:
        """작업 기록"""
        ...
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 반환"""
        ...
    
    def reset_stats(self) -> None:
        """통계 초기화"""
        ...


class BatchProcessor(Protocol):
    """배치 처리 인터페이스"""
    
    def add_operation(self, operation: 'BatchOperation') -> None:
        """배치 작업 추가"""
        ...
    
    def execute_batch(self) -> bool:
        """배치 실행"""
        ...
    
    def clear_batch(self) -> None:
        """배치 초기화"""
        ...


class BatchOperation:
    """배치 작업 정의"""
    
    def __init__(self, operation_type: str, worksheet_name: str, data: Any, **kwargs):
        self.operation_type = operation_type
        self.worksheet_name = worksheet_name
        self.data = data
        self.kwargs = kwargs 