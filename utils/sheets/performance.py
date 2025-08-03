"""
Google Sheets 성능 모니터링 모듈
성능 측정과 통계만 담당합니다.
"""

import time
from typing import Dict, Any, List
from .interfaces import PerformanceMonitor


class SheetsPerformanceMonitor(PerformanceMonitor):
    """시트 성능 모니터링 클래스"""
    
    def __init__(self):
        self._stats = {
            'api_calls': 0,
            'operations': {},
            'errors': 0,
            'start_time': time.time(),
            'last_operation_time': 0
        }
        self._operation_times: List[float] = []
    
    def record_operation(self, operation_type: str, duration: float) -> None:
        """작업 기록"""
        self._stats['api_calls'] += 1
        self._stats['last_operation_time'] = time.time()
        
        if operation_type not in self._stats['operations']:
            self._stats['operations'][operation_type] = {
                'count': 0,
                'total_time': 0,
                'avg_time': 0
            }
        
        op_stats = self._stats['operations'][operation_type]
        op_stats['count'] += 1
        op_stats['total_time'] += duration
        op_stats['avg_time'] = op_stats['total_time'] / op_stats['count']
        
        self._operation_times.append(duration)
        
        # 최근 100개만 유지
        if len(self._operation_times) > 100:
            self._operation_times.pop(0)
    
    def record_error(self, error_type: str = "general") -> None:
        """오류 기록"""
        self._stats['errors'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 반환"""
        uptime = time.time() - self._stats['start_time']
        
        # 평균 응답 시간 계산
        avg_response_time = 0
        if self._operation_times:
            avg_response_time = sum(self._operation_times) / len(self._operation_times)
        
        # 오류율 계산
        error_rate = 0
        if self._stats['api_calls'] > 0:
            error_rate = (self._stats['errors'] / self._stats['api_calls']) * 100
        
        return {
            'api_calls_total': self._stats['api_calls'],
            'errors': self._stats['errors'],
            'error_rate': round(error_rate, 2),
            'uptime_seconds': round(uptime, 2),
            'avg_response_time': round(avg_response_time * 1000, 2),  # ms
            'last_operation_time': self._stats['last_operation_time'],
            'operations': self._stats['operations']
        }
    
    def reset_stats(self) -> None:
        """통계 초기화"""
        self._stats = {
            'api_calls': 0,
            'operations': {},
            'errors': 0,
            'start_time': time.time(),
            'last_operation_time': 0
        }
        self._operation_times.clear()
    
    def get_performance_report(self) -> str:
        """성능 리포트 생성"""
        stats = self.get_stats()
        
        report_lines = ["=== Google Sheets 성능 리포트 ==="]
        
        # 기본 통계
        report_lines.append(f"\n📊 기본 통계:")
        report_lines.append(f"  총 API 호출: {stats['api_calls_total']}회")
        report_lines.append(f"  오류 발생: {stats['errors']}회")
        report_lines.append(f"  오류율: {stats['error_rate']}%")
        report_lines.append(f"  평균 응답시간: {stats['avg_response_time']}ms")
        report_lines.append(f"  가동시간: {stats['uptime_seconds']}초")
        
        # 작업별 통계
        if stats['operations']:
            report_lines.append(f"\n📈 작업별 통계:")
            for op_type, op_stats in stats['operations'].items():
                report_lines.append(f"  {op_type}:")
                report_lines.append(f"    호출 횟수: {op_stats['count']}회")
                report_lines.append(f"    평균 시간: {round(op_stats['avg_time'] * 1000, 2)}ms")
        
        # 성능 등급
        performance_grade = self._calculate_performance_grade(stats)
        report_lines.append(f"\n🏆 성능 등급: {performance_grade}")
        
        return "\n".join(report_lines)
    
    def _calculate_performance_grade(self, stats: Dict[str, Any]) -> str:
        """성능 등급 계산"""
        error_rate = stats['error_rate']
        avg_response_time = stats['avg_response_time']
        
        if error_rate > 10 or avg_response_time > 5000:
            return "🔴 D (개선 필요)"
        elif error_rate > 5 or avg_response_time > 2000:
            return "🟡 C (보통)"
        elif error_rate > 2 or avg_response_time > 1000:
            return "🟢 B (양호)"
        else:
            return "🟢 A (우수)"
    
    def health_check(self) -> Dict[str, Any]:
        """상태 확인"""
        stats = self.get_stats()
        
        health_status = {
            'status': 'healthy',
            'warnings': [],
            'details': stats
        }
        
        # 오류율 확인
        if stats['error_rate'] > 10:
            health_status['status'] = 'warning'
            health_status['warnings'].append(f"높은 오류율: {stats['error_rate']}%")
        
        # 응답 시간 확인
        if stats['avg_response_time'] > 5000:
            health_status['status'] = 'warning'
            health_status['warnings'].append(f"느린 응답시간: {stats['avg_response_time']}ms")
        
        # API 호출 빈도 확인
        if stats['api_calls_total'] > 1000:
            health_status['warnings'].append(f"높은 API 호출 빈도: {stats['api_calls_total']}회")
        
        return health_status 