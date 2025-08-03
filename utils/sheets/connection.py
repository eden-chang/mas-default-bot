"""
Google Sheets 연결 관리 모듈
연결과 관련된 책임만 담당합니다.
"""

import os
import time
import gspread
from typing import Optional
from gspread.exceptions import APIError

from .interfaces import SheetsConnection
from utils.error_handling import safe_execute, SheetAccessError, ErrorContext
from utils.logging_config import logger


class GoogleSheetsConnection(SheetsConnection):
    """Google Sheets 연결 관리 클래스"""
    
    def __init__(self, sheet_name: str, credentials_path: str):
        self.sheet_name = sheet_name
        self.credentials_path = credentials_path
        self._spreadsheet: Optional[gspread.Spreadsheet] = None
        self._last_connection_attempt = 0
        self._connection_retry_count = 0
    
    def connect(self) -> gspread.Spreadsheet:
        """스프레드시트에 연결"""
        if self._spreadsheet is not None:
            return self._spreadsheet
        
        def connection_operation():
            try:
                start_time = time.time()
                
                # Google API 인증
                gc = gspread.service_account(filename=str(self.credentials_path))
                
                # 스프레드시트 열기
                spreadsheet = gc.open(self.sheet_name)
                
                execution_time = time.time() - start_time
                logger.info(f"✅ 스프레드시트 '{self.sheet_name}' 연결 성공 ({execution_time:.3f}초)")
                
                return spreadsheet
                
            except FileNotFoundError:
                raise SheetAccessError(f"인증 파일을 찾을 수 없습니다: {self.credentials_path}")
            except gspread.exceptions.SpreadsheetNotFound:
                raise SheetAccessError(f"스프레드시트 '{self.sheet_name}'을 찾을 수 없습니다.")
            except APIError as e:
                if "RATE_LIMIT_EXCEEDED" in str(e):
                    logger.warning("API 속도 제한 초과, 재시도 대기")
                    time.sleep(2)
                    raise e
                else:
                    raise SheetAccessError(f"Google API 오류: {str(e)}")
            except Exception as e:
                raise SheetAccessError(f"스프레드시트 연결 실패: {str(e)}")
        
        with ErrorContext("스프레드시트 연결", additional_data={"sheet_name": self.sheet_name}):
            result = safe_execute("스프레드시트 연결", max_retries=3)(connection_operation)
            
            if result.success:
                self._spreadsheet = result.result
                self._last_connection_attempt = time.time()
                self._connection_retry_count = 0
                return self._spreadsheet
            else:
                self._connection_retry_count += 1
                raise result.error or SheetAccessError("스프레드시트 연결 실패")
    
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._spreadsheet is not None
    
    def disconnect(self) -> None:
        """연결 해제"""
        self._spreadsheet = None
        logger.info("스프레드시트 연결 해제")
    
    def get_worksheet(self, worksheet_name: str) -> gspread.Worksheet:
        """워크시트 가져오기"""
        spreadsheet = self.connect()
        
        def get_worksheet_operation():
            try:
                return spreadsheet.worksheet(worksheet_name)
            except gspread.exceptions.WorksheetNotFound:
                raise SheetAccessError(f"워크시트 '{worksheet_name}'을 찾을 수 없습니다.")
        
        result = safe_execute("워크시트 가져오기", max_retries=2)(get_worksheet_operation)
        
        if result.success:
            return result.result
        else:
            raise result.error or SheetAccessError(f"워크시트 '{worksheet_name}' 접근 실패")
    
    def health_check(self) -> dict:
        """연결 상태 확인"""
        try:
            if not self.is_connected():
                return {"status": "disconnected", "error": "연결되지 않음"}
            
            # 간단한 연결 테스트
            spreadsheet = self.connect()
            return {
                "status": "connected",
                "title": spreadsheet.title,
                "retry_count": self._connection_retry_count
            }
        except Exception as e:
            return {"status": "error", "error": str(e)} 