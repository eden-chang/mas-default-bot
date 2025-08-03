"""
에러 통계 관리 모듈
"""

import threading
from typing import Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
from .types import KST, ErrorSeverity


class ErrorStats:
    """최적화된 에러 통계 (메모리 효율성 개선)"""
    
    def __init__(self, max_history: int = 1000):
        self._error_counts = defaultdict(int)
        self._recent_errors = deque(maxlen=max_history)
        self._lock = threading.RLock()
        self._hourly_stats = defaultdict(int)
        self._last_cleanup = datetime.now(KST)
    
    def record_error(self, error: Exception, context=None) -> None:
        """에러 기록 (최적화)"""
        with self._lock:
            error_type = error.__class__.__name__
            now = datetime.now(KST)
            
            # 기본 통계 업데이트
            self._error_counts[error_type] += 1
            
            # 최근 에러 기록 (메모리 효율성 개선)
            error_message = str(error)
            if len(error_message) > 100:
                error_message = error_message[:97] + "..."
            
            self._recent_errors.append({
                'type': error_type,
                'message': error_message,
                'timestamp': now,
                'severity': getattr(error, 'severity', ErrorSeverity.MEDIUM).name,
                'user_id': context.user_id if context else None
            })
            
            # 시간별 통계
            hour_key = now.strftime('%Y-%m-%d_%H')
            self._hourly_stats[hour_key] += 1
            
            # 주기적 정리 (1시간마다)
            if (now - self._last_cleanup).total_seconds() > 3600:
                self._cleanup_old_stats()
                self._last_cleanup = now
    
    def get_stats(self) -> Dict[str, Any]:
        """에러 통계 반환"""
        with self._lock:
            now = datetime.now(KST)
            hour_ago = now - timedelta(hours=1)
            day_ago = now - timedelta(days=1)
            
            # 시간별 필터링 (성능 최적화)
            recent_hour = 0
            recent_day = 0
            severity_stats = defaultdict(int)
            
            for err in self._recent_errors:
                timestamp = err['timestamp']
                if timestamp >= hour_ago:
                    recent_hour += 1
                if timestamp >= day_ago:
                    recent_day += 1
                severity_stats[err['severity']] += 1
            
            # 가장 빈번한 에러 타입 계산 (최적화)
            most_common_error = None
            if self._error_counts:
                most_common_error = max(self._error_counts, key=self._error_counts.get)
            
            return {
                'total_errors': sum(self._error_counts.values()),
                'recent_errors_count': len(self._recent_errors),
                'recent_hour_errors': recent_hour,
                'recent_day_errors': recent_day,
                'error_types': dict(self._error_counts),
                'severity_breakdown': dict(severity_stats),
                'most_common_error': most_common_error,
                'current_error_rate': recent_hour  # 시간당 에러율
            }
    
    def _cleanup_old_stats(self) -> None:
        """오래된 통계 정리"""
        cutoff = datetime.now(KST) - timedelta(days=7)
        cutoff_key = cutoff.strftime('%Y-%m-%d_%H')
        
        # 오래된 시간별 통계 제거
        old_keys = [k for k in self._hourly_stats.keys() if k < cutoff_key]
        for key in old_keys:
            del self._hourly_stats[key]
        
        # 오래된 최근 에러 기록 정리 (24시간 이전)
        day_cutoff = datetime.now(KST) - timedelta(days=1)
        while self._recent_errors and self._recent_errors[0]['timestamp'] < day_cutoff:
            self._recent_errors.popleft()
    
    def reset_stats(self, keep_recent: bool = True) -> None:
        """통계 초기화"""
        with self._lock:
            self._error_counts.clear()
            self._hourly_stats.clear()
            
            if not keep_recent:
                self._recent_errors.clear() 