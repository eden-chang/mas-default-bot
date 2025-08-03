"""
구조화된 로깅 설정 모듈 (보완된 버전)
고성능 구조화된 로깅 시스템을 제공합니다.
"""

import json  
import logging
import os
import sys
import threading
import time
import gzip
import pickle
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import pytz
from contextlib import contextmanager
from collections import defaultdict, deque
import hashlib
import uuid

# 경로 설정 (VM 환경 대응)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

try:
    from config.settings import config
except ImportError:
    # VM 환경에서 임포트 실패 시 폴백
    import importlib.util
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.py')
    spec = importlib.util.spec_from_file_location("settings", config_path)
    settings_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(settings_module)
    config = settings_module.config


class LogLevel(Enum):
    """로그 레벨 열거형"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """로그 카테고리 열거형 (보완된 버전)"""
    COMMAND = "command"
    API = "api"
    SHEET = "sheet"
    USER = "user"
    SYSTEM = "system"
    TRANSACTION = "transaction"
    ITEM = "item"
    ERROR = "error"
    PERFORMANCE = "performance"
    SECURITY = "security"
    CACHE = "cache"
    NETWORK = "network"
    DATABASE = "database"
    PLUGIN = "plugin"
    AUDIT = "audit"


class LogFormat(Enum):
    """로그 형식 열거형"""
    TEXT = "text"
    JSON = "json"
    STRUCTURED = "structured"
    COMPRESSED = "compressed"


@dataclass
class LogEntry:
    """로그 엔트리 데이터 클래스 (보완된 버전)"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    level: str = "INFO"
    category: str = "system"
    message: str = ""
    user_id: Optional[str] = None
    username: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    duration: Optional[float] = None
    success: Optional[bool] = None
    source_file: Optional[str] = None
    source_line: Optional[int] = None
    source_function: Optional[str] = None
    stack_trace: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    severity_score: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)
    
    def to_json(self) -> str:
        """JSON 문자열로 변환"""
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)
    
    def get_hash(self) -> str:
        """로그 엔트리의 해시값 반환"""
        content = f"{self.timestamp}{self.level}{self.category}{self.message}{self.user_id}"
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class LogMetrics:
    """로그 메트릭 데이터 클래스"""
    total_logs: int = 0
    logs_by_level: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    logs_by_category: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    logs_by_user: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    average_duration: float = 0.0
    error_rate: float = 0.0
    success_rate: float = 0.0
    last_log_time: Optional[datetime] = None
    peak_log_rate: float = 0.0  # 초당 최대 로그 수


class JSONFormatter(logging.Formatter):
    """JSON 형식 로그 포매터"""
    
    def __init__(self, include_extra_fields: bool = True):
        super().__init__()
        self.include_extra_fields = include_extra_fields
    
    def format(self, record: logging.LogRecord) -> str:
        """JSON 형식으로 포맷팅"""
        log_entry = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'source': {
                'file': record.pathname,
                'line': record.lineno,
                'function': record.funcName
            }
        }
        
        # 추가 필드 포함
        if self.include_extra_fields:
            extra_fields = ['user_id', 'category', 'duration', 'success', 
                          'session_id', 'request_id', 'tags', 'severity_score']
            for field in extra_fields:
                if hasattr(record, field):
                    value = getattr(record, field)
                    if value is not None:
                        log_entry[field] = value
            
            # 예외 정보 포함
            if record.exc_info:
                log_entry['exception'] = {
                    'type': record.exc_info[0].__name__,
                    'message': str(record.exc_info[1]),
                    'traceback': self.formatException(record.exc_info)
                }
        
        return json.dumps(log_entry, ensure_ascii=False, default=str)


class StructuredFormatter(logging.Formatter):
    """구조화된 로그 포매터 (보완된 버전)"""
    
    def __init__(self, include_metadata: bool = True):
        super().__init__()
        self.include_metadata = include_metadata
    
    def format(self, record: logging.LogRecord) -> str:
        """구조화된 로그 포맷"""
        # 기본 정보
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'thread': record.thread,
            'process': record.process
        }
        
        # 메타데이터 포함
        if self.include_metadata:
            metadata = {}
            
            # 사용자 정보
            if hasattr(record, 'user_id'):
                metadata['user_id'] = record.user_id
            if hasattr(record, 'username'):
                metadata['username'] = record.username
            
            # 세션 정보
            if hasattr(record, 'session_id'):
                metadata['session_id'] = record.session_id
            if hasattr(record, 'request_id'):
                metadata['request_id'] = record.request_id
            
            # 성능 정보
            if hasattr(record, 'duration'):
                metadata['duration'] = record.duration
            if hasattr(record, 'success'):
                metadata['success'] = record.success
            
            # 카테고리 및 태그
            if hasattr(record, 'category'):
                metadata['category'] = record.category
            if hasattr(record, 'tags'):
                metadata['tags'] = record.tags
            
            # 심각도 점수
            if hasattr(record, 'severity_score'):
                metadata['severity_score'] = record.severity_score
            
            if metadata:
                log_entry['metadata'] = metadata
        
        # 예외 정보
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        return json.dumps(log_entry, ensure_ascii=False, default=str)


class CompressedFormatter(logging.Formatter):
    """압축된 로그 포매터"""
    
    def __init__(self, compression_level: int = 6):
        super().__init__()
        self.compression_level = compression_level
    
    def format(self, record: logging.LogRecord) -> str:
        """압축된 로그 포맷"""
        # 기본 로그 데이터
        log_data = {
            't': datetime.fromtimestamp(record.created).isoformat(),
            'l': record.levelname,
            'n': record.name,
            'm': record.getMessage(),
            'f': record.funcName,
            'ln': record.lineno
        }
        
        # 추가 필드 (축약형)
        if hasattr(record, 'user_id'):
            log_data['uid'] = record.user_id
        if hasattr(record, 'category'):
            log_data['cat'] = record.category
        if hasattr(record, 'duration'):
            log_data['dur'] = record.duration
        if hasattr(record, 'success'):
            log_data['suc'] = record.success
        
        # JSON 직렬화 후 압축
        json_str = json.dumps(log_data, ensure_ascii=False, separators=(',', ':'))
        compressed = gzip.compress(json_str.encode('utf-8'), self.compression_level)
        
        # Base64 인코딩 (텍스트 파일에 저장 가능)
        import base64
        return base64.b64encode(compressed).decode('ascii')


class LogBuffer:
    """로그 버퍼 (성능 최적화)"""
    
    def __init__(self, max_size: int = 1000, flush_interval: float = 5.0):
        self.max_size = max_size
        self.flush_interval = flush_interval
        self.buffer: deque = deque(maxlen=max_size)
        self.last_flush = time.time()
        self._lock = threading.RLock()
    
    def add(self, log_entry: LogEntry) -> None:
        """로그 엔트리 추가"""
        with self._lock:
            self.buffer.append(log_entry)
    
    def flush(self) -> List[LogEntry]:
        """버퍼 플러시"""
        with self._lock:
            if not self.buffer:
                return []
            
            logs = list(self.buffer)
            self.buffer.clear()
            self.last_flush = time.time()
            return logs
    
    def should_flush(self) -> bool:
        """플러시 여부 확인"""
        return (len(self.buffer) >= self.max_size or 
                time.time() - self.last_flush >= self.flush_interval)
    
    def size(self) -> int:
        """버퍼 크기 반환"""
        return len(self.buffer)


class LogAnalyzer:
    """로그 분석기 (보완된 버전)"""
    
    def __init__(self, log_manager: 'LogManager'):
        self.log_manager = log_manager
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5분 캐시
    
    def analyze_logs(self, hours: int = 24) -> Dict[str, Any]:
        """로그 분석"""
        cache_key = f"analysis_{hours}"
        
        # 캐시 확인
        if cache_key in self._cache:
            cache_time, cache_data = self._cache[cache_key]
            if time.time() - cache_time < self._cache_ttl:
                return cache_data
        
        # 분석 실행
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_logs = [
            log for log in self.log_manager.get_recent_logs(10000)
            if datetime.fromisoformat(log.timestamp) > cutoff_time
        ]
        
        analysis = {
            'period_hours': hours,
            'total_logs': len(recent_logs),
            'logs_by_level': defaultdict(int),
            'logs_by_category': defaultdict(int),
            'logs_by_user': defaultdict(int),
            'error_analysis': self._analyze_errors(recent_logs),
            'performance_analysis': self._analyze_performance(recent_logs),
            'user_activity': self._analyze_user_activity(recent_logs),
            'trends': self._analyze_trends(recent_logs),
            'anomalies': self._detect_anomalies(recent_logs)
        }
        
        # 카운트 집계
        for log in recent_logs:
            analysis['logs_by_level'][log.level] += 1
            analysis['logs_by_category'][log.category] += 1
            if log.user_id:
                analysis['logs_by_user'][log.user_id] += 1
        
        # 캐시 저장
        self._cache[cache_key] = (time.time(), analysis)
        
        return analysis
    
    def _analyze_errors(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """오류 분석"""
        error_logs = [log for log in logs if log.level in ['ERROR', 'CRITICAL']]
        
        error_types = defaultdict(int)
        error_messages = defaultdict(int)
        error_users = defaultdict(int)
        
        for log in error_logs:
            # 오류 타입 분석
            if log.details and 'error_type' in log.details:
                error_types[log.details['error_type']] += 1
            
            # 오류 메시지 분석
            error_messages[log.message] += 1
            
            # 오류 발생 사용자 분석
            if log.user_id:
                error_users[log.user_id] += 1
        
        return {
            'total_errors': len(error_logs),
            'error_rate': len(error_logs) / len(logs) if logs else 0,
            'error_types': dict(error_types),
            'common_error_messages': dict(sorted(error_messages.items(), key=lambda x: x[1], reverse=True)[:10]),
            'users_with_errors': dict(error_users),
            'error_trend': self._calculate_trend([log for log in logs if log.level == 'ERROR'])
        }
    
    def _analyze_performance(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """성능 분석"""
        performance_logs = [log for log in logs if log.duration is not None]
        
        if not performance_logs:
            return {'total_operations': 0, 'average_duration': 0}
        
        durations = [log.duration for log in performance_logs]
        categories = defaultdict(list)
        
        for log in performance_logs:
            categories[log.category].append(log.duration)
        
        return {
            'total_operations': len(performance_logs),
            'average_duration': sum(durations) / len(durations),
            'min_duration': min(durations),
            'max_duration': max(durations),
            'duration_by_category': {cat: sum(durs) / len(durs) for cat, durs in categories.items()},
            'slow_operations': [log for log in performance_logs if log.duration > 5.0]  # 5초 이상
        }
    
    def _analyze_user_activity(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """사용자 활동 분석"""
        user_logs = [log for log in logs if log.user_id]
        
        user_activity = defaultdict(lambda: {
            'total_actions': 0,
            'last_activity': None,
            'categories': defaultdict(int),
            'success_rate': 0,
            'error_count': 0
        })
        
        for log in user_logs:
            user_id = log.user_id
            user_activity[user_id]['total_actions'] += 1
            user_activity[user_id]['categories'][log.category] += 1
            
            if log.timestamp:
                log_time = datetime.fromisoformat(log.timestamp)
                if (user_activity[user_id]['last_activity'] is None or 
                    log_time > user_activity[user_id]['last_activity']):
                    user_activity[user_id]['last_activity'] = log_time
            
            if log.success is not None:
                if log.success:
                    user_activity[user_id]['success_rate'] += 1
                else:
                    user_activity[user_id]['error_count'] += 1
        
        # 성공률 계산
        for user_data in user_activity.values():
            if user_data['total_actions'] > 0:
                user_data['success_rate'] = user_data['success_rate'] / user_data['total_actions']
        
        return {
            'active_users': len(user_activity),
            'user_activity': dict(user_activity),
            'most_active_users': sorted(
                user_activity.items(), 
                key=lambda x: x[1]['total_actions'], 
                reverse=True
            )[:10]
        }
    
    def _analyze_trends(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """트렌드 분석"""
        if not logs:
            return {}
        
        # 시간별 분포
        hourly_distribution = defaultdict(int)
        for log in logs:
            if log.timestamp:
                hour = datetime.fromisoformat(log.timestamp).hour
                hourly_distribution[hour] += 1
        
        # 레벨별 트렌드
        level_trends = defaultdict(list)
        for log in logs:
            if log.timestamp:
                level_trends[log.level].append(datetime.fromisoformat(log.timestamp))
        
        return {
            'hourly_distribution': dict(hourly_distribution),
            'level_trends': {level: len(times) for level, times in level_trends.items()},
            'peak_hours': sorted(hourly_distribution.items(), key=lambda x: x[1], reverse=True)[:3]
        }
    
    def _detect_anomalies(self, logs: List[LogEntry]) -> List[Dict[str, Any]]:
        """이상 징후 탐지"""
        anomalies = []
        
        if not logs:
            return anomalies
        
        # 오류 급증 탐지
        error_logs = [log for log in logs if log.level in ['ERROR', 'CRITICAL']]
        if len(error_logs) > len(logs) * 0.1:  # 10% 이상 오류
            anomalies.append({
                'type': 'high_error_rate',
                'description': f"오류율이 {len(error_logs)/len(logs)*100:.1f}%로 높습니다",
                'severity': 'high'
            })
        
        # 성능 저하 탐지
        slow_logs = [log for log in logs if log.duration and log.duration > 10.0]
        if slow_logs:
            anomalies.append({
                'type': 'performance_degradation',
                'description': f"{len(slow_logs)}개의 느린 작업이 감지되었습니다",
                'severity': 'medium'
            })
        
        # 사용자 활동 이상 탐지
        user_activity = defaultdict(int)
        for log in logs:
            if log.user_id:
                user_activity[log.user_id] += 1
        
        if user_activity:
            avg_activity = sum(user_activity.values()) / len(user_activity)
            high_activity_users = [uid for uid, count in user_activity.items() if count > avg_activity * 3]
            
            if high_activity_users:
                anomalies.append({
                    'type': 'unusual_user_activity',
                    'description': f"{len(high_activity_users)}명의 사용자가 비정상적으로 많은 활동을 보입니다",
                    'severity': 'low'
                })
        
        return anomalies
    
    def _calculate_trend(self, logs: List[LogEntry]) -> str:
        """트렌드 계산"""
        if len(logs) < 2:
            return "stable"
        
        # 시간순 정렬
        sorted_logs = sorted(logs, key=lambda x: x.timestamp)
        mid_point = len(sorted_logs) // 2
        
        first_half = len([log for log in sorted_logs[:mid_point] if log.level == 'ERROR'])
        second_half = len([log for log in sorted_logs[mid_point:] if log.level == 'ERROR'])
        
        if second_half > first_half * 1.5:
            return "increasing"
        elif first_half > second_half * 1.5:
            return "decreasing"
        else:
            return "stable"


class LogManager:
    """로그 관리자 (구조화된 버전)"""
    
    _instance: Optional['LogManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'LogManager':
        """싱글톤 패턴 구현 (스레드 안전)"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """로그 관리자 초기화"""
        if not hasattr(self, '_initialized'):
            self._loggers: Dict[str, logging.Logger] = {}
            self._handlers: Dict[str, logging.Handler] = {}
            self._formatters: Dict[str, logging.Formatter] = {}
            self._log_entries: List[LogEntry] = []
            self._performance_metrics: Dict[str, List[float]] = {}
            self._log_buffer = LogBuffer()
            self._analyzer = LogAnalyzer(self)
            self._metrics = LogMetrics()
            self._setup_main_logger()
            self._initialized = True
    
    def _setup_main_logger(self) -> None:
        """메인 로거 설정"""
        # 메인 로거 생성
        self._main_logger = logging.getLogger('mastodon_bot')
        self._main_logger.setLevel(getattr(logging, config.LOG_LEVEL.upper()))
        
        # 핸들러 중복 방지
        if self._main_logger.handlers:
            self._main_logger.handlers.clear()
        
        # 핸들러 설정
        self._setup_handlers()
        
        # 외부 로거 설정
        self._setup_external_loggers()
        
        # 초기화 로그
        self._log_startup_info()
    
    def _setup_handlers(self) -> None:
        """핸들러 설정 (보완된 버전)"""
        # 파일 핸들러 (텍스트)
        self._setup_text_file_handler()
        
        # JSON 파일 핸들러
        self._setup_json_file_handler()
        
        # 압축 파일 핸들러
        self._setup_compressed_file_handler()
        
        # 콘솔 핸들러
        if config.ENABLE_CONSOLE_LOG:
            self._setup_console_handler()
        
        # 구조화된 로그 핸들러
        if hasattr(config, 'ENABLE_STRUCTURED_LOG') and config.ENABLE_STRUCTURED_LOG:
            self._setup_structured_handler()
    
    def _setup_text_file_handler(self) -> None:
        """텍스트 파일 핸들러 설정"""
        try:
            log_path = Path(config.LOG_FILE_PATH)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = RotatingFileHandler(
                filename=config.LOG_FILE_PATH,
                maxBytes=getattr(config, 'LOG_MAX_BYTES', 10 * 1024 * 1024),
                backupCount=getattr(config, 'LOG_BACKUP_COUNT', 5),
                encoding='utf-8'
            )
            
            formatter = logging.Formatter(
                fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)
            
            self._main_logger.addHandler(file_handler)
            self._handlers['text_file'] = file_handler
            
        except Exception as e:
            print(f"⚠️ 텍스트 파일 핸들러 설정 실패: {e}")
    
    def _setup_json_file_handler(self) -> None:
        """JSON 파일 핸들러 설정"""
        try:
            json_log_path = Path(config.LOG_FILE_PATH).parent / 'logs.json'
            
            json_handler = RotatingFileHandler(
                filename=str(json_log_path),
                maxBytes=getattr(config, 'LOG_MAX_BYTES', 10 * 1024 * 1024),
                backupCount=getattr(config, 'LOG_BACKUP_COUNT', 5),
                encoding='utf-8'
            )
            
            json_formatter = JSONFormatter()
            json_handler.setFormatter(json_formatter)
            json_handler.setLevel(logging.INFO)
            
            self._main_logger.addHandler(json_handler)
            self._handlers['json_file'] = json_handler
            
        except Exception as e:
            print(f"⚠️ JSON 파일 핸들러 설정 실패: {e}")
    
    def _setup_compressed_file_handler(self) -> None:
        """압축 파일 핸들러 설정"""
        try:
            compressed_log_path = Path(config.LOG_FILE_PATH).parent / 'logs.compressed'
            
            compressed_handler = RotatingFileHandler(
                filename=str(compressed_log_path),
                maxBytes=getattr(config, 'LOG_MAX_BYTES', 10 * 1024 * 1024),
                backupCount=getattr(config, 'LOG_BACKUP_COUNT', 5),
                encoding='utf-8'
            )
            
            compressed_formatter = CompressedFormatter()
            compressed_handler.setFormatter(compressed_formatter)
            compressed_handler.setLevel(logging.INFO)
            
            self._main_logger.addHandler(compressed_handler)
            self._handlers['compressed_file'] = compressed_handler
            
        except Exception as e:
            print(f"⚠️ 압축 파일 핸들러 설정 실패: {e}")
    
    def _setup_console_handler(self) -> None:
        """콘솔 핸들러 설정"""
        try:
            console_handler = logging.StreamHandler(sys.stdout)
            
            if getattr(config, 'DEBUG_MODE', False):
                console_formatter = logging.Formatter(
                    fmt='%(asctime)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s',
                    datefmt='%H:%M:%S'
                )
            else:
                console_formatter = logging.Formatter(
                    fmt='%(asctime)s | %(levelname)-8s | %(message)s',
                    datefmt='%H:%M:%S'
                )
            
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(getattr(logging, config.LOG_LEVEL.upper()))
            
            self._main_logger.addHandler(console_handler)
            self._handlers['console'] = console_handler
            
        except Exception as e:
            print(f"⚠️ 콘솔 핸들러 설정 실패: {e}")
    
    def _setup_structured_handler(self) -> None:
        """구조화된 로그 핸들러 설정"""
        try:
            structured_path = Path(config.LOG_FILE_PATH).parent / 'structured.log'
            structured_handler = RotatingFileHandler(
                filename=str(structured_path),
                maxBytes=getattr(config, 'LOG_MAX_BYTES', 10 * 1024 * 1024),
                backupCount=getattr(config, 'LOG_BACKUP_COUNT', 5),
                encoding='utf-8'
            )
            
            structured_formatter = StructuredFormatter()
            structured_handler.setFormatter(structured_formatter)
            structured_handler.setLevel(logging.INFO)
            
            self._main_logger.addHandler(structured_handler)
            self._handlers['structured'] = structured_handler
            
        except Exception as e:
            print(f"⚠️ 구조화된 로그 핸들러 설정 실패: {e}")
    
    def _setup_external_loggers(self) -> None:
        """외부 라이브러리 로거 설정"""
        external_loggers = {
            'gspread': logging.WARNING,
            'requests': logging.WARNING,
            'urllib3': logging.WARNING,
            'mastodon': logging.INFO,
            'oauthlib': logging.WARNING,
            'requests_oauthlib': logging.WARNING,
        }
        
        for logger_name, level in external_loggers.items():
            try:
                external_logger = logging.getLogger(logger_name)
                external_logger.setLevel(level)
            except Exception as e:
                print(f"⚠️ 외부 로거 설정 실패 {logger_name}: {e}")
    
    def _log_startup_info(self) -> None:
        """시작 정보 로깅"""
        self._main_logger.info("=" * 60)
        self._main_logger.info("구조화된 로깅 시스템 초기화 완료")
        self._main_logger.info(f"로그 레벨: {config.LOG_LEVEL}")
        self._main_logger.info(f"파일 로깅: {config.LOG_FILE_PATH}")
        self._main_logger.info(f"콘솔 로깅: {config.ENABLE_CONSOLE_LOG}")
        self._main_logger.info(f"디버그 모드: {getattr(config, 'DEBUG_MODE', False)}")
        self._main_logger.info(f"구조화된 로그: {getattr(config, 'ENABLE_STRUCTURED_LOG', False)}")
        self._main_logger.info("=" * 60)
    
    @property
    def logger(self) -> logging.Logger:
        """메인 로거 반환"""
        return self._main_logger
    
    def get_logger(self, name: str) -> logging.Logger:
        """특정 이름의 로거 반환"""
        if name not in self._loggers:
            self._loggers[name] = logging.getLogger(name)
        return self._loggers[name]
    
    def log_structured(self, level: str, category: LogCategory, message: str, 
                      user_id: Optional[str] = None, username: Optional[str] = None,
                      session_id: Optional[str] = None, request_id: Optional[str] = None,
                      details: Optional[Dict[str, Any]] = None, duration: Optional[float] = None,
                      success: Optional[bool] = None, tags: Optional[List[str]] = None,
                      severity_score: Optional[int] = None, **kwargs) -> None:
        """구조화된 로깅"""
        # 로그 엔트리 생성
        log_entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level.upper(),
            category=category.value,
            message=message,
            user_id=user_id,
            username=username,
            session_id=session_id,
            request_id=request_id,
            details=details,
            duration=duration,
            success=success,
            tags=tags or [],
            severity_score=severity_score
        )
        
        # 버퍼에 추가
        self._log_buffer.add(log_entry)
        
        # 메트릭 업데이트
        self._update_metrics(log_entry)
        
        # 로그 레코드 생성 및 처리
        record = logging.LogRecord(
            name=self._main_logger.name,
            level=getattr(logging, level.upper()),
            pathname='',
            lineno=0,
            msg=message,
            args=(),
            exc_info=None
        )
        
        # 추가 필드 설정
        for field, value in log_entry.to_dict().items():
            if value is not None and field not in ['timestamp', 'level', 'category', 'message']:
                setattr(record, field, value)
        
        self._main_logger.handle(record)
        
        # 버퍼 플러시 확인
        if self._log_buffer.should_flush():
            self._flush_buffer()
    
    def log_sheet_operation(self, operation: str, worksheet: str, success: bool, error: str = None):
        from .logging_config import LogLevel
        self.log_structured(
            level=LogLevel.INFO.value if success else LogLevel.ERROR.value,
            category=LogCategory.SHEET,
            message=f"{operation} - 워크시트: {worksheet}" + (f" - 오류: {error}" if error else ""),
            success=success,
            details={"worksheet": worksheet, "operation": operation, "error": error}
        )
    
    def _update_metrics(self, log_entry: LogEntry) -> None:
        """메트릭 업데이트"""
        self._metrics.total_logs += 1
        self._metrics.logs_by_level[log_entry.level] += 1
        self._metrics.logs_by_category[log_entry.category] += 1
        
        if log_entry.user_id:
            self._metrics.logs_by_user[log_entry.user_id] += 1
        
        if log_entry.duration is not None:
            # 평균 지속시간 업데이트
            current_avg = self._metrics.average_duration
            total_logs = self._metrics.total_logs
            new_avg = (current_avg * (total_logs - 1) + log_entry.duration) / total_logs
            self._metrics.average_duration = new_avg
        
        if log_entry.success is not None:
            # 성공률 업데이트
            if log_entry.success:
                self._metrics.success_rate = (self._metrics.success_rate * (self._metrics.total_logs - 1) + 1) / self._metrics.total_logs
            else:
                self._metrics.success_rate = (self._metrics.success_rate * (self._metrics.total_logs - 1)) / self._metrics.total_logs
        
        # 오류율 업데이트
        error_logs = self._metrics.logs_by_level.get('ERROR', 0) + self._metrics.logs_by_level.get('CRITICAL', 0)
        self._metrics.error_rate = error_logs / self._metrics.total_logs if self._metrics.total_logs > 0 else 0
        
        self._metrics.last_log_time = datetime.now()
    
    def _flush_buffer(self) -> None:
        """버퍼 플러시"""
        flushed_logs = self._log_buffer.flush()
        if flushed_logs:
            # 로그 엔트리 저장
            self._log_entries.extend(flushed_logs)
            
            # 최근 10000개만 유지
            if len(self._log_entries) > 10000:
                self._log_entries = self._log_entries[-10000:]
    
    def get_analyzer(self) -> LogAnalyzer:
        """로그 분석기 반환"""
        return self._analyzer
    
    def get_metrics(self) -> LogMetrics:
        """로그 메트릭 반환"""
        return self._metrics
    
    def get_recent_logs(self, limit: int = 1000) -> List[LogEntry]:
        """최근 로그 반환"""
        return self._log_entries[-limit:]
    
    def clear_logs(self) -> None:
        """로그 캐시 클리어"""
        self._log_entries.clear()
        self._performance_metrics.clear()
        self._metrics = LogMetrics()
    
    def shutdown(self) -> None:
        """로그 시스템 종료"""
        # 버퍼 플러시
        self._flush_buffer()
        
        self._main_logger.info("구조화된 로깅 시스템 종료됨")
        
        # 모든 핸들러 정리
        for handler in self._handlers.values():
            try:
                handler.close()
            except Exception as e:
                print(f"핸들러 종료 오류: {e}")


# 전역 로그 관리자 인스턴스
log_manager = LogManager()
logger = log_manager.logger


def setup_logging() -> LogManager:
    """로깅 시스템 설정"""
    return log_manager


def get_logger() -> logging.Logger:
    """로거 반환"""
    return logger


# 편의 함수들 (보완된 버전)
def log_structured(level: str, category: LogCategory, message: str, **kwargs) -> None:
    """구조화된 로깅"""
    log_manager.log_structured(level, category, message, **kwargs)


def log_info(message: str, **kwargs) -> None:
    """정보 로그"""
    logger.info(message, **kwargs)


def log_warning(message: str, **kwargs) -> None:
    """경고 로그"""
    logger.warning(message, **kwargs)


def log_error(message: str, exc_info: bool = None, **kwargs) -> None:
    """에러 로그"""
    if exc_info is None:
        exc_info = getattr(config, 'DEBUG_MODE', False)
    logger.error(message, exc_info=exc_info, **kwargs)


def log_debug(message: str, **kwargs) -> None:
    """디버그 로그"""
    logger.debug(message, **kwargs)


def log_critical(message: str, **kwargs) -> None:
    """치명적 오류 로그"""
    logger.critical(message, **kwargs)


def shutdown_logging() -> None:
    """로깅 시스템 종료"""
    log_manager.shutdown()


# 컨텍스트 매니저 (보완된 버전)
@contextmanager
def log_context(operation: str, category: LogCategory = LogCategory.SYSTEM, 
                user_id: Optional[str] = None, **context):
    """로깅 컨텍스트 매니저"""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # 시작 로그
    context_str = " | ".join([f"{k}: {v}" for k, v in context.items()])
    log_structured(
        'DEBUG', category,
        f"시작: {operation} | {context_str}",
        user_id=user_id, request_id=request_id, **context
    )
    
    try:
        yield
        # 성공 로그
        duration = time.time() - start_time
        log_structured(
            'DEBUG', category,
            f"완료: {operation} | 소요시간: {duration:.3f}s",
            user_id=user_id, request_id=request_id, duration=duration, success=True, **context
        )
    except Exception as e:
        # 실패 로그
        duration = time.time() - start_time
        log_structured(
            'ERROR', category,
            f"실패: {operation} | 소요시간: {duration:.3f}s | 오류: {e}",
            user_id=user_id, request_id=request_id, duration=duration, success=False, **context
        )
        raise


# 성능 측정 데코레이터 (보완된 버전)
def log_performance(operation: str, category: LogCategory = LogCategory.PERFORMANCE):
    """성능 측정 데코레이터"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            start_time = time.time()
            request_id = str(uuid.uuid4())
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                log_structured(
                    'DEBUG', category,
                    f"성능 측정: {operation}",
                    duration=duration, success=True, request_id=request_id
                )
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                log_structured(
                    'ERROR', category,
                    f"성능 측정 실패: {operation} | 오류: {e}",
                    duration=duration, success=False, request_id=request_id
                )
                
                raise
        return wrapper
    return decorator


# 로그 분석 및 통계 기능
def get_log_analysis(hours: int = 24) -> Dict[str, Any]:
    """로그 분석 결과 반환"""
    return log_manager.get_analyzer().analyze_logs(hours)


def get_log_metrics() -> LogMetrics:
    """로그 메트릭 반환"""
    return log_manager.get_metrics()


def get_log_summary(hours: int = 24) -> Dict[str, Any]:
    """로그 요약 정보"""
    analysis = get_log_analysis(hours)
    metrics = get_log_metrics()
    
    return {
        'analysis': analysis,
        'metrics': {
            'total_logs': metrics.total_logs,
            'average_duration': metrics.average_duration,
            'error_rate': metrics.error_rate,
            'success_rate': metrics.success_rate,
            'last_log_time': metrics.last_log_time.isoformat() if metrics.last_log_time else None
        },
        'period_hours': hours,
        'generated_at': datetime.now().isoformat()
    }


# 로그 시스템 상태 확인
def check_log_health() -> Dict[str, Any]:
    """로그 시스템 상태 확인"""
    try:
        metrics = get_log_metrics()
        analysis = get_log_analysis(1)  # 1시간 분석
        
        health_status = {
            'status': 'healthy',
            'errors': [],
            'warnings': [],
            'details': {
                'total_logs': metrics.total_logs,
                'error_rate': metrics.error_rate,
                'success_rate': metrics.success_rate,
                'recent_anomalies': analysis.get('anomalies', [])
            }
        }
        
        # 오류율 체크
        if metrics.error_rate > 0.1:  # 10% 이상
            health_status['warnings'].append(f"높은 오류율: {metrics.error_rate:.1%}")
        
        # 성공률 체크
        if metrics.success_rate < 0.9:  # 90% 미만
            health_status['warnings'].append(f"낮은 성공률: {metrics.success_rate:.1%}")
        
        # 이상 징후 체크
        anomalies = analysis.get('anomalies', [])
        for anomaly in anomalies:
            if anomaly['severity'] == 'high':
                health_status['errors'].append(anomaly['description'])
            else:
                health_status['warnings'].append(anomaly['description'])
        
        if health_status['errors']:
            health_status['status'] = 'error'
        elif health_status['warnings']:
            health_status['status'] = 'warning'
        
        return health_status
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


# 로그 시스템 최적화
def optimize_log_system() -> Dict[str, Any]:
    """로그 시스템 최적화"""
    try:
        optimization_result = {
            'actions_taken': [],
            'memory_saved': 0,
            'performance_improved': False
        }
        
        # 1. 버퍼 플러시
        initial_buffer_size = log_manager._log_buffer.size()
        log_manager._flush_buffer()
        final_buffer_size = log_manager._log_buffer.size()
        
        if initial_buffer_size > 0:
            optimization_result['actions_taken'].append(f"버퍼 플러시: {initial_buffer_size}개 로그")
        
        # 2. 오래된 로그 정리
        initial_log_count = len(log_manager.get_recent_logs())
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        recent_logs = log_manager.get_recent_logs(10000)
        filtered_logs = [
            log for log in recent_logs
            if datetime.fromisoformat(log.timestamp) > cutoff_time
        ]
        
        log_manager._log_entries = filtered_logs[-5000:]  # 최근 5000개만 유지
        final_log_count = len(log_manager.get_recent_logs())
        
        if initial_log_count > final_log_count:
            optimization_result['actions_taken'].append(f"오래된 로그 정리: {initial_log_count - final_log_count}개 제거")
        
        # 3. 메트릭 정리
        log_manager._metrics = LogMetrics()
        
        optimization_result['memory_saved'] = (initial_log_count - final_log_count) * 1024  # 대략적인 메모리 절약
        optimization_result['performance_improved'] = True
        
        return optimization_result
        
    except Exception as e:
        return {
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


# 애플리케이션 종료 시 cleanup
import atexit
atexit.register(shutdown_logging)


# 전역 로그 매니저 인스턴스 (백워드 호환성)
bot_logger = log_manager