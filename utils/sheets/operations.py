"""
Google Sheets 기본 작업 모듈
시트 읽기/쓰기 작업만 담당합니다.
"""

import time
from typing import List, Dict, Any, Optional
from .interfaces import SheetsOperations
from .connection import GoogleSheetsConnection
from utils.error_handling import safe_execute, ErrorContext
from utils.logging_config import logger, bot_logger


class GoogleSheetsOperations(SheetsOperations):
    """Google Sheets 기본 작업 클래스"""
    
    def __init__(self, connection: GoogleSheetsConnection):
        self.connection = connection
        self._operation_count = 0
    
    def read_worksheet(self, name: str) -> List[Dict[str, Any]]:
        """워크시트 읽기"""
        def read_operation():
            try:
                worksheet = self.connection.get_worksheet(name)
                if worksheet.row_count <= 1:  # 헤더만 있거나 빈 시트
                    return []
                
                records = worksheet.get_all_records()
                self._operation_count += 1
                return records
            except Exception as e:
                # 워크시트가 존재하지 않는 경우
                if "워크시트" in str(e) and "찾을 수 없습니다" in str(e):
                    from utils.logging_config import logger
                    logger.warning(f"워크시트 '{name}'이 존재하지 않습니다.")
                    return []
                raise  # 다른 오류는 다시 발생시킴
        
        with ErrorContext("워크시트 읽기", additional_data={"worksheet": name}):
            result = safe_execute("워크시트 읽기", fallback_result=[])(read_operation)
            
            if result.success:
                bot_logger.log_sheet_operation("워크시트 읽기", name, True)
                return result.result
            else:
                bot_logger.log_sheet_operation("워크시트 읽기", name, False, str(result.error))
                return []
    
    def write_worksheet(self, name: str, data: List[Dict[str, Any]]) -> bool:
        """워크시트 쓰기"""
        def write_operation():
            worksheet = self.connection.get_worksheet(name)
            
            # 기존 데이터 지우기 (헤더 제외)
            if worksheet.row_count > 1:
                worksheet.delete_rows(2, worksheet.row_count)
            
            # 새 데이터 추가
            if data:
                worksheet.append_rows([list(row.values()) for row in data])
            
            self._operation_count += 1
            return True
        
        with ErrorContext("워크시트 쓰기", additional_data={"worksheet": name, "data_count": len(data)}):
            result = safe_execute("워크시트 쓰기", max_retries=3)(write_operation)
            
            success = result.success
            bot_logger.log_sheet_operation("워크시트 쓰기", name, success,
                                         str(result.error) if not success else None)
            
            return success
    
    def update_cell(self, worksheet_name: str, row: int, col: int, value: Any) -> bool:
        """셀 업데이트"""
        def update_operation():
            worksheet = self.connection.get_worksheet(worksheet_name)
            worksheet.update_cell(row, col, value)
            self._operation_count += 1
            return True
        
        with ErrorContext("셀 업데이트", additional_data={"worksheet": worksheet_name, "row": row, "col": col}):
            result = safe_execute("셀 업데이트", max_retries=3)(update_operation)
            
            success = result.success
            bot_logger.log_sheet_operation("셀 업데이트", worksheet_name, success,
                                         str(result.error) if not success else None)
            
            return success
    
    def append_row(self, worksheet_name: str, values: List[Any]) -> bool:
        """행 추가"""
        def append_operation():
            try:
                worksheet = self.connection.get_worksheet(worksheet_name)
                worksheet.append_row(values)
                self._operation_count += 1
                return True
            except Exception as e:
                # 워크시트가 존재하지 않는 경우
                if "워크시트" in str(e) and "찾을 수 없습니다" in str(e):
                    from utils.logging_config import logger
                    logger.warning(f"워크시트 '{worksheet_name}'이 존재하지 않습니다.")
                    return False
                raise  # 다른 오류는 다시 발생시킴
        
        with ErrorContext("행 추가", additional_data={"worksheet": worksheet_name, "values_count": len(values)}):
            result = safe_execute("행 추가", max_retries=3)(append_operation)
            
            success = result.success
            bot_logger.log_sheet_operation("행 추가", worksheet_name, success,
                                         str(result.error) if not success else None)
            
            return success
    
    def find_user_by_id(self, user_id: str, roster_worksheet: str) -> Optional[Dict[str, Any]]:
        """사용자 ID로 사용자 정보 조회"""
        roster_data = self.read_worksheet(roster_worksheet)
        
        for row in roster_data:
            if str(row.get('아이디', '')).strip() == user_id:
                return row
        
        return None
    
    def user_exists(self, user_id: str, roster_worksheet: str) -> bool:
        """사용자 존재 여부 확인"""
        return self.find_user_by_id(user_id, roster_worksheet) is not None
    
    def log_action(self, log_worksheet: str, user_name: str, command: str, 
                  message: str, success: bool = True) -> bool:
        """로그 기록"""
        try:
            from datetime import datetime
            import pytz
            
            now = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')
            status = "성공" if success else "실패"
            
            # 메시지 길이 제한
            if len(message) > 1000:
                message = message[:997] + "..."
            
            return self.append_row(log_worksheet, [now, user_name, command, message, status])
        except Exception as e:
            # 로그 워크시트가 없거나 접근할 수 없는 경우
            from utils.logging_config import logger
            logger.warning(f"로그 기록 실패 (워크시트: {log_worksheet}): {e}")
            return True  # 로그 실패해도 봇 동작에는 영향 없음
    
    def get_operation_stats(self) -> Dict[str, Any]:
        """작업 통계 반환"""
        return {
            'operation_count': self._operation_count,
            'connection_status': self.connection.is_connected()
        } 