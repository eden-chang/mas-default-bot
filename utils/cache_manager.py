"""
캐시 관리 모듈 (성능 최적화 버전)
실시간 데이터 반영과 고성능 캐싱을 제공합니다.
"""

import os
import sys
import time
import threading
import hashlib
import json
import gzip
import pickle
from typing import Any, Optional, Dict, List, Callable, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict
import pytz
try:
    import psutil
except ImportError:
    psutil = None

# 경로 설정 (VM 환경 대응)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

try:
    from config.settings import config
    from utils.logging_config import logger
except ImportError:
    # VM 환경에서 임포트 실패 시 폴백
    import logging
    logger = logging.getLogger('cache_manager')
    
    # 기본 설정값
    class FallbackConfig:
        DEBUG_MODE = False
        FORTUNE_CACHE_TTL = 3600
        MAX_CACHE_SIZE = 1000
        COMPRESSION_THRESHOLD = 1024  # 1KB 이상 압축
    config = FallbackConfig()

# KST 타임존
KST = pytz.timezone('Asia/Seoul')


@dataclass
class CacheItem:
    """캐시 아이템 (성능 최적화)"""
    key: str
    value: Any
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    size_bytes: int = 0
    compressed: bool = False
    
    def update_access(self) -> None:
        """접근 정보 업데이트"""
        self.accessed_at = datetime.now()
        self.access_count += 1
    
    def get_age_seconds(self) -> float:
        """생성 후 경과 시간 (초)"""
        return (datetime.now() - self.created_at).total_seconds()
    
    def get_idle_seconds(self) -> float:
        """마지막 접근 후 경과 시간 (초)"""
        return (datetime.now() - self.accessed_at).total_seconds()


@dataclass
class DailyFortuneCache:
    """유저별 일일 운세 캐시 아이템 (최적화)"""
    user_id: str
    fortune_text: str
    date: str  # YYYY-MM-DD 형식
    created_at: datetime
    access_count: int = 0
    
    def is_valid_for_date(self, target_date: str) -> bool:
        """지정된 날짜에 대해 유효한지 확인"""
        return self.date == target_date
    
    def update_access(self) -> None:
        """접근 횟수 업데이트"""
        self.access_count += 1


@dataclass
class ContentCache:
    """콘텐츠 캐시 아이템 (최적화)"""
    content_type: str
    data: Any
    created_at: datetime
    ttl: int  # TTL (초)
    access_count: int = 0
    size_bytes: int = 0
    compressed: bool = False
    
    def is_expired(self) -> bool:
        """캐시 만료 여부 확인"""
        return (datetime.now() - self.created_at).total_seconds() > self.ttl
    
    def update_access(self) -> None:
        """접근 횟수 업데이트"""
        self.access_count += 1


@dataclass
class CacheMetrics:
    """캐시 성능 메트릭"""
    total_requests: int = 0
    total_hits: int = 0
    total_misses: int = 0
    total_evictions: int = 0
    total_compressions: int = 0
    total_decompressions: int = 0
    memory_usage_bytes: int = 0
    compression_ratio: float = 1.0
    average_response_time: float = 0.0
    last_cleanup_time: float = 0.0


class LRUCache:
    """LRU (Least Recently Used) 캐시 구현"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict = OrderedDict()
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        with self._lock:
            if key in self.cache:
                # LRU 순서 업데이트
                value = self.cache.pop(key)
                self.cache[key] = value
                return value
            return None
    
    def put(self, key: str, value: Any) -> None:
        """캐시에 값 저장"""
        with self._lock:
            if key in self.cache:
                # 기존 값 제거
                self.cache.pop(key)
            elif len(self.cache) >= self.max_size:
                # LRU 항목 제거
                self.cache.popitem(last=False)
            
            self.cache[key] = value
    
    def remove(self, key: str) -> bool:
        """캐시에서 항목 제거"""
        with self._lock:
            if key in self.cache:
                self.cache.pop(key)
                return True
            return False
    
    def clear(self) -> None:
        """캐시 전체 비우기"""
        with self._lock:
            self.cache.clear()
    
    def size(self) -> int:
        """캐시 크기 반환"""
        return len(self.cache)
    
    def keys(self) -> List[str]:
        """캐시 키 목록 반환"""
        return list(self.cache.keys())


class CacheCompressor:
    """캐시 압축/해제 유틸리티"""
    
    @staticmethod
    def compress_data(data: Any) -> Tuple[bytes, bool]:
        """데이터 압축"""
        try:
            # 데이터를 pickle로 직렬화
            serialized = pickle.dumps(data)
            
            # 압축 임계값 확인
            if len(serialized) < getattr(config, 'COMPRESSION_THRESHOLD', 1024):
                return serialized, False
            
            # gzip 압축
            compressed = gzip.compress(serialized)
            
            # 압축률 확인 (압축이 효과적이면 압축된 데이터 반환)
            if len(compressed) < len(serialized):
                return compressed, True
            else:
                return serialized, False
                
        except Exception as e:
            logger.warning(f"데이터 압축 실패: {e}")
            return pickle.dumps(data), False
    
    @staticmethod
    def decompress_data(compressed_data: bytes, is_compressed: bool) -> Any:
        """데이터 해제"""
        try:
            if is_compressed:
                # gzip 해제
                decompressed = gzip.decompress(compressed_data)
            else:
                decompressed = compressed_data
            
            # pickle 역직렬화
            return pickle.loads(decompressed)
            
        except Exception as e:
            logger.error(f"데이터 해제 실패: {e}")
            return None


class CacheManager:
    """고성능 캐시 관리자 (성능 최적화)"""
    
    def __init__(self):
        """CacheManager 초기화"""
        self._fortune_cache: Dict[str, DailyFortuneCache] = {}
        self._content_cache: Dict[str, ContentCache] = {}
        self._lru_cache = LRUCache(max_size=getattr(config, 'MAX_CACHE_SIZE', 1000))
        self._compressor = CacheCompressor()
        self._lock = threading.RLock()
        self._metrics = CacheMetrics()
        
        # 성능 모니터링
        self._last_memory_check = time.time()
        self._memory_check_interval = 300  # 5분마다 메모리 체크
        
        logger.info("고성능 캐시 매니저 초기화 완료")
    
    def get_user_daily_fortune(self, user_id: str, fortune_text: str = None) -> Optional[str]:
        """
        유저별 일일 운세 조회/저장 (성능 최적화)
        
        Args:
            user_id: 사용자 ID
            fortune_text: 새로운 운세 (저장용, None이면 조회만)
            
        Returns:
            Optional[str]: 저장된 운세 또는 None
        """
        start_time = time.time()
        current_date = self._get_kst_date_string()
        cache_key = f"{user_id}:{current_date}"
        
        with self._lock:
            self._metrics.total_requests += 1
            
            # 조회
            if cache_key in self._fortune_cache:
                cached_fortune = self._fortune_cache[cache_key]
                if cached_fortune.is_valid_for_date(current_date):
                    cached_fortune.update_access()
                    self._metrics.total_hits += 1
                    self._update_response_time(time.time() - start_time)
                    logger.debug(f"운세 캐시 히트: {user_id} ({current_date})")
                    return cached_fortune.fortune_text
                else:
                    # 날짜가 바뀐 경우 삭제
                    del self._fortune_cache[cache_key]
            
            # 새로운 운세 저장
            if fortune_text:
                self._fortune_cache[cache_key] = DailyFortuneCache(
                    user_id=user_id,
                    fortune_text=fortune_text,
                    date=current_date,
                    created_at=datetime.now()
                )
                self._metrics.total_misses += 1
                self._update_response_time(time.time() - start_time)
                logger.debug(f"운세 캐시 저장: {user_id} ({current_date})")
                return fortune_text
            
            # 조회만 하는 경우 None 반환
            self._metrics.total_misses += 1
            self._update_response_time(time.time() - start_time)
            return None
    
    def get_content_with_cache(self, content_type: str, fetch_func: Callable) -> Any:
        """
        콘텐츠를 캐시로 조회 (성능 최적화)
        
        Args:
            content_type: 콘텐츠 타입
            fetch_func: 데이터를 가져오는 함수
            
        Returns:
            Any: 캐시된 데이터 또는 새로 가져온 데이터
        """
        start_time = time.time()
        
        with self._lock:
            self._metrics.total_requests += 1
            
            # 캐시 확인
            if content_type in self._content_cache:
                cached_content = self._content_cache[content_type]
                if not cached_content.is_expired():
                    cached_content.update_access()
                    self._metrics.total_hits += 1
                    self._update_response_time(time.time() - start_time)
                    logger.debug(f"콘텐츠 캐시 히트: {content_type}")
                    
                    # 압축된 데이터 해제
                    if cached_content.compressed:
                        self._metrics.total_decompressions += 1
                        return self._compressor.decompress_data(
                            cached_content.data, True
                        )
                    return cached_content.data
                else:
                    # 만료된 캐시 삭제
                    del self._content_cache[content_type]
            
            # 새 데이터 가져오기
            try:
                data = fetch_func()
                
                # 데이터 압축 시도
                compressed_data, is_compressed = self._compressor.compress_data(data)
                
                # 캐시에 저장
                self._content_cache[content_type] = ContentCache(
                    content_type=content_type,
                    data=compressed_data,
                    created_at=datetime.now(),
                    ttl=3600,  # 1시간
                    size_bytes=len(compressed_data),
                    compressed=is_compressed
                )
                
                if is_compressed:
                    self._metrics.total_compressions += 1
                
                self._metrics.total_misses += 1
                self._update_response_time(time.time() - start_time)
                logger.debug(f"콘텐츠 캐시 저장: {content_type}")
                return data
                
            except Exception as e:
                logger.error(f"콘텐츠 조회 실패: {content_type} - {e}")
                self._metrics.total_misses += 1
                self._update_response_time(time.time() - start_time)
                return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """
        일반 캐시에 값 저장 (LRU 적용)
        
        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: TTL (초)
        """
        start_time = time.time()
        
        with self._lock:
            # 데이터 압축
            compressed_data, is_compressed = self._compressor.compress_data(value)
            
            # LRU 캐시에 저장
            self._lru_cache.put(key, {
                'data': compressed_data,
                'compressed': is_compressed,
                'created_at': datetime.now(),
                'ttl': ttl
            })
            
            if is_compressed:
                self._metrics.total_compressions += 1
            
            self._metrics.total_requests += 1
            self._update_response_time(time.time() - start_time)
    
    def get(self, key: str) -> Optional[Any]:
        """
        일반 캐시에서 값 조회 (LRU 적용)
        
        Args:
            key: 캐시 키
            
        Returns:
            Optional[Any]: 캐시된 값 또는 None
        """
        start_time = time.time()
        
        with self._lock:
            cached_item = self._lru_cache.get(key)
            
            if cached_item:
                # TTL 확인
                if (datetime.now() - cached_item['created_at']).total_seconds() > cached_item['ttl']:
                    self._lru_cache.remove(key)
                    self._metrics.total_misses += 1
                    self._update_response_time(time.time() - start_time)
                    return None
                
                # 압축된 데이터 해제
                if cached_item['compressed']:
                    self._metrics.total_decompressions += 1
                    data = self._compressor.decompress_data(
                        cached_item['data'], True
                    )
                else:
                    data = self._compressor.decompress_data(
                        cached_item['data'], False
                    )
                
                self._metrics.total_hits += 1
                self._update_response_time(time.time() - start_time)
                return data
            else:
                self._metrics.total_misses += 1
                self._update_response_time(time.time() - start_time)
                return None
    
    def delete(self, key: str) -> bool:
        """
        캐시에서 항목 삭제
        
        Args:
            key: 삭제할 키
            
        Returns:
            bool: 삭제 성공 여부
        """
        with self._lock:
            return self._lru_cache.remove(key)
    
    def clear_old_entries(self) -> int:
        """
        오래된 캐시 항목 정리
        
        Returns:
            int: 정리된 항목 수
        """
        with self._lock:
            removed_count = 0
            
            # 운세 캐시 정리
            current_date = self._get_kst_date_string()
            keys_to_remove = []
            for key, cached_fortune in self._fortune_cache.items():
                if not cached_fortune.is_valid_for_date(current_date):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._fortune_cache[key]
                removed_count += 1
            
            # 콘텐츠 캐시 정리
            keys_to_remove = []
            for key, cached_content in self._content_cache.items():
                if cached_content.is_expired():
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._content_cache[key]
                removed_count += 1
            
            # LRU 캐시 정리
            keys_to_remove = []
            for key in self._lru_cache.keys():
                cached_item = self._lru_cache.get(key)
                if cached_item and (datetime.now() - cached_item['created_at']).total_seconds() > cached_item['ttl']:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                self._lru_cache.remove(key)
                removed_count += 1
            
            self._metrics.last_cleanup_time = time.time()
            return removed_count
    
    def optimize_memory_usage(self) -> Dict[str, Any]:
        """
        메모리 사용량 최적화
        
        Returns:
            Dict[str, Any]: 최적화 결과
        """
        current_time = time.time()
        if current_time - self._last_memory_check < self._memory_check_interval:
            return {'status': 'skipped', 'reason': 'too_frequent'}
        
        self._last_memory_check = current_time
        
        if psutil:
            try:
                # 메모리 사용량 확인
                process = psutil.Process()
                memory_info = process.memory_info()
                current_memory = memory_info.rss
                
                optimization_result = {
                    'status': 'optimized',
                    'before_memory_mb': current_memory / (1024 * 1024),
                    'actions_taken': []
                }
                
                with self._lock:
                    # 1. 오래된 항목 정리
                    removed_count = self.clear_old_entries()
                    if removed_count > 0:
                        optimization_result['actions_taken'].append(f'removed_old_entries: {removed_count}')
                    
                    # 2. LRU 캐시 크기 조정
                    if self._lru_cache.size() > self._lru_cache.max_size * 0.8:
                        # 20% 제거
                        remove_count = int(self._lru_cache.size() * 0.2)
                        keys_to_remove = list(self._lru_cache.keys())[:remove_count]
                        for key in keys_to_remove:
                            self._lru_cache.remove(key)
                        optimization_result['actions_taken'].append(f'reduced_lru_cache: {remove_count}')
                    
                    # 3. 압축률이 낮은 항목 재압축
                    recompressed_count = 0
                    for key, cached_content in self._content_cache.items():
                        if not cached_content.compressed and cached_content.size_bytes > 1024:
                            # 재압축 시도
                            compressed_data, is_compressed = self._compressor.compress_data(
                                self._compressor.decompress_data(cached_content.data, False)
                            )
                            if is_compressed and len(compressed_data) < cached_content.size_bytes:
                                cached_content.data = compressed_data
                                cached_content.compressed = True
                                cached_content.size_bytes = len(compressed_data)
                                recompressed_count += 1
                    
                    if recompressed_count > 0:
                        optimization_result['actions_taken'].append(f'recompressed_items: {recompressed_count}')
                
                # 최적화 후 메모리 사용량
                memory_info = process.memory_info()
                after_memory = memory_info.rss
                optimization_result['after_memory_mb'] = after_memory / (1024 * 1024)
                optimization_result['memory_saved_mb'] = (current_memory - after_memory) / (1024 * 1024)
                
                return optimization_result
                
            except Exception as e:
                logger.error(f"메모리 최적화 실패: {e}")
                return {'status': 'error', 'error': str(e)}
        else:
            return {'status': 'skipped', 'reason': 'psutil_not_available'}
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """
        상세한 캐시 통계 반환
        
        Returns:
            Dict[str, Any]: 상세한 통계 정보
        """
        with self._lock:
            total_requests = self._metrics.total_requests
            hit_rate = (self._metrics.total_hits / total_requests * 100) if total_requests > 0 else 0
            
            # 메모리 사용량 계산
            memory_usage = 0
            for cached_content in self._content_cache.values():
                memory_usage += cached_content.size_bytes
            
            # 압축률 계산
            compression_ratio = self._metrics.compression_ratio
            
            return {
                'fortune_cache_size': len(self._fortune_cache),
                'content_cache_size': len(self._content_cache),
                'lru_cache_size': self._lru_cache.size(),
                'total_requests': total_requests,
                'total_hits': self._metrics.total_hits,
                'total_misses': self._metrics.total_misses,
                'hit_rate': round(hit_rate, 2),
                'total_evictions': self._metrics.total_evictions,
                'total_compressions': self._metrics.total_compressions,
                'total_decompressions': self._metrics.total_decompressions,
                'memory_usage_mb': round(memory_usage / (1024 * 1024), 2),
                'compression_ratio': round(compression_ratio, 2),
                'average_response_time_ms': round(self._metrics.average_response_time * 1000, 2),
                'last_cleanup_time': self._metrics.last_cleanup_time
            }
    
    def _update_response_time(self, response_time: float) -> None:
        """응답 시간 업데이트"""
        total_requests = self._metrics.total_requests
        current_avg = self._metrics.average_response_time
        new_avg = (current_avg * (total_requests - 1) + response_time) / total_requests
        self._metrics.average_response_time = new_avg
    
    def _get_kst_date_string(self) -> str:
        """현재 KST 날짜를 YYYY-MM-DD 형식으로 반환"""
        kst_now = datetime.now(KST)
        return kst_now.strftime('%Y-%m-%d')


class BotCacheManager:
    """봇 전용 캐시 관리자 (성능 최적화)"""
    
    def __init__(self):
        """BotCacheManager 초기화"""
        self.cache = CacheManager()
        # general_cache 속성 추가 (하위 호환성)
        self.general_cache = self.cache
        logger.info("고성능 봇 캐시 매니저 초기화 완료")
    
    def get_user_daily_fortune(self, user_id: str, fortune_text: str = None) -> Optional[str]:
        """유저별 일일 운세 조회/저장"""
        return self.cache.get_user_daily_fortune(user_id, fortune_text)
    
    def get_fortune_phrases(self, fetch_func: Callable) -> List[str]:
        """운세 문구 목록 조회 (1시간 캐시)"""
        return self.cache.get_content_with_cache('fortune_list', fetch_func) or []
    
    def get_help_items(self, fetch_func: Callable) -> List[Dict]:
        """도움말 항목 조회 (1시간 캐시)"""
        return self.cache.get_content_with_cache('help_items', fetch_func) or []
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """일반 캐시에 값 저장"""
        self.cache.set(key, value, ttl)
    
    def get(self, key: str) -> Optional[Any]:
        """일반 캐시에서 값 조회"""
        return self.cache.get(key)
    
    def delete(self, key: str) -> bool:
        """캐시에서 항목 삭제"""
        return self.cache.delete(key)
    
    def clear_old_entries(self) -> int:
        """오래된 캐시 정리"""
        return self.cache.clear_old_entries()
    
    def optimize_memory(self) -> Dict[str, Any]:
        """메모리 최적화"""
        return self.cache.optimize_memory_usage()
    
    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        return self.cache.get_detailed_stats()
    
    def health_check(self) -> Dict[str, Any]:
        """캐시 상태 확인"""
        stats = self.get_stats()
        
        health_status = {
            'status': 'healthy',
            'errors': [],
            'warnings': [],
            'details': stats
        }
        
        # 히트율 확인
        if stats['hit_rate'] < 50:
            health_status['warnings'].append(f"낮은 캐시 히트율: {stats['hit_rate']}%")
        
        # 메모리 사용량 확인
        if stats['memory_usage_mb'] > 100:  # 100MB 이상
            health_status['warnings'].append(f"높은 메모리 사용량: {stats['memory_usage_mb']}MB")
        
        # 응답 시간 확인
        if stats['average_response_time_ms'] > 100:  # 100ms 이상
            health_status['warnings'].append(f"느린 응답 시간: {stats['average_response_time_ms']}ms")
        
        return health_status
    
    def cleanup_all_expired(self) -> Dict[str, int]:
        """모든 만료된 캐시 정리"""
        try:
            # 일반 캐시 정리
            general_cleared = self.cache.clear_old_entries()
            
            return {
                'general_cache': general_cleared,
                'total': general_cleared
            }
            
        except Exception as e:
            logger.error(f"캐시 정리 중 오류 발생: {e}")
            return {
                'general_cache': 0,
                'total': 0,
                'error': str(e)
            }


# 전역 캐시 매니저 인스턴스
bot_cache = BotCacheManager()


# 편의 함수들
def get_user_daily_fortune(user_id: str, fortune_text: str = None) -> Optional[str]:
    """유저별 일일 운세 조회/저장"""
    return bot_cache.get_user_daily_fortune(user_id, fortune_text)


def get_fortune_phrases_cached(fetch_func: Callable) -> List[str]:
    """운세 문구 목록 조회 (캐시 적용)"""
    return bot_cache.get_fortune_phrases(fetch_func)


def get_help_items_cached(fetch_func: Callable) -> List[Dict]:
    """도움말 항목 조회 (캐시 적용)"""
    return bot_cache.get_help_items(fetch_func)


def set_cache(key: str, value: Any, ttl: int = 3600) -> None:
    """캐시에 값 저장"""
    bot_cache.set(key, value, ttl)


def get_cache(key: str) -> Optional[Any]:
    """캐시에서 값 조회"""
    return bot_cache.get(key)


def delete_cache(key: str) -> bool:
    """캐시에서 항목 삭제"""
    return bot_cache.delete(key)


def clear_old_entries() -> int:
    """오래된 캐시 정리"""
    return bot_cache.clear_old_entries()


def optimize_memory() -> Dict[str, Any]:
    """메모리 최적화"""
    return bot_cache.optimize_memory()


def get_cache_stats() -> Dict[str, Any]:
    """캐시 통계 반환"""
    return bot_cache.get_stats()


def get_cache_health() -> Dict[str, Any]:
    """캐시 상태 확인"""
    return bot_cache.health_check()


def clear_cache() -> None:
    """캐시 전체 삭제 (백워드 호환성)"""
    bot_cache.cache._fortune_cache.clear()
    bot_cache.cache._content_cache.clear()
    bot_cache.cache._lru_cache.clear()
    logger.info("캐시 전체 삭제 완료")


def schedule_optimization():
    """
    캐시 최적화 스케줄링 (별도 스레드에서 실행)
    """
    import threading
    import time
    
    def optimization_worker():
        """최적화 워커"""
        while True:
            try:
                # 30분마다 최적화 실행
                time.sleep(1800)
                
                # 메모리 최적화
                optimization_result = optimize_memory()
                if optimization_result['status'] == 'optimized':
                    logger.info(f"캐시 최적화 완료: {optimization_result}")
                
                # 오래된 항목 정리
                cleared = clear_old_entries()
                if cleared > 0:
                    logger.info(f"오래된 캐시 정리: {cleared}개 항목 제거")
                
            except Exception as e:
                logger.error(f"캐시 최적화 중 오류: {e}")
                time.sleep(3600)  # 1시간 후 재시도
    
    # 데몬 스레드로 실행
    optimization_thread = threading.Thread(target=optimization_worker, daemon=True)
    optimization_thread.start()
    logger.info("캐시 최적화 스케줄링 시작")


# 캐시 성능 리포트 생성
def generate_performance_report() -> str:
    """
    캐시 성능 리포트 생성
    
    Returns:
        str: 성능 리포트
    """
    try:
        stats = get_cache_stats()
        health = get_cache_health()
        
        report_lines = ["=== 고성능 캐시 성능 리포트 ==="]
        
        # 기본 통계
        report_lines.append(f"\n📊 캐시 통계:")
        report_lines.append(f"  운세 캐시: {stats['fortune_cache_size']}개")
        report_lines.append(f"  콘텐츠 캐시: {stats['content_cache_size']}개")
        report_lines.append(f"  LRU 캐시: {stats['lru_cache_size']}개")
        report_lines.append(f"  총 요청: {stats['total_requests']}회")
        report_lines.append(f"  히트율: {stats['hit_rate']}%")
        
        # 성능 메트릭
        report_lines.append(f"\n⚡ 성능 메트릭:")
        report_lines.append(f"  메모리 사용량: {stats['memory_usage_mb']}MB")
        report_lines.append(f"  압축률: {stats['compression_ratio']}")
        report_lines.append(f"  평균 응답시간: {stats['average_response_time_ms']}ms")
        report_lines.append(f"  압축 횟수: {stats['total_compressions']}회")
        report_lines.append(f"  해제 횟수: {stats['total_decompressions']}회")
        
        # 최적화 정보
        report_lines.append(f"\n✅ 최적화 적용:")
        report_lines.append(f"  - LRU 캐시: 자주 사용되는 항목 우선 보존")
        report_lines.append(f"  - 데이터 압축: 1KB 이상 자동 압축")
        report_lines.append(f"  - 메모리 최적화: 30분마다 자동 실행")
        report_lines.append(f"  - TTL 관리: 만료된 항목 자동 정리")
        
        # 경고사항
        if health['warnings']:
            report_lines.append(f"\n⚠️ 경고:")
            for warning in health['warnings']:
                report_lines.append(f"  - {warning}")
        
        return "\n".join(report_lines)
        
    except Exception as e:
        return f"성능 리포트 생성 실패: {e}"


# 모듈 초기화 시 최적화 스케줄링 시작
if __name__ != "__main__":
    try:
        schedule_optimization()
    except Exception as e:
        logger.warning(f"캐시 최적화 스케줄링 실패: {e}")


def warmup_cache(sheets_manager=None):
    """
    캐시 워밍업 (필수 데이터 미리 로드)
    
    Args:
        sheets_manager: Google Sheets 매니저 (선택사항)
    """
    try:
        logger.info("🔥 캐시 워밍업 시작...")
        
        # 기본 캐시 초기화
        bot_cache.set("warmup_status", "completed", 3600)
        
        # Google Sheets가 있는 경우 운세 문구 미리 로드
        if sheets_manager:
            try:
                # 운세 문구 미리 로드
                def fetch_fortune_phrases():
                    return sheets_manager.get_fortune_phrases()
                
                fortune_phrases = bot_cache.get_fortune_phrases(fetch_fortune_phrases)
                if fortune_phrases:
                    logger.info(f"✅ 운세 문구 {len(fortune_phrases)}개 미리 로드 완료")
                
                # 도움말 항목 미리 로드
                def fetch_help_items():
                    return sheets_manager.get_help_items()
                
                help_items = bot_cache.get_help_items(fetch_help_items)
                if help_items:
                    logger.info(f"✅ 도움말 항목 {len(help_items)}개 미리 로드 완료")
                    
            except Exception as e:
                logger.warning(f"⚠️ Google Sheets 데이터 미리 로드 실패: {e}")
        
        # 기본 통계 초기화
        bot_cache.set("cache_stats", {
            "initialized_at": time.time(),
            "version": "1.0"
        }, 86400)  # 24시간
        
        logger.info("✅ 캐시 워밍업 완료")
        
    except Exception as e:
        logger.error(f"❌ 캐시 워밍업 실패: {e}")
        raise


def start_cache_cleanup_scheduler(interval: int = 300):
    """
    캐시 정리 스케줄러 시작
    
    Args:
        interval: 정리 간격 (초, 기본값: 300초 = 5분)
    """
    try:
        logger.info(f"🔄 캐시 정리 스케줄러 시작 (간격: {interval}초)")
        
        def cleanup_worker():
            """정리 워커"""
            while True:
                try:
                    time.sleep(interval)
                    
                    # 오래된 항목 정리
                    cleared_count = clear_old_entries()
                    if cleared_count > 0:
                        logger.info(f"🧹 캐시 정리: {cleared_count}개 항목 제거")
                    
                    # 메모리 최적화 (30분마다)
                    if int(time.time()) % 1800 < interval:
                        optimization_result = optimize_memory()
                        if optimization_result['status'] == 'optimized':
                            logger.info(f"⚡ 메모리 최적화 완료: {optimization_result.get('memory_saved_mb', 0):.2f}MB 절약")
                    
                except Exception as e:
                    logger.error(f"캐시 정리 중 오류: {e}")
                    time.sleep(60)  # 1분 후 재시도
        
        # 데몬 스레드로 실행
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        
        # 스케줄러 상태 저장
        bot_cache.set("cleanup_scheduler", {
            "started_at": time.time(),
            "interval": interval,
            "status": "running"
        }, 86400)
        
        logger.info("✅ 캐시 정리 스케줄러 시작 완료")
        
    except Exception as e:
        logger.error(f"❌ 캐시 정리 스케줄러 시작 실패: {e}")
        raise


# 테스트 함수
def test_optimized_cache():
    """최적화된 캐시 시스템 테스트"""
    print("=== 고성능 캐시 시스템 테스트 ===")
    
    # 운세 캐시 테스트
    test_user = "test_user"
    test_fortune = "오늘은 좋은 일이 있을 것입니다."
    
    # 저장
    result1 = get_user_daily_fortune(test_user, test_fortune)
    print(f"운세 저장: {result1}")
    
    # 조회
    result2 = get_user_daily_fortune(test_user)
    print(f"운세 조회: {result2}")
    
    # 일반 캐시 테스트
    set_cache("test_key", "test_value", 60)
    cached_value = get_cache("test_key")
    print(f"일반 캐시: {cached_value}")
    
    # 통계 확인
    stats = get_cache_stats()
    print(f"캐시 통계: {stats}")
    
    # 성능 리포트 생성
    report = generate_performance_report()
    print(f"\n{report}")
    
    print("=" * 40)


if __name__ == "__main__":
    test_optimized_cache()