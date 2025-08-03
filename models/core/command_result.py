"""
Main command result class
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import pytz
from ..enums.command_type import CommandType
from ..enums.command_status import CommandStatus
from ..base.base_result import BaseResult


@dataclass
class CommandResult:
    """명령어 실행 결과 통합 클래스"""
    
    command_type: CommandType               # 명령어 타입
    status: CommandStatus                   # 실행 상태
    user_id: str                           # 실행한 사용자 ID
    user_name: str                         # 사용자 이름
    original_command: str                  # 원본 명령어
    message: str                           # 결과 메시지
    result_data: Optional[BaseResult] = None
    error: Optional[Exception] = None      # 오류 (있는 경우)
    execution_time: Optional[float] = None # 실행 시간 (초)
    timestamp: datetime = field(default_factory=lambda: datetime.now(pytz.timezone('Asia/Seoul')))
    metadata: Dict[str, Any] = field(default_factory=dict)  # 추가 메타데이터
    
    @classmethod
    def success(cls, command_type: CommandType, user_id: str, user_name: str, 
                original_command: str, message: str, result_data: Any = None,
                execution_time: float = None, **metadata) -> 'CommandResult':
        """
        성공 결과 생성
        
        Args:
            command_type: 명령어 타입
            user_id: 사용자 ID
            user_name: 사용자 이름
            original_command: 원본 명령어
            message: 결과 메시지
            result_data: 결과 데이터
            execution_time: 실행 시간
            **metadata: 추가 메타데이터
            
        Returns:
            CommandResult: 성공 결과 객체
        """
        return cls(
            command_type=command_type,
            status=CommandStatus.SUCCESS,
            user_id=user_id,
            user_name=user_name,
            original_command=original_command,
            message=message,
            result_data=result_data,
            execution_time=execution_time,
            metadata=metadata
        )
    
    @classmethod
    def failure(cls, command_type: CommandType, user_id: str, user_name: str,
                original_command: str, error: Exception, execution_time: float = None,
                **metadata) -> 'CommandResult':
        """
        실패 결과 생성
        
        Args:
            command_type: 명령어 타입
            user_id: 사용자 ID
            user_name: 사용자 이름
            original_command: 원본 명령어
            error: 발생한 오류
            execution_time: 실행 시간
            **metadata: 추가 메타데이터
            
        Returns:
            CommandResult: 실패 결과 객체
        """
        return cls(
            command_type=command_type,
            status=CommandStatus.FAILED,
            user_id=user_id,
            user_name=user_name,
            original_command=original_command,
            message=str(error),
            error=error,
            execution_time=execution_time,
            metadata=metadata
        )
    
    @classmethod
    def error(cls, command_type: CommandType, user_id: str, user_name: str,
              original_command: str, error: Exception, execution_time: float = None,
              **metadata) -> 'CommandResult':
        """
        오류 결과 생성
        
        Args:
            command_type: 명령어 타입
            user_id: 사용자 ID
            user_name: 사용자 이름
            original_command: 원본 명령어
            error: 발생한 오류
            execution_time: 실행 시간
            **metadata: 추가 메타데이터
            
        Returns:
            CommandResult: 오류 결과 객체
        """
        return cls(
            command_type=command_type,
            status=CommandStatus.ERROR,
            user_id=user_id,
            user_name=user_name,
            original_command=original_command,
            message=str(error),
            error=error,
            execution_time=execution_time,
            metadata=metadata
        )
    
    def is_successful(self) -> bool:
        """성공 여부 확인"""
        return self.status == CommandStatus.SUCCESS
    
    def has_error(self) -> bool:
        """오류 여부 확인"""
        return self.error is not None
    
    def get_log_message(self) -> str:
        """로그용 메시지 반환"""
        status_text = "성공" if self.is_successful() else "실패"
        execution_info = f" ({self.execution_time:.3f}초)" if self.execution_time else ""
        return f"[{self.command_type.value}] {self.user_name} | {self.original_command} | {status_text}{execution_info}"
    
    def get_user_message(self) -> str:
        """사용자에게 표시할 메시지 반환"""
        return self.message
    
    def get_result_summary(self) -> Dict[str, Any]:
        """결과 요약 정보 반환"""
        summary = {
            'command_type': self.command_type.value,
            'status': self.status.value,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'command': self.original_command,
            'success': self.is_successful(),
            'has_error': self.has_error(),
            'execution_time': self.execution_time,
            'timestamp': self.timestamp.isoformat()
        }
        
        if self.result_data:
            if hasattr(self.result_data, 'to_dict'):
                summary['result_data'] = self.result_data.to_dict()
            else:
                summary['result_data'] = str(self.result_data)
        
        if self.error:
            summary['error_type'] = type(self.error).__name__
            summary['error_message'] = str(self.error)
        
        summary.update(self.metadata)
        
        return summary
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (직렬화용)"""
        data = {
            'command_type': self.command_type.value,
            'status': self.status.value,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'original_command': self.original_command,
            'message': self.message,
            'execution_time': self.execution_time,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }
        
        if self.result_data and hasattr(self.result_data, 'to_dict'):
            data['result_data'] = self.result_data.to_dict()
        
        if self.error:
            data['error'] = {
                'type': type(self.error).__name__,
                'message': str(self.error)
            }
        
        return data
    
    def add_metadata(self, key: str, value: Any) -> None:
        """메타데이터 추가"""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """메타데이터 조회"""
        return self.metadata.get(key, default) 