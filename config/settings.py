"""
설정 관리 모듈
환경 변수를 로드하고 애플리케이션 전반의 설정을 관리합니다.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List, Set, Dict
from functools import lru_cache

# 경로 설정 (VM 환경 대응)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def _parse_env_line(line: str) -> tuple[str, str]:
    """환경 변수 라인을 파싱하는 헬퍼 함수"""
    if not line or line.startswith('#') or '=' not in line:
        return None, None
    
    key, value = line.split('=', 1)
    key = key.strip()
    value = value.strip()
    
    # 따옴표 제거
    if (value.startswith('"') and value.endswith('"')) or \
       (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    
    return key, value


def _load_env_file(env_path: Path, encoding: str) -> bool:
    """지정된 인코딩으로 .env 파일을 로드하는 함수"""
    try:
        with open(env_path, 'r', encoding=encoding) as f:
            for line in f:
                key, value = _parse_env_line(line.strip())
                if key and value:
                    os.environ.setdefault(key, value)
        return True
    except UnicodeDecodeError:
        return False


def _load_env():
    """환경 변수를 먼저 로드하는 함수"""
    base_dir = Path(__file__).parent.parent
    env_path = base_dir / '.env'
    
    if not env_path.exists():
        return
    
    # UTF-8로 먼저 시도
    if _load_env_file(env_path, 'utf-8'):
        return
    
    # UTF-8 실패시 여러 인코딩으로 시도
    encodings = ['cp949', 'euc-kr', 'latin-1', 'iso-8859-1']
    for encoding in encodings:
        if _load_env_file(env_path, encoding):
            break


# 환경변수 먼저 로드
_load_env()


class Config:
    """애플리케이션 설정 클래스"""
    
    # 기본 경로 설정
    BASE_DIR = Path(__file__).parent.parent

    # 응답 메시지 프리픽스 (이것만 수정하면 모든 응답에 반영!)
    RESPONSE_PREFIX: str = os.getenv('RESPONSE_PREFIX', '✶ ')
    RESPONSE_PREFIX_STRIPPED = RESPONSE_PREFIX.strip()  # 미리 계산
    
    # Mastodon API 설정 (이제 환경변수가 로드된 후라서 정상 작동)
    MASTODON_CLIENT_ID: str = os.getenv('MASTODON_CLIENT_ID', '')
    MASTODON_CLIENT_SECRET: str = os.getenv('MASTODON_CLIENT_SECRET', '')
    MASTODON_ACCESS_TOKEN: str = os.getenv('MASTODON_ACCESS_TOKEN', '')
    MASTODON_API_BASE_URL: str = os.getenv('MASTODON_API_BASE_URL', '')
    
    # Google Sheets 설정
    GOOGLE_CREDENTIALS_PATH: str = os.getenv(
        'GOOGLE_CREDENTIALS_PATH', 
        str(BASE_DIR / 'credentials.json')
    )
    SHEET_NAME: str = os.getenv('SHEET_NAME', '기본 자동봇 시트')
    
    # 봇 동작 설정
    MAX_RETRIES: int = int(os.getenv('BOT_MAX_RETRIES', '5'))
    BASE_WAIT_TIME: int = int(os.getenv('BOT_BASE_WAIT_TIME', '2'))
    MAX_DICE_COUNT: int = int(os.getenv('BOT_MAX_DICE_COUNT', '20'))
    MAX_DICE_SIDES: int = int(os.getenv('BOT_MAX_DICE_SIDES', '1000'))
    MAX_CARD_COUNT: int = int(os.getenv('BOT_MAX_CARD_COUNT', '52'))
    
    # 시스템 관리자 설정
    SYSTEM_ADMIN_ID: str = os.getenv('SYSTEM_ADMIN_ID', 'admin')
    
    # 봇 계정 이름들 (자동 인식용)
    BOT_ACCOUNT_NAMES: List[str] = [
        'store', 'bot', 'admin',
        os.getenv('BOT_ACCOUNT_NAME', 'defaultbot').lower()
    ]
    
    # 로그 설정
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE_PATH: str = os.getenv('LOG_FILE_PATH', 'bot.log')
    LOG_MAX_BYTES: int = int(os.getenv('LOG_MAX_BYTES', '10485760'))  # 10MB
    LOG_BACKUP_COUNT: int = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    
    # 캐시 설정 (운세 전용)
    FORTUNE_CACHE_TTL: int = int(os.getenv('FORTUNE_CACHE_TTL', '3600'))  # 1시간
    
    # 메시지 청킹 설정
    MESSAGE_MAX_LENGTH: int = int(os.getenv('MESSAGE_MAX_LENGTH', '500'))
    
    # API 설정
    API_TIMEOUT: int = int(os.getenv('API_TIMEOUT', '30'))
    CONNECTION_RETRY_INTERVAL: int = int(os.getenv('CONNECTION_RETRY_INTERVAL', '5'))
    MAX_CONNECTION_RETRIES: int = int(os.getenv('MAX_CONNECTION_RETRIES', '3'))
    
    # 개발/디버그 설정
    DEBUG_MODE: bool = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
    ENABLE_CONSOLE_LOG: bool = os.getenv('ENABLE_CONSOLE_LOG', 'True').lower() == 'true'
    
    # 워크시트 이름 상수
    WORKSHEET_NAMES = {
        'ROSTER': '명단',
        'CUSTOM': '커스텀',
        'HELP': '도움말',
        'FORTUNE': '운세',
        'LOG': '로그',
    }
    
    # 시스템 키워드 (공백 있는/없는 버전 모두 지원)
    _BASE_KEYWORDS = ['다이스', '카드뽑기', '운세', '도움말']
    _SPACE_KEYWORDS = ['카드 뽑기']  # 공백 포함 버전
    
    SYSTEM_KEYWORDS: Set[str] = set(_BASE_KEYWORDS + _SPACE_KEYWORDS)
    
    # 명령어 정규화 매핑 (공백 제거 등)
    COMMAND_NORMALIZATION = {
        '카드 뽑기': '카드뽑기',
        '카드  뽑기': '카드뽑기',  # 여러 공백
        '주사위': '다이스',
        '운세보기': '운세',
        '도움': '도움말'
    }
    
    # 성공 메시지 상수
    SUCCESS_MESSAGES = {
        'SHEET_CONNECTED': '스프레드시트 연결 성공',
        'AUTH_SUCCESS': 'auth success',
        'STREAMING_START': 'Mastodon 스트리밍 시작',
        'ERROR_NOTIFICATION_SENT': '오류 알림 전송 완료'
    }
    
    @classmethod
    @lru_cache(maxsize=1)
    def _get_error_messages(cls) -> Dict[str, str]:
        """에러 메시지 딕셔너리를 반환합니다 (캐싱 적용)"""
        return {
            'USER_NOT_FOUND': '등록되지 않은 사용자입니다. 먼저 캐릭터를 등록해주세요.',
            'USER_ID_CHECK_FAILED': '명령어 시전자의 아이디를 확인할 수 없습니다. 잠시만 기다려 주세요.',
            'USER_NAME_INVALID': '사용자 이름 정보가 올바르지 않습니다.',
            'TEMPORARY_ERROR': '일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.',
            'UNKNOWN_COMMAND': '알 수 없는 명령어입니다. [도움말]을 입력해 사용 가능한 명령어를 확인하세요.',
            'DICE_FORMAT_ERROR': '주사위 형식이 올바르지 않습니다. 예: [2d6], [1d6<4] (4 이하 성공), [3d10>7] (7 이상 성공)',
            'DICE_COUNT_LIMIT': f'주사위 개수는 최대 {cls.MAX_DICE_COUNT}개까지 가능합니다.',
            'DICE_SIDES_LIMIT': f'주사위 면수는 최대 {cls.MAX_DICE_SIDES}면까지 가능합니다.',
            'CARD_COUNT_ERROR': f'카드는 1장부터 {cls.MAX_CARD_COUNT}장까지 뽑을 수 있습니다.',
            'CARD_FORMAT_ERROR': '뽑을 카드 장수를 지정해 주세요.\n예시: [카드뽑기/5장] 또는 [카드 뽑기/5장]',
            'CARD_NUMBER_ERROR': '카드 장수는 숫자로 입력해 주세요.\n예시: [카드뽑기/5장] 또는 [카드 뽑기/5장]',
            'SHEET_NOT_FOUND': '필요한 시트를 찾을 수 없습니다.',
            'DATA_NOT_FOUND': '데이터를 찾을 수 없습니다.'
        }
    
    @classmethod
    def get_credentials_path(cls) -> Path:
        """
        Google 인증 파일의 경로를 반환합니다.
        
        Returns:
            Path: 인증 파일 경로
        """
        cred_path = Path(cls.GOOGLE_CREDENTIALS_PATH)
        if not cred_path.is_absolute():
            cred_path = cls.BASE_DIR / cred_path
        return cred_path
    
    @classmethod
    def normalize_command(cls, command: str) -> str:
        """
        명령어를 정규화합니다 (공백 제거, 동의어 변환 등)
        
        Args:
            command: 원본 명령어
            
        Returns:
            str: 정규화된 명령어
        """
        if not command:
            return command
            
        # 앞뒤 공백 제거
        normalized = command.strip()
        
        # 정규화 매핑 적용
        if normalized in cls.COMMAND_NORMALIZATION:
            normalized = cls.COMMAND_NORMALIZATION[normalized]
        
        # 추가 정규화: 연속된 공백을 단일 공백으로
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    @classmethod
    def is_system_keyword(cls, keyword: str) -> bool:
        """
        시스템 키워드인지 확인합니다 (정규화 후 확인)
        
        Args:
            keyword: 확인할 키워드
            
        Returns:
            bool: 시스템 키워드면 True
        """
        if not keyword:
            return False
        
        normalized = cls.normalize_command(keyword)
        return normalized in cls.SYSTEM_KEYWORDS or keyword in cls.SYSTEM_KEYWORDS
    
    @classmethod
    def is_bot_account(cls, account_name: str) -> bool:
        """
        봇 계정인지 확인합니다
        
        Args:
            account_name: 확인할 계정명
            
        Returns:
            bool: 봇 계정이면 True
        """
        if not account_name:
            return False
            
        # @ 제거하고 소문자 변환
        clean_name = account_name.lstrip('@').lower()
        
        return any(bot_name in clean_name for bot_name in cls.BOT_ACCOUNT_NAMES)
    
    @classmethod
    def get_worksheet_name(cls, key: str) -> Optional[str]:
        """
        워크시트 키에 해당하는 실제 시트 이름을 반환합니다.
        
        Args:
            key: 워크시트 키 (예: 'ROSTER', 'LOG')
            
        Returns:
            Optional[str]: 시트 이름 또는 None
        """
        return cls.WORKSHEET_NAMES.get(key.upper())
    
    @classmethod
    def get_error_message(cls, key: str) -> str:
        """
        에러 메시지 키에 해당하는 메시지를 반환합니다.
        
        Args:
            key: 에러 메시지 키
            
        Returns:
            str: 에러 메시지
        """
        error_messages = cls._get_error_messages()
        return error_messages.get(key, error_messages['TEMPORARY_ERROR'])
    
    @classmethod
    def get_success_message(cls, key: str) -> str:
        """
        성공 메시지 키에 해당하는 메시지를 반환합니다.
        
        Args:
            key: 성공 메시지 키
            
        Returns:
            str: 성공 메시지
        """
        return cls.SUCCESS_MESSAGES.get(key, '')
    
    @classmethod
    def format_response(cls, message: str) -> str:
        """
        모든 응답 메시지에 프리픽스 추가
        
        Args:
            message: 원본 메시지
            
        Returns:
            str: 프리픽스가 추가된 메시지
        """
        if not message or not isinstance(message, str):
            return message
        
        # 공백 제거
        message = message.strip()
        if not message:
            return message
        
        # 이미 프리픽스가 있으면 중복 방지
        if message.startswith(cls.RESPONSE_PREFIX_STRIPPED):
            return message
            
        return f"{cls.RESPONSE_PREFIX}{message}"


# 설정 인스턴스 (싱글톤 패턴)
config = Config()