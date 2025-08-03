"""
사용자 데이터 모델
사용자 정보를 관리하는 데이터 클래스들을 정의합니다.
"""

import os
import sys
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Union, TypeVar, Generic
from datetime import datetime, timedelta
from enum import Enum
import pytz
from collections import defaultdict
import time
import re

# 경로 설정 (VM 환경 대응)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

try:
    from config.settings import config
    from utils.error_handling import UserNotFoundError, UserValidationError
except ImportError:
    # VM 환경에서 임포트 실패 시 폴백
    import importlib.util
    
    # config 로드
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.py')
    spec = importlib.util.spec_from_file_location("settings", config_path)
    settings_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(settings_module)
    config = settings_module.config
    
    # 기본 예외 클래스들
    class UserNotFoundError(Exception):
        """사용자를 찾을 수 없을 때 발생하는 예외"""
        def __init__(self, user_id: str, message: str = "사용자를 찾을 수 없습니다"):
            self.user_id = user_id
            self.message = message
            super().__init__(f"{message}: {user_id}")
    
    class UserValidationError(Exception):
        """사용자 데이터 검증 실패 시 발생하는 예외"""
        def __init__(self, user_id: str, error_code: str, message: str = "사용자 데이터 검증 실패"):
            self.user_id = user_id
            self.error_code = error_code
            self.message = message
            super().__init__(f"{message} ({error_code}): {user_id}")


class UserStatus(Enum):
    """사용자 상태 열거형"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class UserRole(Enum):
    """사용자 역할 열거형"""
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    BOT = "bot"


T = TypeVar('T')


@dataclass
class User:
    """사용자 정보 모델"""
    
    id: str                              # 마스토돈 사용자 ID
    name: str                            # 사용자 이름
    created_at: Optional[datetime] = None  # 등록 시간
    last_active: Optional[datetime] = None # 마지막 활동 시간
    command_count: int = 0               # 총 명령어 사용 횟수
    status: UserStatus = UserStatus.ACTIVE  # 사용자 상태
    role: UserRole = UserRole.USER       # 사용자 역할
    additional_data: Dict[str, Any] = field(default_factory=dict)  # 추가 데이터
    
    def __post_init__(self):
        """초기화 후 처리"""
        if self.created_at is None:
            self.created_at = self._get_current_time()
        if self.last_active is None:
            self.last_active = self.created_at
        
        # ID 정규화 (@ 제거)
        if self.id.startswith('@'):
            self.id = self.id[1:]
    
    @classmethod
    def from_sheet_data(cls, data: Dict[str, Any]) -> 'User':
        """
        Google Sheets 데이터에서 User 객체 생성
        
        Args:
            data: 시트에서 가져온 행 데이터
            
        Returns:
            User: 생성된 사용자 객체
            
        Raises:
            UserValidationError: 필수 데이터가 없는 경우
        """
        if not data:
            raise UserValidationError("", "empty_data", "빈 데이터입니다")
        
        # 필수 필드 검증
        user_id = str(data.get('아이디', '')).strip()
        user_name = str(data.get('이름', '')).strip()
        
        if not user_id:
            raise UserValidationError("", "missing_id", "사용자 ID가 없습니다")
        
        if not user_name:
            raise UserValidationError(user_id, "missing_name", "사용자 이름이 없습니다")
        
        # 추가 데이터 수집 (아이디, 이름 제외한 모든 컬럼)
        additional_data = {}
        for key, value in data.items():
            if key not in ['아이디', '이름'] and value is not None:
                additional_data[key] = str(value).strip()
        
        return cls(
            id=user_id,
            name=user_name,
            additional_data=additional_data
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """
        딕셔너리에서 User 객체 생성 (캐시 데이터 등에서 사용)
        
        Args:
            data: 사용자 데이터 딕셔너리
            
        Returns:
            User: 생성된 사용자 객체
        """
        # datetime 문자열을 datetime 객체로 변환
        created_at = None
        last_active = None
        
        if 'created_at' in data and data['created_at']:
            created_at = cls._parse_datetime(data['created_at'])
        
        if 'last_active' in data and data['last_active']:
            last_active = cls._parse_datetime(data['last_active'])
        
        # 상태 및 역할 파싱
        status = UserStatus.ACTIVE
        role = UserRole.USER
        
        if 'status' in data:
            try:
                status = UserStatus(data['status'])
            except ValueError:
                pass
        
        if 'role' in data:
            try:
                role = UserRole(data['role'])
            except ValueError:
                pass
        
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            created_at=created_at,
            last_active=last_active,
            command_count=data.get('command_count', 0),
            status=status,
            role=role,
            additional_data=data.get('additional_data', {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        User 객체를 딕셔너리로 변환 (캐싱, 직렬화용)
        
        Returns:
            Dict: 사용자 데이터 딕셔너리
        """
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_active': self.last_active.isoformat() if self.last_active else None,
            'command_count': self.command_count,
            'status': self.status.value,
            'role': self.role.value,
            'additional_data': self.additional_data
        }
    
    def to_sheet_format(self) -> Dict[str, Any]:
        """
        Google Sheets 형식으로 변환
        
        Returns:
            Dict: 시트 저장용 데이터
        """
        sheet_data = {
            '아이디': self.id,
            '이름': self.name
        }
        
        # 추가 데이터 병합
        sheet_data.update(self.additional_data)
        
        return sheet_data
    
    def update_activity(self, command_executed: bool = True) -> None:
        """
        사용자 활동 업데이트
        
        Args:
            command_executed: 명령어 실행 여부
        """
        self.last_active = self._get_current_time()
        if command_executed:
            self.command_count += 1
    
    def is_valid(self) -> bool:
        """
        사용자 데이터 유효성 검사
        
        Returns:
            bool: 유효성 여부
        """
        # ID는 반드시 있어야 함
        if not self.id or not self.id.strip():
            return False
        
        # 빈 사용자(등록되지 않은 사용자)는 ID만 있으면 유효
        if not self.name or not self.name.strip():
            # ID가 유효한 형식인지만 확인
            return validate_user_id(self.id)
        
        # 정상 사용자는 ID, 이름 모두 있어야 하고 정지되지 않아야 함
        return (
            self.name and self.name.strip() and
            self.status != UserStatus.SUSPENDED
        )
    
    def is_active(self) -> bool:
        """
        사용자가 활성 상태인지 확인
        
        Returns:
            bool: 활성 상태 여부
        """
        return self.status == UserStatus.ACTIVE
    
    def can_use_commands(self) -> bool:
        """
        사용자가 명령어를 사용할 수 있는지 확인
        
        Returns:
            bool: 명령어 사용 가능 여부
        """
        return self.is_valid() and self.is_active()
    
    def get_display_name(self) -> str:
        """
        표시용 이름 반환 (이름이 없으면 ID 사용)
        
        Returns:
            str: 표시용 이름
        """
        return self.name if self.name else self.id
    
    def get_activity_summary(self) -> Dict[str, Any]:
        """
        사용자 활동 요약 정보 반환
        
        Returns:
            Dict: 활동 요약
        """
        now = self._get_current_time()
        
        # 마지막 활동으로부터 경과 시간 계산
        if self.last_active:
            inactive_duration = now - self.last_active
            inactive_days = inactive_duration.days
            inactive_hours = inactive_duration.seconds // 3600
        else:
            inactive_days = None
            inactive_hours = None
        
        # 등록 후 경과 시간 계산
        if self.created_at:
            member_duration = now - self.created_at
            member_days = member_duration.days
        else:
            member_days = None
        
        return {
            'user_id': self.id,
            'user_name': self.name,
            'command_count': self.command_count,
            'member_days': member_days,
            'inactive_days': inactive_days,
            'inactive_hours': inactive_hours,
            'last_active': self.last_active.strftime('%Y-%m-%d %H:%M:%S') if self.last_active else None,
            'status': self.status.value,
            'role': self.role.value
        }
    
    def has_additional_data(self, key: str) -> bool:
        """
        특정 추가 데이터 보유 여부 확인
        
        Args:
            key: 확인할 데이터 키
            
        Returns:
            bool: 보유 여부
        """
        return key in self.additional_data and self.additional_data[key]
    
    def get_additional_data(self, key: str, default: Any = None) -> Any:
        """
        추가 데이터 조회
        
        Args:
            key: 데이터 키
            default: 기본값
            
        Returns:
            Any: 데이터 값
        """
        return self.additional_data.get(key, default)
    
    def set_additional_data(self, key: str, value: Any) -> None:
        """
        추가 데이터 설정
        
        Args:
            key: 데이터 키
            value: 설정할 값
        """
        self.additional_data[key] = value
    
    def remove_additional_data(self, key: str) -> bool:
        """
        추가 데이터 제거
        
        Args:
            key: 제거할 데이터 키
            
        Returns:
            bool: 제거 성공 여부
        """
        if key in self.additional_data:
            del self.additional_data[key]
            return True
        return False
    
    def get_permission_level(self) -> int:
        """
        사용자 권한 레벨 반환
        
        Returns:
            int: 권한 레벨 (0: 일반 사용자, 1: 모더레이터, 2: 관리자)
        """
        if self.role == UserRole.ADMIN:
            return 2
        elif self.role == UserRole.MODERATOR:
            return 1
        else:
            return 0
    
    def has_permission(self, required_level: int) -> bool:
        """
        특정 권한 레벨 보유 여부 확인
        
        Args:
            required_level: 필요한 권한 레벨
            
        Returns:
            bool: 권한 보유 여부
        """
        return self.get_permission_level() >= required_level
    
    @staticmethod
    def _get_current_time() -> datetime:
        """현재 KST 시간 반환"""
        return datetime.now(pytz.timezone('Asia/Seoul'))
    
    @staticmethod
    def _parse_datetime(datetime_str: str) -> Optional[datetime]:
        """
        문자열을 datetime 객체로 파싱
        
        Args:
            datetime_str: datetime 문자열
            
        Returns:
            Optional[datetime]: 파싱된 datetime 또는 None
        """
        if not datetime_str:
            return None
        
        try:
            # ISO 형식 파싱 시도
            if 'T' in datetime_str:
                return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            else:
                # 일반적인 형식 파싱 시도
                return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return None
    
    def __str__(self) -> str:
        """문자열 표현 - 사용자 ID만 반환"""
        return self.id
    
    def __repr__(self) -> str:
        """개발자용 문자열 표현"""
        return (f"User(id='{self.id}', name='{self.name}', "
                f"command_count={self.command_count}, "
                f"status={self.status.value}, "
                f"last_active={self.last_active})")
    
    def get_info_string(self) -> str:
        """상세 정보 문자열 반환 (기존 __str__ 기능)"""
        return f"User(id='{self.id}', name='{self.name}', commands={self.command_count})"


@dataclass
class UserStats:
    """사용자 통계 정보"""
    
    total_users: int = 0
    active_users_today: int = 0
    active_users_week: int = 0
    total_commands: int = 0
    most_active_user: Optional[str] = None
    most_active_commands: int = 0
    newest_user: Optional[str] = None
    suspended_users: int = 0
    moderator_count: int = 0
    admin_count: int = 0
    
    @classmethod
    def from_users(cls, users: List[User]) -> 'UserStats':
        """
        사용자 리스트에서 통계 생성
        
        Args:
            users: 사용자 리스트
            
        Returns:
            UserStats: 통계 객체
        """
        if not users:
            return cls()
        
        now = datetime.now(pytz.timezone('Asia/Seoul'))
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        
        active_today = 0
        active_week = 0
        total_commands = 0
        most_active_user = None
        most_active_commands = 0
        newest_user = None
        newest_time = None
        suspended_users = 0
        moderator_count = 0
        admin_count = 0
        
        for user in users:
            # 총 명령어 수 누적
            total_commands += user.command_count
            
            # 가장 활발한 사용자 찾기
            if user.command_count > most_active_commands:
                most_active_commands = user.command_count
                most_active_user = user.name
            
            # 가장 최근 사용자 찾기
            if user.created_at and (newest_time is None or user.created_at > newest_time):
                newest_time = user.created_at
                newest_user = user.name
            
            # 상태별 카운트
            if user.status == UserStatus.SUSPENDED:
                suspended_users += 1
            elif user.role == UserRole.MODERATOR:
                moderator_count += 1
            elif user.role == UserRole.ADMIN:
                admin_count += 1
            
            # 활성 사용자 카운트
            if user.last_active:
                if user.last_active >= today_start:
                    active_today += 1
                if user.last_active >= week_start:
                    active_week += 1
        
        return cls(
            total_users=len(users),
            active_users_today=active_today,
            active_users_week=active_week,
            total_commands=total_commands,
            most_active_user=most_active_user,
            most_active_commands=most_active_commands,
            newest_user=newest_user,
            suspended_users=suspended_users,
            moderator_count=moderator_count,
            admin_count=admin_count
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'total_users': self.total_users,
            'active_users_today': self.active_users_today,
            'active_users_week': self.active_users_week,
            'total_commands': self.total_commands,
            'most_active_user': self.most_active_user,
            'most_active_commands': self.most_active_commands,
            'newest_user': self.newest_user,
            'suspended_users': self.suspended_users,
            'moderator_count': self.moderator_count,
            'admin_count': self.admin_count
        }
    
    def get_summary_text(self) -> str:
        """
        요약 텍스트 반환
        
        Returns:
            str: 통계 요약 텍스트
        """
        lines = [
            f"📊 사용자 통계",
            f"총 사용자: {self.total_users}명",
            f"오늘 활성: {self.active_users_today}명",
            f"주간 활성: {self.active_users_week}명",
            f"총 명령어: {self.total_commands:,}회"
        ]
        
        if self.suspended_users > 0:
            lines.append(f"정지된 사용자: {self.suspended_users}명")
        
        if self.moderator_count > 0:
            lines.append(f"모더레이터: {self.moderator_count}명")
        
        if self.admin_count > 0:
            lines.append(f"관리자: {self.admin_count}명")
        
        if self.most_active_user:
            lines.append(f"최고 활성: {self.most_active_user} ({self.most_active_commands:,}회)")
        
        if self.newest_user:
            lines.append(f"최신 사용자: {self.newest_user}")
        
        return "\n".join(lines)


class UserManager:
    """사용자 관리 클래스"""
    
    def __init__(self, cache_ttl: int = 300):
        """
        UserManager 초기화
        
        Args:
            cache_ttl: 캐시 TTL (초)
        """
        self._users_cache: Dict[str, User] = {}
        self._cache_timestamp = None
        self._cache_ttl = cache_ttl
        self._stats_cache: Optional[UserStats] = None
        self._stats_cache_timestamp = None
    
    def create_user_from_sheet_data(self, data: Dict[str, Any]) -> User:
        """
        시트 데이터에서 사용자 생성
        
        Args:
            data: 시트 행 데이터
            
        Returns:
            User: 생성된 사용자 객체
            
        Raises:
            UserValidationError: 데이터 검증 실패 시
        """
        return User.from_sheet_data(data)
    
    def validate_user_data(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """
        사용자 데이터 유효성 검사
        
        Args:
            user_id: 사용자 ID
            user_data: 사용자 데이터
            
        Returns:
            bool: 유효성 여부
        """
        try:
            user = User.from_sheet_data(user_data)
            return user.is_valid() and user.id == user_id
        except (UserValidationError, Exception):
            return False
    
    def get_user_display_info(self, user: User) -> Dict[str, str]:
        """
        사용자 표시 정보 반환
        
        Args:
            user: User 객체
            
        Returns:
            Dict: 표시용 정보
        """
        return {
            'id': user.id,
            'name': user.get_display_name(),
            'command_count': f"{user.command_count:,}",
            'last_active': user.last_active.strftime('%Y-%m-%d %H:%M') if user.last_active else '없음',
            'status': user.status.value,
            'role': user.role.value
        }
    
    def create_user_stats(self, users: List[User]) -> UserStats:
        """
        사용자 통계 생성 (캐시 지원)
        
        Args:
            users: 사용자 리스트
            
        Returns:
            UserStats: 통계 객체
        """
        current_time = time.time()
        
        # 캐시된 통계가 유효한지 확인
        if (self._stats_cache and self._stats_cache_timestamp and 
            current_time - self._stats_cache_timestamp < self._cache_ttl):
            return self._stats_cache
        
        # 새로운 통계 생성
        stats = UserStats.from_users(users)
        
        # 캐시 업데이트
        self._stats_cache = stats
        self._stats_cache_timestamp = current_time
        
        return stats
    
    def get_user_by_id(self, user_id: str, users: List[User]) -> Optional[User]:
        """
        ID로 사용자 찾기
        
        Args:
            user_id: 사용자 ID
            users: 사용자 리스트
            
        Returns:
            Optional[User]: 찾은 사용자 또는 None
        """
        # ID 정규화
        if user_id.startswith('@'):
            user_id = user_id[1:]
        
        for user in users:
            if user.id == user_id:
                return user
        return None
    
    def filter_users_by_status(self, users: List[User], status: UserStatus) -> List[User]:
        """
        상태별 사용자 필터링
        
        Args:
            users: 사용자 리스트
            status: 필터링할 상태
            
        Returns:
            List[User]: 필터링된 사용자 리스트
        """
        return [user for user in users if user.status == status]
    
    def filter_users_by_role(self, users: List[User], role: UserRole) -> List[User]:
        """
        역할별 사용자 필터링
        
        Args:
            users: 사용자 리스트
            role: 필터링할 역할
            
        Returns:
            List[User]: 필터링된 사용자 리스트
        """
        return [user for user in users if user.role == role]
    
    def get_active_users(self, users: List[User]) -> List[User]:
        """
        활성 사용자만 반환
        
        Args:
            users: 사용자 리스트
            
        Returns:
            List[User]: 활성 사용자 리스트
        """
        return [user for user in users if user.is_active()]
    
    def clear_cache(self) -> None:
        """캐시 초기화"""
        self._users_cache.clear()
        self._cache_timestamp = None
        self._stats_cache = None
        self._stats_cache_timestamp = None


# 편의 함수들
def create_user_from_sheet(data: Dict[str, Any]) -> User:
    """시트 데이터에서 사용자 생성 (편의 함수)"""
    return User.from_sheet_data(data)


def validate_user_id(user_id: str) -> bool:
    """
    사용자 ID 형식 검증
    
    Args:
        user_id: 검증할 사용자 ID
        
    Returns:
        bool: 유효성 여부
    """
    if not user_id or not isinstance(user_id, str):
        return False
    
    user_id = user_id.strip()
    
    # @ 제거 후 검증
    if user_id.startswith('@'):
        user_id = user_id[1:]
    
    # 기본 검증: 비어있지 않고, 특수문자 제한
    if not user_id or len(user_id) < 1:
        return False
    
    # 마스토돈 사용자명 형식 검증
    # 허용된 문자: 영문자, 숫자, 언더스코어, 하이픈
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, user_id))


def create_empty_user(user_id: str) -> User:
    """
    빈 사용자 객체 생성 (등록되지 않은 사용자용)
    
    Args:
        user_id: 사용자 ID
        
    Returns:
        User: 빈 사용자 객체
    """
    return User(id=user_id, name="", command_count=0)


def create_admin_user(user_id: str, name: str) -> User:
    """
    관리자 사용자 객체 생성
    
    Args:
        user_id: 사용자 ID
        name: 사용자 이름
        
    Returns:
        User: 관리자 사용자 객체
    """
    return User(
        id=user_id,
        name=name,
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE
    )


def create_moderator_user(user_id: str, name: str) -> User:
    """
    모더레이터 사용자 객체 생성
    
    Args:
        user_id: 사용자 ID
        name: 사용자 이름
        
    Returns:
        User: 모더레이터 사용자 객체
    """
    return User(
        id=user_id,
        name=name,
        role=UserRole.MODERATOR,
        status=UserStatus.ACTIVE
    )


# 전역 사용자 관리자 인스턴스
user_manager = UserManager()

# 호환성을 위한 별칭
UserNotFoundError = UserNotFoundError
UserValidationError = UserValidationError