"""
Command statistics classes
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any
from datetime import datetime, timedelta
import pytz
from .command_result import CommandResult
from ..enums.command_status import CommandStatus


@dataclass
class CommandStats:
    """명령어 실행 통계"""
    
    total_commands: int = 0
    successful_commands: int = 0
    failed_commands: int = 0
    error_commands: int = 0
    command_type_counts: Dict[str, int] = field(default_factory=dict)
    user_command_counts: Dict[str, int] = field(default_factory=dict)
    average_execution_time: float = 0.0
    total_execution_time: float = 0.0
    
    @classmethod
    def from_results(cls, results: List[CommandResult]) -> 'CommandStats':
        """
        명령어 결과 리스트에서 통계 생성
        
        Args:
            results: 명령어 결과 리스트
            
        Returns:
            CommandStats: 통계 객체
        """
        if not results:
            return cls()
        
        stats = cls()
        execution_times = []
        
        for result in results:
            stats.total_commands += 1
            
            # 상태별 카운트
            if result.status == CommandStatus.SUCCESS:
                stats.successful_commands += 1
            elif result.status == CommandStatus.FAILED:
                stats.failed_commands += 1
            elif result.status == CommandStatus.ERROR:
                stats.error_commands += 1
            
            # 명령어 타입별 카운트
            cmd_type = result.command_type.value
            stats.command_type_counts[cmd_type] = stats.command_type_counts.get(cmd_type, 0) + 1
            
            # 사용자별 카운트
            stats.user_command_counts[result.user_name] = stats.user_command_counts.get(result.user_name, 0) + 1
            
            # 실행 시간 수집
            if result.execution_time:
                execution_times.append(result.execution_time)
                stats.total_execution_time += result.execution_time
        
        # 평균 실행 시간 계산
        if execution_times:
            stats.average_execution_time = sum(execution_times) / len(execution_times)
        
        return stats
    
    @property
    def success_rate(self) -> float:
        """성공률 (퍼센트)"""
        if self.total_commands == 0:
            return 0.0
        return (self.successful_commands / self.total_commands) * 100
    
    @property
    def error_rate(self) -> float:
        """오류율 (퍼센트)"""
        if self.total_commands == 0:
            return 0.0
        return (self.error_commands / self.total_commands) * 100
    
    def get_top_users(self, limit: int = 5) -> List[tuple]:
        """
        상위 사용자 목록 반환
        
        Args:
            limit: 반환할 사용자 수
            
        Returns:
            List[tuple]: (사용자명, 명령어수) 튜플 리스트
        """
        sorted_users = sorted(
            self.user_command_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_users[:limit]
    
    def get_top_commands(self, limit: int = 5) -> List[tuple]:
        """
        상위 명령어 타입 목록 반환
        
        Args:
            limit: 반환할 명령어 타입 수
            
        Returns:
            List[tuple]: (명령어타입, 사용횟수) 튜플 리스트
        """
        sorted_commands = sorted(
            self.command_type_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_commands[:limit]
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'total_commands': self.total_commands,
            'successful_commands': self.successful_commands,
            'failed_commands': self.failed_commands,
            'error_commands': self.error_commands,
            'success_rate': round(self.success_rate, 2),
            'error_rate': round(self.error_rate, 2),
            'command_type_counts': self.command_type_counts,
            'user_command_counts': self.user_command_counts,
            'average_execution_time': round(self.average_execution_time, 3),
            'total_execution_time': round(self.total_execution_time, 3),
            'top_users': self.get_top_users(),
            'top_commands': self.get_top_commands()
        }
    
    def get_summary_text(self) -> str:
        """
        통계 요약 텍스트 반환
        
        Returns:
            str: 통계 요약
        """
        lines = [
            f"📈 명령어 실행 통계",
            f"총 실행: {self.total_commands:,}회",
            f"성공: {self.successful_commands:,}회 ({self.success_rate:.1f}%)",
            f"실패: {self.failed_commands:,}회",
            f"오류: {self.error_commands:,}회 ({self.error_rate:.1f}%)"
        ]
        
        if self.average_execution_time > 0:
            lines.append(f"평균 실행시간: {self.average_execution_time:.3f}초")
        
        top_commands = self.get_top_commands(3)
        if top_commands:
            lines.append(f"인기 명령어: {', '.join([f'{cmd}({cnt})' for cmd, cnt in top_commands])}")
        
        top_users = self.get_top_users(3)
        if top_users:
            lines.append(f"활성 사용자: {', '.join([f'{user}({cnt})' for user, cnt in top_users])}")
        
        return "\n".join(lines)


# 전역 통계 관리자
class GlobalCommandStats:
    """전역 명령어 통계 관리자"""
    
    def __init__(self):
        self._results: List[CommandResult] = []
        self._max_results = 1000  # 최대 저장할 결과 수
    
    def add_result(self, result: CommandResult) -> None:
        """결과 추가"""
        try:
            self._results.append(result)
            
            # 최대 개수 초과 시 오래된 결과 제거
            if len(self._results) > self._max_results:
                self._results = self._results[-self._max_results:]
        except Exception:
            # 추가 실패 시 무시 (통계는 필수가 아님)
            pass
    
    def get_stats(self, hours: int = 24) -> CommandStats:
        """
        최근 N시간 통계 반환
        
        Args:
            hours: 조회할 시간 범위
            
        Returns:
            CommandStats: 통계 객체
        """
        try:
            cutoff_time = datetime.now(pytz.timezone('Asia/Seoul')) - timedelta(hours=hours)
            recent_results = [
                result for result in self._results
                if result.timestamp >= cutoff_time
            ]
            return CommandStats.from_results(recent_results)
        except Exception:
            # 오류 시 빈 통계 반환
            return CommandStats()
    
    def clear_old_results(self, days: int = 7) -> int:
        """
        오래된 결과 정리
        
        Args:
            days: 보관할 일수
            
        Returns:
            int: 정리된 결과 수
        """
        try:
            cutoff_time = datetime.now(pytz.timezone('Asia/Seoul')) - timedelta(days=days)
            old_count = len(self._results)
            self._results = [
                result for result in self._results
                if result.timestamp >= cutoff_time
            ]
            return old_count - len(self._results)
        except Exception:
            return 0


# 전역 통계 인스턴스
global_stats = GlobalCommandStats() 