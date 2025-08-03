"""
Google Sheets 캐시 관리 모듈
캐시와 관련된 책임만 담당합니다.
"""

import time
from typing import Any, Optional, Dict
from .interfaces import SheetsCache


class NoCacheStrategy(SheetsCache):
    """캐시를 사용하지 않는 전략"""
    
    def get(self, key: str) -> Optional[Any]:
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        pass
    
    def invalidate(self, key: str) -> None:
        pass
    
    def clear(self) -> None:
        pass


class TimeBasedCacheStrategy(SheetsCache):
    """시간 기반 캐시 전략"""
    
    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        
        cache_entry = self._cache[key]
        if time.time() > cache_entry['expires_at']:
            del self._cache[key]
            return None
        
        return cache_entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl = ttl or self.default_ttl
        self._cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl
        }
    
    def invalidate(self, key: str) -> None:
        if key in self._cache:
            del self._cache[key]
    
    def clear(self) -> None:
        self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """만료된 캐시 정리"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if current_time > entry['expires_at']
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        return len(expired_keys)


class SheetsCacheManager:
    """시트 캐시 관리자"""
    
    def __init__(self, cache_strategy: SheetsCache = None):
        self.cache_strategy = cache_strategy or NoCacheStrategy()
        self._cache_hits = 0
        self._cache_misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        value = self.cache_strategy.get(key)
        if value is not None:
            self._cache_hits += 1
        else:
            self._cache_misses += 1
        return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """캐시에 값 저장"""
        self.cache_strategy.set(key, value, ttl)
    
    def invalidate(self, key: str) -> None:
        """캐시 무효화"""
        self.cache_strategy.invalidate(key)
    
    def clear(self) -> None:
        """전체 캐시 정리"""
        self.cache_strategy.clear()
        self._cache_hits = 0
        self._cache_misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate': round(hit_rate, 2),
            'total_requests': total_requests
        }
    
    def cleanup(self) -> int:
        """만료된 캐시 정리"""
        if isinstance(self.cache_strategy, TimeBasedCacheStrategy):
            return self.cache_strategy.cleanup_expired()
        return 0 