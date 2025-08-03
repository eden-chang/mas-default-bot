"""
텍스트 처리 유틸리티
공통으로 사용되는 텍스트 처리 함수들을 정의합니다.
"""

import os
import sys
import re
import functools
from typing import List, Optional, Dict, Union, Callable, Any
from bs4 import BeautifulSoup

# 상수 정의
DEFAULT_MAX_LENGTH = 490
DEFAULT_DELIMITER = '\n'
DEFAULT_SUFFIX = "..."
DEFAULT_MASK_CHAR = '*'
DEFAULT_WORDS_PER_MINUTE = 200

# 정규식 패턴 상수 (컴파일된 버전)
COMMAND_PATTERN = r'\[([^\[\]]+)\]'
MENTION_PATTERN = r'@(\w+(?:\.\w+)*)'
MENTION_REMOVE_PATTERN = r'@\w+(?:\.\w+)*'
DICE_PATTERN = r'\b(\d+d\d+(?:[+\-]\d+)?(?:[<>]\d+)?)\b'
NUMBER_PATTERN = r'\b\d+\b'
INVALID_FILENAME_CHARS = r'[<>:"/\\|?*]'

# 컴파일된 정규식 패턴 (성능 최적화)
COMMAND_REGEX = re.compile(COMMAND_PATTERN)
MENTION_REGEX = re.compile(MENTION_PATTERN)
MENTION_REMOVE_REGEX = re.compile(MENTION_REMOVE_PATTERN)
DICE_REGEX = re.compile(DICE_PATTERN, re.IGNORECASE)
NUMBER_REGEX = re.compile(NUMBER_PATTERN)
INVALID_FILENAME_REGEX = re.compile(INVALID_FILENAME_CHARS)
WHITESPACE_REGEX = re.compile(r'\s+')

# 경로 설정 (VM 환경 대응)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

try:
    from config.settings import config
    from utils.logging_config import logger
except ImportError:
    # VM 환경에서 임포트 실패 시 폴백
    import logging
    logger = logging.getLogger('text_processing')
    
    class Config:
        @staticmethod
        def normalize_command(command: str) -> str:
            return command.strip()
    
    config = Config()


def safe_string_operation(func: Callable) -> Callable:
    """
    문자열 연산을 안전하게 수행하는 데코레이터
    
    Args:
        func: 데코레이트할 함수
        
    Returns:
        함수의 래퍼
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except (TypeError, ValueError, AttributeError) as e:
            logger.warning(f"문자열 연산 오류 in {func.__name__}: {e}")
            # 기본값 반환
            if func.__name__ in ['extract_text_from_html', 'normalize_spacing', 'clean_command_text']:
                return ""
            elif func.__name__ in ['extract_commands_from_text', 'parse_command_keywords', 'extract_mentions_from_text']:
                return []
            elif func.__name__ in ['has_command_format', 'validate_command_syntax', 'is_empty_or_whitespace']:
                return False
            elif func.__name__ in ['count_korean_characters', 'estimate_reading_time']:
                return 0
            else:
                return ""
    return wrapper


@safe_string_operation
def extract_text_from_html(html_content: str) -> str:
    """
    HTML 태그 제거하여 텍스트 추출
    
    Args:
        html_content: HTML 콘텐츠
        
    Returns:
        str: 순수 텍스트
    """
    if not html_content:
        return ""
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text(separator=' ', strip=True)
    except Exception as e:
        logger.warning(f"HTML 파싱 오류: {e}")
        return html_content


@safe_string_operation
def has_command_format(text: str) -> bool:
    """
    텍스트에 명령어 형식이 있는지 확인
    
    Args:
        text: 확인할 텍스트
        
    Returns:
        bool: 명령어 형식 포함 여부
    """
    if not text:
        return False
    
    # [] 패턴 확인
    if '[' not in text or ']' not in text:
        return False
    
    # [] 위치 확인
    start_pos = text.find('[')
    end_pos = text.find(']')
    
    return start_pos < end_pos


@safe_string_operation
def extract_commands_from_text(text: str) -> List[str]:
    """
    텍스트에서 모든 명령어 추출
    
    Args:
        text: 분석할 텍스트
        
    Returns:
        List[str]: 추출된 명령어 리스트
    """
    if not text:
        return []
    
    commands = []
    
    # 정규식으로 [내용] 패턴 추출
    matches = COMMAND_REGEX.findall(text)
    
    for match in matches:
        # 명령어 정규화
        normalized = config.normalize_command(match) if hasattr(config, 'normalize_command') else match.strip()
        if normalized:
            commands.append(normalized)
    
    return commands


@safe_string_operation
def parse_command_keywords(command_text: str) -> List[str]:
    """
    명령어 텍스트에서 키워드 리스트 추출
    
    Args:
        command_text: 명령어 텍스트 ([] 제외)
        
    Returns:
        List[str]: 키워드 리스트
    """
    if not command_text:
        return []
    
    # '/' 또는 공백으로 분할
    if '/' in command_text:
        keywords = command_text.split('/')
    else:
        keywords = command_text.split()
    
    # 빈 문자열 제거 및 정규화
    result = []
    for keyword in keywords:
        normalized = config.normalize_command(keyword) if hasattr(config, 'normalize_command') else keyword.strip()
        if normalized:
            result.append(normalized)
    
    return result


@safe_string_operation
def normalize_spacing(text: str) -> str:
    """
    텍스트의 공백을 정규화 (연속된 공백을 단일 공백으로)
    
    Args:
        text: 정규화할 텍스트
        
    Returns:
        str: 정규화된 텍스트
    """
    if not text:
        return text
    
    # 연속된 공백을 단일 공백으로 변환
    normalized = WHITESPACE_REGEX.sub(' ', text.strip())
    return normalized


@safe_string_operation
def remove_mentions_from_text(text: str) -> str:
    """
    텍스트에서 멘션(@사용자명) 제거
    
    Args:
        text: 원본 텍스트
        
    Returns:
        str: 멘션이 제거된 텍스트
    """
    if not text:
        return text
    
    # @사용자명 패턴 제거
    cleaned = MENTION_REMOVE_REGEX.sub('', text)
    
    # 공백 정규화
    return normalize_spacing(cleaned)


@safe_string_operation
def extract_mentions_from_text(text: str) -> List[str]:
    """
    텍스트에서 멘션된 사용자명 추출
    
    Args:
        text: 분석할 텍스트
        
    Returns:
        List[str]: 멘션된 사용자명 리스트 (@ 제외)
    """
    if not text:
        return []
    
    # @사용자명 패턴 추출
    matches = MENTION_REGEX.findall(text)
    
    return list(set(matches))  # 중복 제거


@safe_string_operation
def clean_command_text(text: str) -> str:
    """
    명령어 텍스트 정리 (멘션 제거, 공백 정규화 등)
    
    Args:
        text: 원본 텍스트
        
    Returns:
        str: 정리된 텍스트
    """
    if not text:
        return text
    
    # HTML 태그 제거
    cleaned = extract_text_from_html(text)
    
    # 멘션 제거
    cleaned = remove_mentions_from_text(cleaned)
    
    # 공백 정규화
    cleaned = normalize_spacing(cleaned)
    
    return cleaned


@safe_string_operation
def clean_text(text: str) -> str:
    """
    일반 텍스트 정리 (백워드 호환성)
    
    Args:
        text: 정리할 텍스트
        
    Returns:
        str: 정리된 텍스트
    """
    return clean_command_text(text)


def split_text_by_length(text: str, max_length: int = DEFAULT_MAX_LENGTH, 
                        delimiter: str = DEFAULT_DELIMITER) -> List[str]:
    """
    텍스트를 최대 길이로 분할
    
    Args:
        text: 분할할 텍스트
        max_length: 최대 길이
        delimiter: 우선 분할 기준 (줄바꿈 등)
        
    Returns:
        List[str]: 분할된 텍스트 조각들
    """
    if not text or len(text) <= max_length:
        return [text] if text else []
    
    chunks = []
    
    # 구분자 기준으로 먼저 분할 시도
    if delimiter in text:
        parts = text.split(delimiter)
        current_chunk = ""
        
        for part in parts:
            # 현재 청크에 추가했을 때 길이 확인
            test_chunk = current_chunk + (delimiter if current_chunk else "") + part
            
            if len(test_chunk) <= max_length:
                current_chunk = test_chunk
            else:
                # 현재 청크를 저장하고 새로운 청크 시작
                if current_chunk:
                    chunks.append(current_chunk)
                
                # 파트 자체가 너무 긴 경우 강제 분할
                if len(part) > max_length:
                    chunks.extend(force_split_text(part, max_length))
                    current_chunk = ""
                else:
                    current_chunk = part
        
        # 마지막 청크 추가
        if current_chunk:
            chunks.append(current_chunk)
    else:
        # 구분자가 없으면 강제 분할
        chunks = force_split_text(text, max_length)
    
    return chunks


def force_split_text(text: str, max_length: int) -> List[str]:
    """
    텍스트를 강제로 지정된 길이로 분할
    
    Args:
        text: 분할할 텍스트
        max_length: 최대 길이
        
    Returns:
        List[str]: 분할된 텍스트 조각들
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_length
        chunk = text[start:end]
        chunks.append(chunk)
        start = end
    
    return chunks


# 조사 관련 캐시
_particle_cache: Dict[str, Dict[str, str]] = {}


def detect_korean_particle(word: str, particle_type: str = 'object') -> str:
    """
    한글 단어의 받침 여부에 따른 조사 결정
    
    Args:
        word: 분석할 한글 단어
        particle_type: 조사 타입
            - 'object' 또는 'eul_reul': 을/를 (목적격 조사)
            - 'subject' 또는 'i_ga': 이/가 (주격 조사)
            - 'topic' 또는 'eun_neun': 은/는 (보조사, 주제 표시)
            - 'with' 또는 'wa_gwa': 와/과 (부사격 조사, ~와 함께)
        
    Returns:
        str: 적절한 조사
    """
    if not word:
        return ""
    
    # 캐시 키 생성
    cache_key = f"{word}_{particle_type}"
    
    # 캐시에서 확인
    if cache_key in _particle_cache:
        return _particle_cache[cache_key]
    
    # 마지막 글자 추출
    last_char = word[-1]
    
    # 받침 여부 확인
    has_final = _has_korean_final_consonant(last_char)
    
    # 조사 타입별 반환
    particle_map = {
        'object': '을' if has_final else '를',
        'eul_reul': '을' if has_final else '를',
        '을를': '을' if has_final else '를',
        '_을를': '을' if has_final else '를',
        'subject': '이' if has_final else '가',
        'i_ga': '이' if has_final else '가',
        '이가': '이' if has_final else '가',
        '_이가': '이' if has_final else '가',
        'topic': '은' if has_final else '는',
        'eun_neun': '은' if has_final else '는',
        '은는': '은' if has_final else '는',
        '_은는': '은' if has_final else '는',
        'with': '과' if has_final else '와',
        'wa_gwa': '과' if has_final else '와',
        '와과': '과' if has_final else '와',
        '_와과': '과' if has_final else '와',
    }
    
    result = particle_map.get(particle_type, '')
    
    # 캐시에 저장
    _particle_cache[cache_key] = result
    
    return result


def _has_korean_final_consonant(char: str) -> bool:
    """
    한글 문자의 받침(종성) 여부 확인
    
    Args:
        char: 확인할 한글 문자 (단일 문자)
        
    Returns:
        bool: 받침이 있으면 True, 없으면 False
    """
    if not char:
        return False
    
    # 한글 범위 확인 (완성된 한글: 가-힣)
    if '가' <= char <= '힣':
        # 유니코드 계산으로 받침 확인
        code = ord(char) - ord('가')
        final_consonant = code % 28
        return final_consonant != 0
    
    # 한글 자모 범위 확인 (ㄱ-ㅣ)
    elif 'ㄱ' <= char <= 'ㅣ':
        # 자음은 받침 있음으로 취급, 모음은 받침 없음으로 취급
        if 'ㄱ' <= char <= 'ㅎ':  # 자음
            return True
        elif 'ㅏ' <= char <= 'ㅣ':  # 모음
            return False
        else:
            return False
    
    # 영어, 숫자 등 한글이 아닌 경우
    else:
        # 영어 자음으로 끝나는 경우 받침 있음으로 취급
        if char.isalpha():
            consonants = 'bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ'
            return char in consonants
        # 숫자나 기타 문자는 받침 있음으로 취급 (기본값)
        else:
            return True


def get_all_particles(word: str) -> Dict[str, str]:
    """
    한 단어에 대한 모든 조사 변형을 반환
    
    Args:
        word: 분석할 단어
        
    Returns:
        Dict[str, str]: 모든 조사 변형이 포함된 딕셔너리
    """
    if not word:
        return {}
    
    # 캐시에서 확인
    if word in _particle_cache:
        return _particle_cache[word]
    
    result = {
        'object': detect_korean_particle(word, 'object'),       # 을/를
        'subject': detect_korean_particle(word, 'subject'),     # 이/가
        'topic': detect_korean_particle(word, 'topic'),         # 은/는
        'with': detect_korean_particle(word, 'with'),           # 와/과
        # 추가 조사들
        'from': detect_korean_particle(word, 'object') + '서',   # 을서/를서 (에서의 줄임)
        'to': detect_korean_particle(word, 'object') + '로',     # 을로/를로 (으로/로)
    }
    
    # 캐시에 저장
    _particle_cache[word] = result
    
    return result


def format_with_particle(word: str, particle_type: str) -> str:
    """
    단어와 조사를 합쳐서 반환
    
    Args:
        word: 대상 단어
        particle_type: 조사 타입
        
    Returns:
        str: "단어+조사" 형태의 문자열
    """
    if not word:
        return ""
    
    particle = detect_korean_particle(word, particle_type)
    return f"{word}{particle}"


def replace_particles_in_text(text: str, word_particle_map: Dict[str, str]) -> str:
    """
    텍스트에서 지정된 단어들의 조사를 자동으로 교체
    
    Args:
        text: 원본 텍스트
        word_particle_map: {단어: 조사타입} 형태의 매핑
        
    Returns:
        str: 조사가 교체된 텍스트
    """
    if not text or not word_particle_map:
        return text
    
    result = text
    
    for word, particle_type in word_particle_map.items():
        if word in result:
            # 조사가 올바른지 확인하고 교체
            correct_form = format_with_particle(word, particle_type)
            
            # 기존의 잘못된 조사 패턴들을 찾아서 교체
            wrong_patterns = [
                f"{word}을", f"{word}를",  # 목적격
                f"{word}이", f"{word}가",  # 주격
                f"{word}은", f"{word}는",  # 주제
                f"{word}와", f"{word}과",  # 부사격
            ]
            
            for pattern in wrong_patterns:
                if pattern in result:
                    result = result.replace(pattern, correct_form)
    
    return result


def format_list_text(items: List[str], separator: str = ', ', 
                    last_separator: Optional[str] = None, max_items: Optional[int] = None) -> str:
    """
    리스트를 읽기 좋은 텍스트로 포맷
    
    Args:
        items: 아이템 리스트
        separator: 일반 구분자
        last_separator: 마지막 구분자 (예: ' 그리고 ')
        max_items: 최대 표시 아이템 수
        
    Returns:
        str: 포맷된 텍스트
    """
    if not items:
        return ""
    
    # 최대 아이템 수 제한
    if max_items and len(items) > max_items:
        display_items = items[:max_items]
        remaining_count = len(items) - max_items
        return format_list_text(display_items, separator, last_separator) + f" 외 {remaining_count}개"
    
    if len(items) == 1:
        return items[0]
    
    if len(items) == 2:
        if last_separator:
            return f"{items[0]}{last_separator}{items[1]}"
        else:
            return separator.join(items)
    
    # 3개 이상
    if last_separator:
        return separator.join(items[:-1]) + last_separator + items[-1]
    else:
        return separator.join(items)


def truncate_text(text: str, max_length: int, suffix: str = DEFAULT_SUFFIX) -> str:
    """
    텍스트를 지정된 길이로 자르고 접미사 추가
    
    Args:
        text: 원본 텍스트
        max_length: 최대 길이
        suffix: 접미사
        
    Returns:
        str: 잘린 텍스트
    """
    if not text or len(text) <= max_length:
        return text
    
    # 접미사 길이를 고려하여 자르기
    truncate_length = max_length - len(suffix)
    if truncate_length <= 0:
        return suffix[:max_length]
    
    return text[:truncate_length] + suffix


@safe_string_operation
def validate_command_syntax(command: str) -> bool:
    """
    명령어 문법 유효성 검사
    
    Args:
        command: 검사할 명령어
        
    Returns:
        bool: 유효성 여부
    """
    if not command:
        return False
    
    # 기본 문법 확인: [내용] 형태
    if not (command.startswith('[') and command.endswith(']')):
        return False
    
    # 내용 추출
    content = command[1:-1].strip()
    if not content:
        return False
    
    # 중첩된 대괄호 확인
    if '[' in content or ']' in content:
        return False
    
    return True


@safe_string_operation
def extract_dice_notation(text: str) -> List[str]:
    """
    텍스트에서 다이스 표기법 추출 (예: 2d6, 1d20+5)
    
    Args:
        text: 분석할 텍스트
        
    Returns:
        List[str]: 다이스 표기법 리스트
    """
    if not text:
        return []
    
    # 다이스 표기법 패턴: 숫자d숫자[+/-숫자][</>숫자]
    matches = DICE_REGEX.findall(text)
    
    return matches


@safe_string_operation
def extract_numbers_from_text(text: str) -> List[int]:
    """
    텍스트에서 숫자 추출
    
    Args:
        text: 분석할 텍스트
        
    Returns:
        List[int]: 추출된 숫자 리스트
    """
    if not text:
        return []
    
    # 숫자 패턴 추출
    matches = NUMBER_REGEX.findall(text)
    
    try:
        return [int(match) for match in matches]
    except ValueError:
        return []


@safe_string_operation
def clean_filename(filename: str) -> str:
    """
    파일명에서 특수문자 제거
    
    Args:
        filename: 원본 파일명
        
    Returns:
        str: 정리된 파일명
    """
    if not filename:
        return ""
    
    # 파일명에서 사용할 수 없는 문자 제거
    cleaned = INVALID_FILENAME_REGEX.sub('_', filename)
    
    # 연속된 언더스코어를 단일로 변환
    cleaned = WHITESPACE_REGEX.sub('_', cleaned)
    
    # 앞뒤 언더스코어 제거
    cleaned = cleaned.strip('_')
    
    return cleaned


def mask_sensitive_data(text: str, mask_char: str = DEFAULT_MASK_CHAR) -> str:
    """
    민감한 데이터 마스킹 (토큰, 비밀번호 등)
    
    Args:
        text: 원본 텍스트
        mask_char: 마스킹 문자
        
    Returns:
        str: 마스킹된 텍스트
    """
    if not text or len(text) <= 4:
        return mask_char * len(text) if text else ""
    
    # 앞 2자리와 뒤 2자리만 표시, 나머지는 마스킹
    return text[:2] + mask_char * (len(text) - 4) + text[-2:]


# 편의 함수들
@safe_string_operation
def is_empty_or_whitespace(text: str) -> bool:
    """텍스트가 비어있거나 공백만 있는지 확인"""
    return not text or text.isspace()


@safe_string_operation
def count_korean_characters(text: str) -> int:
    """한글 문자 개수 계산"""
    if not text:
        return 0
    
    count = 0
    for char in text:
        if '가' <= char <= '힣' or 'ㄱ' <= char <= 'ㅣ':
            count += 1
    
    return count


def estimate_reading_time(text: str, words_per_minute: int = DEFAULT_WORDS_PER_MINUTE) -> int:
    """
    텍스트 읽기 시간 추정 (분 단위)
    
    Args:
        text: 분석할 텍스트
        words_per_minute: 분당 읽기 단어 수
        
    Returns:
        int: 예상 읽기 시간 (분)
    """
    if not text:
        return 0
    
    # 단어 수 계산 (공백 기준)
    words = len(text.split())
    
    # 한글의 경우 조정
    korean_chars = count_korean_characters(text)
    if korean_chars > 0:
        # 한글은 단어 개념이 다르므로 문자 기준으로 조정
        estimated_words = words + (korean_chars // 2)
    else:
        estimated_words = words
    
    # 읽기 시간 계산 (최소 1분)
    reading_time = max(1, estimated_words // words_per_minute)
    
    return reading_time


def clear_particle_cache() -> None:
    """조사 캐시를 초기화합니다."""
    global _particle_cache
    _particle_cache.clear()


def get_cache_stats() -> Dict[str, int]:
    """캐시 통계를 반환합니다."""
    return {
        'particle_cache_size': len(_particle_cache)
    }


def validate_text_input(text: str, max_length: Optional[int] = None) -> bool:
    """
    텍스트 입력 유효성 검사
    
    Args:
        text: 검사할 텍스트
        max_length: 최대 길이 제한
        
    Returns:
        bool: 유효성 여부
    """
    if not isinstance(text, str):
        return False
    
    if max_length and len(text) > max_length:
        return False
    
    return True


def get_text_statistics(text: str) -> Dict[str, Union[int, float]]:
    """
    텍스트 통계 정보 반환
    
    Args:
        text: 분석할 텍스트
        
    Returns:
        Dict[str, Union[int, float]]: 텍스트 통계
    """
    if not text:
        return {
            'length': 0,
            'word_count': 0,
            'line_count': 0,
            'korean_char_count': 0,
            'estimated_reading_time': 0
        }
    
    lines = text.split('\n')
    words = text.split()
    
    return {
        'length': len(text),
        'word_count': len(words),
        'line_count': len(lines),
        'korean_char_count': count_korean_characters(text),
        'estimated_reading_time': estimate_reading_time(text)
    }


def normalize_text_for_comparison(text: str) -> str:
    """
    텍스트 비교를 위한 정규화
    
    Args:
        text: 정규화할 텍스트
        
    Returns:
        str: 정규화된 텍스트
    """
    if not text:
        return ""
    
    # 소문자 변환
    normalized = text.lower()
    
    # HTML 태그 제거
    normalized = extract_text_from_html(normalized)
    
    # 멘션 제거
    normalized = remove_mentions_from_text(normalized)
    
    # 공백 정규화
    normalized = normalize_spacing(normalized)
    
    # 특수문자 제거 (한글, 영문, 숫자만 유지)
    normalized = re.sub(r'[^\w\s가-힣ㄱ-ㅣ]', '', normalized)
    
    return normalized


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    두 텍스트 간의 유사도 계산 (간단한 구현)
    
    Args:
        text1: 첫 번째 텍스트
        text2: 두 번째 텍스트
        
    Returns:
        float: 유사도 (0.0 ~ 1.0)
    """
    if not text1 or not text2:
        return 0.0
    
    # 텍스트 정규화
    norm1 = normalize_text_for_comparison(text1)
    norm2 = normalize_text_for_comparison(text2)
    
    if not norm1 or not norm2:
        return 0.0
    
    # 단어 집합 생성
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    
    if not words1 and not words2:
        return 1.0
    
    # Jaccard 유사도 계산
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0.0


def extract_hashtags(text: str) -> List[str]:
    """
    텍스트에서 해시태그 추출
    
    Args:
        text: 분석할 텍스트
        
    Returns:
        List[str]: 해시태그 리스트 (# 제외)
    """
    if not text:
        return []
    
    # 해시태그 패턴: #단어
    pattern = r'#(\w+)'
    matches = re.findall(pattern, text)
    
    return list(set(matches))  # 중복 제거


def remove_hashtags_from_text(text: str) -> str:
    """
    텍스트에서 해시태그 제거
    
    Args:
        text: 원본 텍스트
        
    Returns:
        str: 해시태그가 제거된 텍스트
    """
    if not text:
        return text
    
    # 해시태그 패턴 제거
    pattern = r'#\w+'
    cleaned = re.sub(pattern, '', text)
    
    # 공백 정규화
    return normalize_spacing(cleaned)


def format_byte_size(size_bytes: int) -> str:
    """
    바이트 크기를 읽기 쉬운 형태로 변환
    
    Args:
        size_bytes: 바이트 크기
        
    Returns:
        str: 포맷된 크기 문자열
    """
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f}MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"


def is_valid_email(email: str) -> bool:
    """
    이메일 주소 유효성 검사
    
    Args:
        email: 검사할 이메일 주소
        
    Returns:
        bool: 유효성 여부
    """
    if not email:
        return False
    
    # 간단한 이메일 패턴 검사
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def sanitize_html(text: str) -> str:
    """
    HTML 태그를 안전하게 제거하고 텍스트만 추출
    
    Args:
        text: 원본 텍스트
        
    Returns:
        str: 정리된 텍스트
    """
    if not text:
        return ""
    
    try:
        soup = BeautifulSoup(text, 'html.parser')
        # 스크립트와 스타일 태그 제거
        for script in soup(["script", "style"]):
            script.decompose()
        return soup.get_text(separator=' ', strip=True)
    except Exception as e:
        logger.warning(f"HTML 정리 오류: {e}")
        return text


@safe_string_operation
def extract_mentions(text: str) -> List[str]:
    """
    멘션 추출 (백워드 호환성)
    
    Args:
        text: 분석할 텍스트
        
    Returns:
        List[str]: 멘션 리스트
    """
    return extract_mentions_from_text(text)


@safe_string_operation
def format_message(message: str, prefix: str = None) -> str:
    """
    메시지 포맷팅 (백워드 호환성)
    
    Args:
        message: 원본 메시지
        prefix: 접두사 (기본값: config.RESPONSE_PREFIX)
        
    Returns:
        str: 포맷된 메시지
    """
    if not message:
        return ""
    
    if prefix is None:
        prefix = getattr(config, 'RESPONSE_PREFIX', '✶ ')
    
    # 접두사가 이미 있으면 추가하지 않음
    if message.startswith(prefix):
        return message
    
    return f"{prefix}{message}"