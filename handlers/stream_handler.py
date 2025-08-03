"""
스트림 핸들러 (실시간 데이터 반영 최적화)
마스토돈 스트리밍 이벤트를 처리하고 최적화된 명령어 라우터와 연동
메모리 효율성과 성능 최적화에 중점을 둔 완전한 재설계
"""

import os
import sys
import time
import threading
from typing import Optional, Tuple, Any, List, Dict, Set
from bs4 import BeautifulSoup
from dataclasses import dataclass
from datetime import datetime
import pytz

# 경로 설정 (VM 환경 대응)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

try:
    import mastodon
    from config.settings import config
    from utils.logging_config import logger, bot_logger, LogContext
    from utils.sheets import SheetsManager
    from handlers.command_router import parse_command_from_text, validate_command_format
    from models.command_result import CommandResult, CommandType, global_stats
    from utils.text_processing import (
        extract_text_from_html, 
        has_command_format, 
        detect_korean_particle,
        format_with_particle
    )
    from utils.dm_sender import DMSender, initialize_dm_sender
    from models.command_result import TransferResult
    from utils.message_chunking import MessageChunker
except ImportError:
    # VM 환경에서 임포트 실패 시 폴백
    import logging
    logger = logging.getLogger('stream_handler')
    
    # 마스토돈 더미 클래스
    class StreamListener:
        pass
    
    # CommandType fallback for VM environment
    class CommandType:
        UNKNOWN = "unknown"
        DICE = "dice"
        CARD = "card"
        FORTUNE = "fortune"
        HELP = "help"
        CUSTOM = "custom"
    
    class CommandResult:
        @staticmethod
        def error(**kwargs):
            return None
    
    # SheetsManager fallback
    class SheetsManager:
        pass
    
    # text_processing 함수들 fallback
    def extract_text_from_html(html_content: str) -> str:
        """HTML 태그 제거하여 텍스트 추출 (fallback)"""
        if not html_content:
            return ""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.get_text(separator=' ', strip=True)
        except:
            # BeautifulSoup도 실패하면 간단한 태그 제거
            import re
            return re.sub(r'<[^>]+>', '', html_content)
    
    def has_command_format(text: str) -> bool:
        """텍스트에 명령어 형식이 있는지 확인 (fallback)"""
        if not text:
            return False
        return '[' in text and ']' in text
    
    def detect_korean_particle(word: str, particle_type: str = 'object') -> str:
        """한국어 조사 감지 (fallback)"""
        return '을' if particle_type == 'object' else '이'
    
    def format_with_particle(word: str, particle_type: str) -> str:
        """조사와 함께 포맷팅 (fallback)"""
        particle = detect_korean_particle(word, particle_type)
        return f"{word}{particle}"
    
    # parse_command_from_text fallback
    def parse_command_from_text(text: str) -> List[str]:
        """텍스트에서 명령어 키워드 추출 (fallback)"""
        if not text:
            return []
        
        import re
        # 빠른 패턴 매칭
        match = re.search(r'\[([^\]]+)\]', text)
        if not match:
            return []
        
        keywords_str = match.group(1)
        if not keywords_str:
            return []
        
        # 키워드 분할
        keywords = []
        for keyword in keywords_str.split('/'):
            clean_keyword = keyword.strip()
            if clean_keyword:
                keywords.append(clean_keyword)
        
        return keywords
    
    # validate_command_format fallback
    def validate_command_format(text: str) -> Tuple[bool, str]:
        """명령어 형식 유효성 검사 (fallback)"""
        if not text:
            return False, "텍스트가 비어있습니다."
        
        # 기본 형식 확인
        if '[' not in text or ']' not in text:
            return False, "명령어는 [명령어] 형식으로 입력해야 합니다."
        
        start_pos = text.find('[')
        end_pos = text.find(']')
        
        if start_pos >= end_pos:
            return False, "명령어 형식이 올바르지 않습니다. [명령어] 순서를 확인해주세요."
        
        # 키워드 추출 및 확인
        keywords = parse_command_from_text(text)
        if not keywords:
            return False, "명령어가 비어있습니다."
        
        return True, "올바른 명령어 형식입니다."
    
    # LogContext fallback
    class LogContext:
        def __init__(self, operation: str, **kwargs):
            self.operation = operation
            self.kwargs = kwargs
        
        def __enter__(self):
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass


def validate_stream_dependencies() -> Tuple[bool, List[str]]:
    """
    스트림 핸들러 의존성 검증
    
    Returns:
        Tuple[bool, List[str]]: (검증 성공 여부, 오류 목록)
    """
    errors = []
    
    try:
        # mastodon 모듈 확인
        import mastodon
    except ImportError:
        errors.append("mastodon 모듈을 찾을 수 없습니다")
    
    try:
        # BeautifulSoup 확인
        from bs4 import BeautifulSoup
    except ImportError:
        errors.append("beautifulsoup4 모듈을 찾을 수 없습니다")
    
    try:
        # pytz 확인
        import pytz
    except ImportError:
        errors.append("pytz 모듈을 찾을 수 없습니다")
    
    # 설정 확인
    try:
        from config.settings import config
    except ImportError:
        errors.append("설정 파일을 찾을 수 없습니다")
    
    return len(errors) == 0, errors


@dataclass
class MentionEvent:
    """멘션 이벤트 데이터"""
    notification_id: str
    status_id: str
    user_id: str
    user_name: str
    content: str
    text_content: str
    visibility: str
    mentioned_users: List[str]
    timestamp: datetime
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(pytz.timezone('Asia/Seoul'))


@dataclass
class ProcessingMetrics:
    """처리 성능 지표"""
    total_notifications: int = 0
    processed_mentions: int = 0
    successful_commands: int = 0
    failed_commands: int = 0
    ignored_notifications: int = 0
    dm_sent: int = 0
    avg_processing_time: float = 0.0
    error_rate: float = 0.0
    
    def update_avg_time(self, new_time: float, count: int):
        """평균 처리 시간 업데이트"""
        if count > 0:
            self.avg_processing_time = ((self.avg_processing_time * (count - 1)) + new_time) / count


class BotStreamHandler(mastodon.StreamListener):
    """
    최적화된 마스토돈 스트림 핸들러
    
    메모리 효율성과 성능 최적화:
    - 경량화된 이벤트 처리
    - 스마트한 메시지 분할
    - 효율적인 멘션 처리
    - 실시간 성능 모니터링
    """
    
    def __init__(self, api: mastodon.Mastodon, sheets_manager: Optional[SheetsManager]):
        """
        BotStreamHandler 초기화
        
        Args:
            api: 마스토돈 API 객체
            sheets_manager: 최적화된 Google Sheets 관리자
        """
        super().__init__()
        self.api = api
        self.sheets_manager = sheets_manager
        from handlers.command_router import initialize_command_router
        from utils.dm_sender import initialize_dm_sender
        from utils.message_chunking import MessageChunker
        self.command_router = initialize_command_router(sheets_manager)
        
        # DM 전송기 초기화
        self.dm_sender = initialize_dm_sender(api)
        
        # 메시지 분할기 초기화
        self.message_chunker = MessageChunker(max_length=490)
        
        # 봇 계정 정보 (경량화된 캐싱)
        self._bot_account_cache = {
            'info': None,
            'last_updated': 0,
            'ttl': 3600  # 1시간
        }
        
        # 성능 지표 (최소화)
        self.metrics = ProcessingMetrics()
        self._processing_times = []  # 최근 100개만 유지
        self._lock = threading.RLock()
        
        # 설정
        self.max_response_length = 490
        self.max_thread_messages = 10
        self.api_delay = 0.5  # API 호출 간 지연
        
        logger.info("최적화된 BotStreamHandler 초기화 완료")
    
    def on_notification(self, notification) -> None:
        """
        알림 이벤트 처리 (최적화)
        
        Args:
            notification: 마스토돈 알림 객체
        """
        start_time = time.time()
        
        with self._lock:
            self.metrics.total_notifications += 1
        
        try:
            # 멘션만 처리 (빠른 필터링)
            if notification.type != 'mention':
                with self._lock:
                    self.metrics.ignored_notifications += 1
                return
            
            # 멘션 이벤트 생성
            mention_event = self._create_mention_event(notification)
            if not mention_event:
                with self._lock:
                    self.metrics.ignored_notifications += 1
                return
            
            # 명령어 형식 확인 (빠른 체크)
            if not has_command_format(mention_event.text_content):
                with self._lock:
                    self.metrics.ignored_notifications += 1
                return
            
            with self._lock:
                self.metrics.processed_mentions += 1
            
            # 멘션 처리
            with LogContext("멘션 처리", 
                          notification_id=mention_event.notification_id,
                          user_id=mention_event.user_id):
                self._process_mention(mention_event)
            
            # 처리 시간 기록
            processing_time = time.time() - start_time
            self._record_processing_time(processing_time)
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"알림 처리 중 예상치 못한 오류: {e}", exc_info=True)
            
            with self._lock:
                self.metrics.failed_commands += 1
            
            # 에러 응답 전송 시도
            try:
                self._send_error_response_safe(notification, "일시적인 오류가 발생했습니다.")
            except Exception:
                logger.error("오류 응답 전송 실패")
            
            self._record_processing_time(processing_time)
    
    def _create_mention_event(self, notification) -> Optional[MentionEvent]:
        """
        마스토돈 알림에서 멘션 이벤트 생성
        
        Args:
            notification: 마스토돈 알림 객체
            
        Returns:
            Optional[MentionEvent]: 멘션 이벤트 또는 None
        """
        try:
            status = notification.status
            
            # 기본 정보 추출
            user_id = status.account.acct
            user_name = status.account.display_name or status.account.username
            content = status.content
            visibility = getattr(status, 'visibility', 'public')
            
            # HTML 태그 제거하여 텍스트 추출
            text_content = extract_text_from_html(content)
            
            # 멘션된 사용자들 추출
            mentioned_users = self._extract_mentioned_users_fast(status)
            
            return MentionEvent(
                notification_id=notification.id,
                status_id=status.id,
                user_id=user_id,
                user_name=user_name,
                content=content,
                text_content=text_content,
                visibility=visibility,
                mentioned_users=mentioned_users,
                timestamp=datetime.now(pytz.timezone('Asia/Seoul'))
            )
            
        except Exception as e:
            logger.error(f"멘션 이벤트 생성 실패: {e}")
            return None
    
    def _extract_mentioned_users_fast(self, status) -> List[str]:
        """
        멘션된 사용자들 빠른 추출 (최적화)
        
        Args:
            status: 마스토돈 status 객체
            
        Returns:
            List[str]: 멘션된 사용자 ID 목록 (봇 제외)
        """
        mentioned_users = set()
        
        try:
            # 1. mentions 속성에서 추출 (가장 정확함)
            if hasattr(status, 'mentions') and status.mentions:
                for mention in status.mentions:
                    user_acct = mention.get('acct', '')
                    if user_acct and not self._is_bot_account_fast(user_acct):
                        mentioned_users.add(user_acct)
            
            # 2. 원작성자도 포함 (자신이 아닌 경우)
            author_acct = status.account.acct
            if author_acct and not self._is_bot_account_fast(author_acct):
                mentioned_users.add(author_acct)
            
            # 3. mentions가 없는 경우 HTML에서 파싱 (최후의 수단)
            if not mentioned_users:
                soup = BeautifulSoup(status.content, 'html.parser')
                mention_links = soup.find_all('a', class_='mention')
                
                for link in mention_links[:5]:  # 최대 5개만 처리
                    href = link.get('href', '')
                    if '@' in href:
                        user_id = href.split('@')[-1]
                        if user_id and not self._is_bot_account_fast(user_id):
                            mentioned_users.add(user_id)
            
            result = list(mentioned_users)
            result.sort()  # 일관된 순서
            
            logger.debug(f"추출된 멘션 사용자: {result}")
            return result
            
        except Exception as e:
            logger.warning(f"멘션 사용자 추출 실패: {e}")
            # 실패 시 최소한 원작성자는 포함
            author_acct = status.account.acct
            if author_acct and not self._is_bot_account_fast(author_acct):
                return [author_acct]
            return []
    
    def _is_bot_account_fast(self, acct: str) -> bool:
        """
        봇 계정인지 빠른 확인 (캐싱 최적화)
        
        Args:
            acct: 확인할 계정 ID
            
        Returns:
            bool: 봇 계정 여부
        """
        if not acct:
            return False
        
        # 설정 기반 빠른 체크
        clean_acct = acct.lstrip('@').lower()
        
        # 설정된 봇 계정명들과 비교
        for bot_name in config.BOT_ACCOUNT_NAMES:
            if bot_name.lower() in clean_acct:
                return True
        
        # API를 통한 정확한 확인 (캐싱)
        current_time = time.time()
        cache = self._bot_account_cache
        
        if (cache['info'] is None or 
            current_time - cache['last_updated'] > cache['ttl']):
            
            try:
                cache['info'] = self.api.me()
                cache['last_updated'] = current_time
                logger.debug("봇 계정 정보 캐시 갱신")
            except Exception as e:
                logger.warning(f"봇 계정 정보 조회 실패: {e}")
                return False
        
        if cache['info']:
            bot_acct = cache['info'].get('acct', '').lstrip('@').lower()
            return clean_acct == bot_acct
        
        return False
    
    def _process_mention(self, mention_event: MentionEvent) -> None:
        """
        최적화된 멘션 처리
        
        Args:
            mention_event: 멘션 이벤트
        """
        # 명령어 추출
        keywords = parse_command_from_text(mention_event.text_content)
        if not keywords:
            logger.debug(f"명령어 추출 실패: {mention_event.user_id}")
            return
        
        # 명령어 실행
        command_result = self._execute_command_fast(mention_event.user_id, keywords)
        
        # 응답 전송
        success = self._send_response(mention_event, command_result)
        
        # 통계 업데이트
        with self._lock:
            if success and command_result.is_successful():
                self.metrics.successful_commands += 1
            else:
                self.metrics.failed_commands += 1
        
        # 전역 통계에도 추가
        try:
            global_stats.add_result(command_result)
        except Exception:
            pass  # 통계 실패는 무시
    
    def _execute_command_fast(self, user_id: str, keywords: List[str]) -> CommandResult:
        """
        빠른 명령어 실행
        
        Args:
            user_id: 사용자 ID
            keywords: 키워드 리스트
            
        Returns:
            CommandResult: 실행 결과
        """
        start_time = time.time()
        
        try:
            # 명령어 라우터를 통한 실행
            result = self.command_router.route_command(user_id, keywords)
            
            execution_time = time.time() - start_time
            
            # 실행 시간 로깅 (간소화)
            if execution_time > 3.0:  # 3초 이상 걸린 경우만 경고
                logger.warning(f"느린 명령어 실행: {keywords} - {execution_time:.2f}초")
            else:
                logger.debug(f"명령어 실행: {user_id} - [{'/'.join(keywords)}] - {execution_time:.3f}초")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"명령어 실행 중 오류: {keywords} - {e}")
            
            # 오류 결과 생성 (안전한 방식)
            try:
                # CommandType이 정의되지 않은 경우를 위한 폴백
                command_type = getattr(CommandType, 'UNKNOWN', 'unknown')
                return CommandResult.error(
                    command_type=command_type,
                    user_id=user_id,
                    user_name=user_id,
                    original_command=f"[{'/'.join(keywords)}]",
                    error=e,
                    execution_time=execution_time
                )
            except Exception:
                # 최종 폴백
                class DummyResult:
                    def __init__(self, message):
                        self.message = message
                    def is_successful(self):
                        return False
                    def get_user_message(self):
                        return self.message
                    def get_log_message(self):
                        return f"오류: {self.message}"
                
                return DummyResult("명령어 실행 중 오류가 발생했습니다.")
    
    def _send_response(self, mention_event: MentionEvent, command_result: CommandResult) -> bool:
        """
        최적화된 응답 전송
        
        Args:
            mention_event: 멘션 이벤트
            command_result: 명령어 실행 결과
            
        Returns:
            bool: 전송 성공 여부
        """
        try:
            # 모든 참여자 멘션 생성
            mentions = ' '.join([f"@{user}" for user in mention_event.mentioned_users])
            
            # 실패한 경우 단순 오류 메시지 전송
            if not command_result.is_successful():
                formatted_message = config.format_response(command_result.message)
                full_message = f"{mentions} {formatted_message}"
                
                self._send_single_status(mention_event.status_id, full_message, mention_event.visibility)
                logger.info(f"오류 응답 전송: {mention_event.user_id}")
                return True
            
            # 성공한 경우 메시지 길이에 따라 처리
            formatted_message = config.format_response(command_result.message)
            full_message = f"{mentions} {formatted_message}"
            message_length = len(full_message)
            
            if message_length <= self.max_response_length:
                # 짧은 메시지: 단일 답장
                success = self._send_single_status(mention_event.status_id, full_message, mention_event.visibility)
                logger.info(f"단일 응답 전송: {mention_event.user_id} ({message_length}자)")
                
            else:
                # 긴 메시지: 스레드 답장
                logger.info(f"긴 메시지 감지: {mention_event.user_id} ({message_length}자), 스레드로 전송")
                success = self._send_threaded_response(mention_event, command_result, mentions)
            
            # 양도 명령어인 경우 DM 전송 처리
            if success:
                self._handle_transfer_dm(command_result)
            
            return success
        
        except Exception as e:
            logger.error(f"응답 전송 실패: {mention_event.user_id} - {e}")
            
            try:
                # 에러 메시지 전송 시도
                mentions = ' '.join([f"@{user}" for user in mention_event.mentioned_users])
                error_message = config.format_response("응답 처리 중 오류가 발생했습니다.")
                self._send_single_status(mention_event.status_id, f"{mentions} {error_message}", mention_event.visibility)
                return False
            except Exception:
                logger.error("오류 메시지 전송도 실패")
                return False
    
    def _send_single_status(self, reply_to_id: str, message: str, visibility: str) -> bool:
        """
        단일 상태 전송
        
        Args:
            reply_to_id: 답장할 상태 ID
            message: 메시지
            visibility: 공개 범위
            
        Returns:
            bool: 전송 성공 여부
        """
        try:
            self.api.status_post(
                in_reply_to_id=reply_to_id,
                status=message,
                visibility=visibility
            )
            return True
        except Exception as e:
            logger.error(f"단일 상태 전송 실패: {e}")
            return False
    
    def _send_threaded_response(self, mention_event: MentionEvent, 
                                        command_result: CommandResult, mentions: str) -> bool:
        """
        최적화된 스레드 응답 전송
        
        Args:
            mention_event: 멘션 이벤트
            command_result: 명령어 결과
            mentions: 멘션 문자열
            
        Returns:
            bool: 전송 성공 여부
        """
        try:
            # 메시지 분할
            chunks = self._split_message_smart(command_result)
            
            if len(chunks) > self.max_thread_messages:
                # 너무 많은 메시지인 경우 제한
                chunks = chunks[:self.max_thread_messages]
                chunks[-1] += "\n\n(메시지가 길어 일부가 생략되었습니다)"
            
            # 청크들을 순차적으로 전송
            reply_to_id = mention_event.status_id
            sent_count = 0
            
            for i, chunk in enumerate(chunks):
                try:
                    # 첫 번째 청크에만 멘션 포함
                    if i == 0:
                        full_chunk = f"{mentions} {config.format_response(chunk)}"
                    else:
                        full_chunk = config.format_response(chunk)
                    
                    status = self.api.status_post(
                        in_reply_to_id=reply_to_id,
                        status=full_chunk,
                        visibility=mention_event.visibility
                    )
                    
                    reply_to_id = status['id']  # 다음 답장은 방금 보낸 툿에 연결
                    sent_count += 1
                    
                    # API 제한 고려하여 대기 (마지막 제외)
                    if i < len(chunks) - 1:
                        time.sleep(self.api_delay)
                    
                except Exception as e:
                    logger.error(f"청크 {i+1} 전송 실패: {e}")
                    break
            
            logger.info(f"스레드 응답 완료: {mention_event.user_id}, {sent_count}/{len(chunks)}개 툿 전송")
            return sent_count > 0
            
        except Exception as e:
            logger.error(f"스레드 응답 전송 실패: {e}")
            return False
    
    def _split_message_smart(self, command_result: CommandResult) -> List[str]:
        """
        스마트한 메시지 분할
        
        Args:
            command_result: 명령어 결과
            
        Returns:
            List[str]: 분할된 메시지 리스트
        """
        try:
            # 결과 타입별 특별 처리
            if hasattr(command_result, 'result_data') and command_result.result_data:
                result_data = command_result.result_data
                
                # 상점 결과
                if hasattr(result_data, 'items') and hasattr(result_data, 'currency_unit'):
                    return self.message_chunker.split_shop_items(result_data.items, result_data.currency_unit)
                
                # 인벤토리 결과
                elif hasattr(result_data, 'inventory') and hasattr(result_data, 'user_name'):
                    return self.message_chunker.split_inventory_items(
                        result_data.inventory, 
                        result_data.user_name, 
                        getattr(result_data, 'suffix', '의')
                    )
            
            # 기본 메시지 분할
            return self.message_chunker.split_message(command_result.message)
            
        except Exception as e:
            logger.error(f"메시지 분할 실패: {e}")
            # 폴백: 기본 분할
            return self.message_chunker.split_message(command_result.message)
    
    def _handle_transfer_dm(self, command_result: CommandResult) -> None:
        """
        최적화된 양도 DM 처리
        
        Args:
            command_result: 명령어 결과
        """
        try:
            # TransferResult인지 확인
            if (hasattr(command_result, 'result_data') and 
                command_result.result_data and 
                isinstance(command_result.result_data, TransferResult)):
                
                transfer_result = command_result.result_data
                
                # DM 전송이 성공으로 표시된 경우에만 실제 전송
                if transfer_result.dm_sent and self.dm_sender:
                    # 조사 처리
                    giver_subject = self._get_korean_particle(transfer_result.giver_name, 'subject')
                    item_particle = self._get_korean_particle(transfer_result.item_name, 'object')
                    
                    # DM 전송
                    dm_success = self.dm_sender.send_transfer_notification(
                        receiver_id=transfer_result.receiver_id,
                        giver_name=transfer_result.giver_name,
                        giver_subject=giver_subject,
                        item_name=transfer_result.item_name,
                        item_particle=item_particle
                    )
                    
                    if dm_success:
                        with self._lock:
                            self.metrics.dm_sent += 1
                        logger.info(f"양도 DM 전송 성공: {transfer_result.receiver_id}")
                    else:
                        logger.warning(f"양도 DM 전송 실패: {transfer_result.receiver_id}")
                
        except Exception as e:
            logger.error(f"DM 처리 중 오류: {e}")
    
    def _get_korean_particle(self, word: str, particle_type: str) -> str:
        """
        한글 조사 반환 (최적화)
        
        Args:
            word: 단어
            particle_type: 조사 타입 ('subject', 'object')
            
        Returns:
            str: 적절한 조사
        """
        try:
            return detect_korean_particle(word, particle_type)
        except (ImportError, Exception):
            # 폴백: 간단한 조사 처리
            if not word:
                return '이' if particle_type == 'subject' else '을'
            
            last_char = word[-1]
            if '가' <= last_char <= '힣':
                code = ord(last_char) - ord('가')
                has_final = (code % 28) != 0
                
                if particle_type == 'subject':
                    return '이' if has_final else '가'
                else:  # object
                    return '을' if has_final else '를'
            else:
                return '이' if particle_type == 'subject' else '을'
    
    def _send_error_response_safe(self, notification, error_message: str) -> None:
        """
        안전한 오류 응답 전송
        
        Args:
            notification: 원본 알림
            error_message: 오류 메시지
        """
        try:
            status = notification.status
            visibility = getattr(status, 'visibility', 'public')
            
            # 멘션된 사용자들 추출
            mentioned_users = self._extract_mentioned_users_fast(status)
            mentions = ' '.join([f"@{user}" for user in mentioned_users])
            
            formatted_message = config.format_response(error_message)
            self._send_single_status(status.id, f"{mentions} {formatted_message}", visibility)
            
        except Exception as e:
            logger.error(f"오류 응답 전송 실패: {e}")
    
    def _record_processing_time(self, processing_time: float) -> None:
        """
        처리 시간 기록 (메모리 효율적)
        
        Args:
            processing_time: 처리 시간 (초)
        """
        with self._lock:
            # 최근 100개만 유지
            self._processing_times.append(processing_time)
            if len(self._processing_times) > 100:
                self._processing_times.pop(0)
            
            # 평균 처리 시간 업데이트
            if self._processing_times:
                self.metrics.avg_processing_time = sum(self._processing_times) / len(self._processing_times)
            
            # 오류율 계산
            total_processed = self.metrics.successful_commands + self.metrics.failed_commands
            if total_processed > 0:
                self.metrics.error_rate = (self.metrics.failed_commands / total_processed) * 100
    
    def process_pending_dms(self) -> Dict[str, int]:
        """
        대기 중인 DM들을 처리
        
        Returns:
            Dict: 처리 결과
        """
        try:
            if self.dm_sender:
                return self.dm_sender.process_pending_dms()
            return {'processed': 0, 'success': 0, 'failed': 0, 'retries': 0}
        except Exception as e:
            logger.error(f"DM 처리 실패: {e}")
            return {'processed': 0, 'success': 0, 'failed': 0, 'retries': 0}
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        핸들러 통계 정보 반환 (최적화)
        
        Returns:
            Dict: 통계 정보
        """
        with self._lock:
            current_time = time.time()
            
            # 기본 통계
            stats = {
                'total_notifications': self.metrics.total_notifications,
                'processed_mentions': self.metrics.processed_mentions,
                'successful_commands': self.metrics.successful_commands,
                'failed_commands': self.metrics.failed_commands,
                'ignored_notifications': self.metrics.ignored_notifications,
                'dm_sent': self.metrics.dm_sent,
                'avg_processing_time': self.metrics.avg_processing_time,
                'error_rate': self.metrics.error_rate,
                'processing_efficiency': self._calculate_efficiency()
            }
            
            # 처리율 계산
            if self.metrics.total_notifications > 0:
                stats['mention_rate'] = (self.metrics.processed_mentions / self.metrics.total_notifications) * 100
                stats['success_rate'] = (self.metrics.successful_commands / self.metrics.processed_mentions * 100) if self.metrics.processed_mentions > 0 else 0
            else:
                stats['mention_rate'] = 0
                stats['success_rate'] = 0
            
            # 처리 시간 분석
            if self._processing_times:
                stats['min_processing_time'] = min(self._processing_times)
                stats['max_processing_time'] = max(self._processing_times)
                stats['recent_avg_time'] = sum(self._processing_times[-10:]) / min(10, len(self._processing_times))
            
            return stats
    
    def get_handler_statistics(self) -> Dict[str, Any]:
        """핸들러 통계 정보 반환 (별칭)"""
        return self.get_statistics()
    
    def _calculate_efficiency(self) -> float:
        """
        처리 효율성 계산
        
        Returns:
            float: 효율성 점수 (0-100)
        """
        try:
            # 성공률, 처리 속도, 오류율을 종합한 효율성 점수
            success_score = (self.metrics.successful_commands / max(1, self.metrics.processed_mentions)) * 100
            speed_score = max(0, 100 - (self.metrics.avg_processing_time * 50))  # 2초 = 0점
            error_score = max(0, 100 - self.metrics.error_rate * 5)  # 20% 오류율 = 0점
            
            efficiency = (success_score * 0.5 + speed_score * 0.3 + error_score * 0.2)
            return min(100, max(0, efficiency))
            
        except Exception:
            return 0.0
    
    def start_streaming(self, max_retries: int = 3) -> bool:
        """스트리밍 시작"""
        try:
            logger.info("🚀 마스토돈 스트리밍 시작...")
            
            # 실제 마스토돈 스트리밍 시작 (스트림 객체 저장)
            self._stream = self.api.stream_user(self)
            
            logger.info("✅ 스트리밍 시작 완료")
            return True
        except Exception as e:
            logger.error(f"❌ 스트리밍 시작 중 오류: {e}")
            return False
    
    def stop_streaming(self) -> None:
        """스트리밍 중지"""
        try:
            logger.info("🛑 스트리밍 중지 요청")
            # 스트리밍 중지 (close 메서드 호출)
            if hasattr(self, '_stream') and self._stream:
                self._stream.close()
            logger.info("✅ 스트리밍 중지 완료")
        except Exception as e:
            logger.error(f"❌ 스트리밍 중지 중 오류: {e}")
    
    def reset_statistics(self) -> None:
        """통계 초기화"""
        with self._lock:
            self.metrics = ProcessingMetrics()
            self._processing_times.clear()
            logger.info("핸들러 통계 초기화")
    
    def health_check(self) -> Dict[str, Any]:
        """
        핸들러 상태 확인 (종합적)
        
        Returns:
            Dict: 상태 정보
        """
        health_status = {
            'status': 'healthy',
            'errors': [],
            'warnings': [],
            'details': {}
        }
        
        try:
            # API 연결 상태 확인
            if not self.api:
                health_status['errors'].append("마스토돈 API 객체 없음")
                health_status['status'] = 'error'
            
            # Sheets 관리자 상태 확인
            if not self.sheets_manager:
                health_status['errors'].append("Sheets 관리자 없음")
                health_status['status'] = 'error'
            else:
                # Sheets 매니저 상태 확인
                try:
                    sheets_health = self.sheets_manager.health_check()
                    health_status['details']['sheets_health'] = sheets_health
                    
                    if sheets_health['status'] != 'healthy':
                        health_status['warnings'].extend(sheets_health.get('warnings', []))
                        health_status['errors'].extend(sheets_health.get('errors', []))
                        
                        if sheets_health['status'] == 'error':
                            health_status['status'] = 'error'
                        elif sheets_health['status'] == 'warning' and health_status['status'] == 'healthy':
                            health_status['status'] = 'warning'
                except Exception as e:
                    health_status['warnings'].append(f"Sheets 상태 확인 실패: {str(e)}")
            
            # 명령어 라우터 상태 확인
            if not self.command_router:
                health_status['errors'].append("명령어 라우터 없음")
                health_status['status'] = 'error'
            else:
                try:
                    router_health = self.command_router.health_check()
                    health_status['details']['router_health'] = router_health
                    
                    if router_health['status'] != 'healthy':
                        health_status['warnings'].extend(router_health.get('warnings', []))
                        health_status['errors'].extend(router_health.get('errors', []))
                        
                        if router_health['status'] == 'error':
                            health_status['status'] = 'error'
                        elif router_health['status'] == 'warning' and health_status['status'] == 'healthy':
                            health_status['status'] = 'warning'
                except Exception as e:
                    health_status['warnings'].append(f"라우터 상태 확인 실패: {str(e)}")
            
            # DM 전송기 상태 확인
            if self.dm_sender:
                try:
                    dm_health = self.dm_sender.health_check()
                    health_status['details']['dm_health'] = dm_health
                    
                    if dm_health['status'] != 'healthy':
                        health_status['warnings'].extend(dm_health.get('warnings', []))
                        health_status['errors'].extend(dm_health.get('errors', []))
                        
                        if dm_health['status'] == 'error':
                            health_status['status'] = 'error'
                        elif dm_health['status'] == 'warning' and health_status['status'] == 'healthy':
                            health_status['status'] = 'warning'
                except Exception as e:
                    health_status['warnings'].append(f"DM 전송기 상태 확인 실패: {str(e)}")
            
            # 성능 지표 확인
            stats = self.get_statistics()
            health_status['details']['performance'] = stats
            
            # 성능 기준 검사
            if stats['total_notifications'] > 10:  # 최소 10개 이상 처리한 경우
                if stats['error_rate'] > 20:  # 20% 이상 오류율
                    health_status['warnings'].append(f"높은 오류율: {stats['error_rate']:.1f}%")
                    health_status['status'] = 'warning' if health_status['status'] == 'healthy' else health_status['status']
                
                if stats['avg_processing_time'] > 5.0:  # 5초 이상 평균 처리 시간
                    health_status['warnings'].append(f"느린 평균 처리 시간: {stats['avg_processing_time']:.3f}초")
                    health_status['status'] = 'warning' if health_status['status'] == 'healthy' else health_status['status']
                
                if stats['processing_efficiency'] < 70:  # 70% 미만 효율성
                    health_status['warnings'].append(f"낮은 처리 효율성: {stats['processing_efficiency']:.1f}%")
                    health_status['status'] = 'warning' if health_status['status'] == 'healthy' else health_status['status']
            
            # 메모리 사용량 추정
            memory_items = len(self._processing_times) + len(self.metrics.__dict__)
            health_status['details']['estimated_memory_items'] = memory_items
            
            if memory_items > 500:  # 메모리 사용량이 많은 경우
                health_status['warnings'].append(f"높은 메모리 사용량: {memory_items}개 항목")
                health_status['status'] = 'warning' if health_status['status'] == 'healthy' else health_status['status']
            
            # 봇 계정 캐시 상태
            cache_age = time.time() - self._bot_account_cache['last_updated']
            health_status['details']['bot_account_cache'] = {
                'has_info': self._bot_account_cache['info'] is not None,
                'cache_age_seconds': cache_age,
                'is_fresh': cache_age < self._bot_account_cache['ttl']
            }
            
        except Exception as e:
            health_status['errors'].append(f"상태 확인 중 오류: {str(e)}")
            health_status['status'] = 'error'
            logger.error(f"Health check 실패: {e}", exc_info=True)
        
        return health_status
    
    def optimize_performance(self) -> Dict[str, Any]:
        """
        성능 최적화 실행
        
        Returns:
            Dict: 최적화 결과
        """
        optimization_results = {
            'actions_taken': [],
            'memory_freed': 0,
            'performance_improved': False
        }
        
        try:
            with self._lock:
                # 처리 시간 리스트 정리
                if len(self._processing_times) > 50:
                    old_count = len(self._processing_times)
                    self._processing_times = self._processing_times[-50:]  # 최근 50개만 유지
                    freed = old_count - len(self._processing_times)
                    optimization_results['memory_freed'] += freed
                    optimization_results['actions_taken'].append(f"처리 시간 기록 정리: {freed}개 항목 제거")
                
                # 봇 계정 캐시 갱신
                cache_age = time.time() - self._bot_account_cache['last_updated']
                if cache_age > self._bot_account_cache['ttl']:
                    self._bot_account_cache['info'] = None
                    self._bot_account_cache['last_updated'] = 0
                    optimization_results['actions_taken'].append("봇 계정 캐시 만료 처리")
            
            # 명령어 라우터 최적화
            if self.command_router:
                try:
                    from handlers.command_router import optimize_router_performance
                    optimize_router_performance()
                    optimization_results['actions_taken'].append("명령어 라우터 최적화 실행")
                except Exception as e:
                    logger.warning(f"라우터 최적화 실패: {e}")
            
            # DM 처리
            if self.dm_sender:
                try:
                    dm_results = self.process_pending_dms()
                    if dm_results['processed'] > 0:
                        optimization_results['actions_taken'].append(f"대기 DM 처리: {dm_results['processed']}개")
                except Exception as e:
                    logger.warning(f"DM 처리 실패: {e}")
            
            # 성능 개선 여부 확인
            if optimization_results['memory_freed'] > 0 or len(optimization_results['actions_taken']) > 1:
                optimization_results['performance_improved'] = True
            
            logger.info(f"성능 최적화 완료: {len(optimization_results['actions_taken'])}개 작업 수행")
            
        except Exception as e:
            logger.error(f"성능 최적화 중 오류: {e}")
            optimization_results['actions_taken'].append(f"최적화 중 오류 발생: {str(e)}")
        
        return optimization_results


# 성능 모니터링 및 리포트 생성
def generate_stream_handler_report(handler: BotStreamHandler) -> str:
    """
    스트림 핸들러 성능 리포트 생성
    
    Args:
        handler: 스트림 핸들러 인스턴스
        
    Returns:
        str: 성능 리포트
    """
    try:
        stats = handler.get_statistics()
        health = handler.health_check()
        
        report_lines = ["=== 스트림 핸들러 성능 리포트 ==="]
        
        # 기본 통계
        report_lines.append(f"\n📊 처리 통계:")
        report_lines.append(f"  총 알림: {stats['total_notifications']:,}개")
        report_lines.append(f"  처리된 멘션: {stats['processed_mentions']:,}개 ({stats['mention_rate']:.1f}%)")
        report_lines.append(f"  성공한 명령어: {stats['successful_commands']:,}개")
        report_lines.append(f"  실패한 명령어: {stats['failed_commands']:,}개")
        report_lines.append(f"  무시된 알림: {stats['ignored_notifications']:,}개")
        report_lines.append(f"  전송된 DM: {stats['dm_sent']:,}개")
        
        # 성능 지표
        report_lines.append(f"\n🚀 성능 지표:")
        report_lines.append(f"  성공률: {stats['success_rate']:.1f}%")
        report_lines.append(f"  오류율: {stats['error_rate']:.1f}%")
        report_lines.append(f"  평균 처리시간: {stats['avg_processing_time']:.3f}초")
        report_lines.append(f"  처리 효율성: {stats['processing_efficiency']:.1f}%")
        
        if 'recent_avg_time' in stats:
            report_lines.append(f"  최근 평균시간: {stats['recent_avg_time']:.3f}초")
        
        if 'min_processing_time' in stats and 'max_processing_time' in stats:
            report_lines.append(f"  처리시간 범위: {stats['min_processing_time']:.3f}초 ~ {stats['max_processing_time']:.3f}초")
        
        # 상태 확인
        report_lines.append(f"\n🏥 상태: {health['status']}")
        
        if health['warnings']:
            report_lines.append(f"⚠️ 경고:")
            for warning in health['warnings']:
                report_lines.append(f"  - {warning}")
        
        if health['errors']:
            report_lines.append(f"❌ 오류:")
            for error in health['errors']:
                report_lines.append(f"  - {error}")
        
        # 하위 시스템 상태
        details = health.get('details', {})
        
        if 'sheets_health' in details:
            sheets_status = details['sheets_health']['status']
            report_lines.append(f"\n📊 Sheets 상태: {sheets_status}")
        
        if 'router_health' in details:
            router_status = details['router_health']['status']
            report_lines.append(f"🔀 라우터 상태: {router_status}")
        
        if 'dm_health' in details:
            dm_status = details['dm_health']['status']
            report_lines.append(f"💬 DM 전송기 상태: {dm_status}")
        
        # 메모리 사용량
        if 'estimated_memory_items' in details:
            memory_items = details['estimated_memory_items']
            report_lines.append(f"\n💾 메모리 사용량: 약 {memory_items}개 항목")
        
        # 최적화 정보
        report_lines.append(f"\n✅ 적용된 최적화:")
        report_lines.append(f"  - 경량화된 이벤트 처리")
        report_lines.append(f"  - 스마트한 메시지 분할")
        report_lines.append(f"  - 효율적인 멘션 추출")
        report_lines.append(f"  - 실시간 성능 모니터링")
        report_lines.append(f"  - 메모리 효율적 통계 수집")
        
        return "\n".join(report_lines)
        
    except Exception as e:
        return f"스트림 핸들러 리포트 생성 실패: {e}"


def test_stream_handler_performance():
    """스트림 핸들러 성능 테스트"""
    print("=== 스트림 핸들러 성능 테스트 ===")
    
    try:
        # 테스트용 더미 API와 시트 매니저
        class DummyAPI:
            def status_post(self, **kwargs):
                return {'id': 'test_status_id'}
            
            def me(self):
                return {'acct': 'test_bot'}
        
        class DummySheets:
            def find_user_by_id_real_time(self, user_id):
                return {'아이디': user_id, '이름': f'테스트_{user_id}'}
            
            def health_check(self):
                return {'status': 'healthy', 'warnings': [], 'errors': []}
        
        # 핸들러 생성
        handler = BotStreamHandler(DummyAPI(), DummySheets())
        
        print("1. 핸들러 초기화 완료")
        
        # 통계 확인
        stats = handler.get_statistics()
        print(f"2. 초기 통계: {stats['total_notifications']}개 알림, {stats['processing_efficiency']:.1f}% 효율성")
        
        # 상태 확인
        health = handler.health_check()
        print(f"3. 상태 확인: {health['status']}")
        
        # 성능 최적화 테스트
        optimization = handler.optimize_performance()
        print(f"4. 최적화 실행: {len(optimization['actions_taken'])}개 작업")
        
        # 리포트 생성
        report = generate_stream_handler_report(handler)
        print(f"5. 리포트 생성 완료 ({len(report)}자)")
        
        print("\n✅ 모든 테스트 완료")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
    
    print("=" * 60)


def benchmark_mention_processing():
    """멘션 처리 성능 벤치마크"""
    print("\n=== 멘션 처리 성능 벤치마크 ===")
    
    try:
        # 테스트 데이터
        test_mentions = [
            {'text': '[다이스/2d6] 테스트', 'expected_keywords': ['다이스', '2d6']},
            {'text': '[카드뽑기/5장] 카드 뽑기', 'expected_keywords': ['카드뽑기', '5장']},
            {'text': '[운세] 오늘 운세', 'expected_keywords': ['운세']},
            {'text': '[도움말] 명령어 보기', 'expected_keywords': ['도움말']},
            {'text': '[2d20] 주사위 굴리기', 'expected_keywords': ['2d20']},
        ]
        
        # 성능 측정
        total_time = 0
        processed_count = 0
        
        for i in range(100):  # 100회 반복
            for mention_data in test_mentions:
                start_time = time.time()
                
                # 명령어 추출 테스트
                keywords = parse_command_from_text(mention_data['text'])
                
                # 검증
                if keywords == mention_data['expected_keywords']:
                    processed_count += 1
                
                end_time = time.time()
                total_time += (end_time - start_time)
        
        # 결과 분석
        total_operations = 100 * len(test_mentions)
        avg_time = total_time / total_operations
        success_rate = (processed_count / total_operations) * 100
        ops_per_second = total_operations / total_time if total_time > 0 else 0
        
        print(f"1. 멘션 처리 벤치마크 결과:")
        print(f"   총 작업: {total_operations}회")
        print(f"   성공: {processed_count}회 ({success_rate:.1f}%)")
        print(f"   평균 시간: {avg_time*1000:.3f}ms")
        print(f"   초당 처리: {ops_per_second:.0f}회")
        print(f"   총 소요시간: {total_time:.3f}초")
        
        # 성능 기준 검증
        if avg_time < 0.001:  # 1ms 미만
            print("✅ 성능 기준 통과")
        else:
            print("❌ 성능 기준 미달")
        
    except Exception as e:
        print(f"❌ 벤치마크 실패: {e}")
    
    print("=" * 60)


# 백워드 호환성을 위한 별칭
StreamManager = BotStreamHandler


def initialize_stream_with_dm(api: mastodon.Mastodon, sheets_manager: Optional[SheetsManager]) -> BotStreamHandler:
    """
    DM 지원 기능이 있는 스트림 핸들러 초기화
    
    Args:
        api: 마스토돈 API 클라이언트
        sheets_manager: Google Sheets 관리자
        
    Returns:
        BotStreamHandler: 초기화된 스트림 핸들러
    """
    try:
        # DM 전송기 초기화
        from utils.dm_sender import initialize_dm_sender
        dm_sender = initialize_dm_sender(api)
        
        # 스트림 핸들러 생성
        handler = BotStreamHandler(api, sheets_manager)
        
        # DM 전송기를 핸들러에 연결
        handler.dm_sender = dm_sender
        
        logger.info("✅ DM 지원 스트림 핸들러 초기화 완료")
        return handler
        
    except Exception as e:
        logger.error(f"❌ DM 지원 스트림 핸들러 초기화 실패: {e}")
        # 폴백: 기본 핸들러 반환
        return BotStreamHandler(api, sheets_manager)


# 모듈 로드 완료 로깅
logger.info("최적화된 스트림 핸들러 모듈 로드 완료")


# 테스트 실행 (개발 환경에서만)
if __name__ == "__main__":
    test_stream_handler_performance()
    benchmark_mention_processing()