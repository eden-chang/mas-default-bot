"""
DM 전송 모듈
마스토돈 DM(Direct Message) 전송 기능을 제공합니다.
"""

import os
import sys
import time
import asyncio
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import pytz
from collections import deque

# 경로 설정 (VM 환경 대응)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

try:
    import mastodon
    from utils.logging_config import logger
    from config.settings import config
except ImportError:
    # VM 환경에서 임포트 실패 시 폴백
    import logging
    logger = logging.getLogger('dm_sender')
    
    # 더미 마스토돈 클래스
    class mastodon:
        class Mastodon:
            pass


class DMStatus(Enum):
    """DM 상태 열거형"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class DMMessage:
    """DM 메시지 데이터 클래스"""
    receiver_id: str
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(pytz.timezone('Asia/Seoul')))
    attempts: int = 0
    max_attempts: int = 3
    status: DMStatus = DMStatus.PENDING
    error: Optional[str] = None
    retry_delay: float = 1.0  # 재시도 간격 (초)
    
    def can_retry(self) -> bool:
        """재시도 가능 여부"""
        return self.status in [DMStatus.PENDING, DMStatus.FAILED] and self.attempts < self.max_attempts
    
    def mark_attempt(self, success: bool, error: str = None):
        """시도 결과 기록"""
        self.attempts += 1
        if success:
            self.status = DMStatus.SENT
            self.error = None
        else:
            self.status = DMStatus.FAILED if self.attempts >= self.max_attempts else DMStatus.RETRYING
            self.error = error
    
    def should_retry_now(self) -> bool:
        """지금 재시도해야 하는지 확인"""
        if not self.can_retry():
            return False
        
        # 재시도 간격 확인
        elapsed = (datetime.now(pytz.timezone('Asia/Seoul')) - self.timestamp).total_seconds()
        return elapsed >= self.retry_delay * self.attempts


class DMSender:
    """DM 전송 클래스"""
    
    def __init__(self, mastodon_client: mastodon.Mastodon, 
                 batch_size: int = 10, 
                 retry_delay: float = 1.0,
                 max_queue_size: int = 1000):
        """
        DMSender 초기화
        
        Args:
            mastodon_client: 마스토돈 클라이언트
            batch_size: 배치 처리 크기
            retry_delay: 재시도 간격 (초)
            max_queue_size: 최대 대기열 크기
        """
        self.mastodon = mastodon_client
        self.pending_dms: deque = deque(maxlen=max_queue_size)
        self.batch_size = batch_size
        self.retry_delay = retry_delay
        
        # 통계
        self.stats = {
            'total_sent': 0,
            'successful_sent': 0,
            'failed_sent': 0,
            'retry_attempts': 0,
            'queue_overflow': 0
        }
        
        # 성능 최적화를 위한 캐시
        self._receiver_cache = {}
        self._last_health_check = 0
        self._health_check_interval = 300  # 5분
    
    def send_dm(self, receiver_id: str, message: str) -> bool:
        """
        즉시 DM 전송
        
        Args:
            receiver_id: 수신자 마스토돈 ID
            message: 메시지 내용
            
        Returns:
            bool: 전송 성공 여부
        """
        if not self._validate_receiver_id(receiver_id):
            logger.error(f"유효하지 않은 수신자 ID: {receiver_id}")
            return False
        
        try:
            # DM으로 전송 (visibility='direct')
            status = self.mastodon.status_post(
                status=f"@{receiver_id} {message}",
                visibility='direct'
            )
            
            self._update_stats(success=True)
            logger.info(f"DM 전송 성공: {receiver_id} -> {message[:50]}...")
            return True
            
        except Exception as e:
            self._update_stats(success=False)
            logger.error(f"DM 전송 실패: {receiver_id} -> {e}")
            return False
    
    def queue_dm(self, receiver_id: str, message: str, priority: bool = False) -> bool:
        """
        DM을 대기열에 추가
        
        Args:
            receiver_id: 수신자 마스토돈 ID
            message: 메시지 내용
            priority: 우선순위 (True면 앞에 추가)
            
        Returns:
            bool: 대기열 추가 성공 여부
        """
        if not self._validate_receiver_id(receiver_id):
            logger.error(f"유효하지 않은 수신자 ID: {receiver_id}")
            return False
        
        if len(self.pending_dms) >= self.pending_dms.maxlen:
            self.stats['queue_overflow'] += 1
            logger.warning(f"대기열이 가득 찼습니다. 메시지 무시: {receiver_id}")
            return False
        
        dm_message = DMMessage(
            receiver_id=receiver_id,
            message=message,
            retry_delay=self.retry_delay
        )
        
        if priority:
            self.pending_dms.appendleft(dm_message)
        else:
            self.pending_dms.append(dm_message)
        
        logger.debug(f"DM 대기열 추가: {receiver_id} -> {message[:30]}...")
        return True
    
    def process_pending_dms(self, max_batches: int = 5) -> Dict[str, int]:
        """
        대기 중인 DM들을 배치 처리
        
        Args:
            max_batches: 최대 처리 배치 수
            
        Returns:
            Dict: 처리 결과 통계
        """
        if not self.pending_dms:
            return {'processed': 0, 'success': 0, 'failed': 0, 'retries': 0}
        
        results = {'processed': 0, 'success': 0, 'failed': 0, 'retries': 0}
        batches_processed = 0
        
        while self.pending_dms and batches_processed < max_batches:
            batch = self._get_ready_batch()
            if not batch:
                break
            
            batch_results = self._process_batch(batch)
            
            # 결과 합산
            for key in results:
                results[key] += batch_results[key]
            
            batches_processed += 1
        
        if results['processed'] > 0:
            logger.info(f"DM 배치 처리 완료: {results}")
        
        return results
    
    def _get_ready_batch(self) -> List[DMMessage]:
        """처리할 준비가 된 DM 배치 반환"""
        batch = []
        ready_dms = []
        
        # 재시도 가능하고 시간이 된 DM들 찾기
        for dm in self.pending_dms:
            if dm.should_retry_now():
                ready_dms.append(dm)
                if len(ready_dms) >= self.batch_size:
                    break
        
        # 배치 크기만큼 처리
        for dm in ready_dms[:self.batch_size]:
            batch.append(dm)
            self.pending_dms.remove(dm)
        
        return batch
    
    def _process_batch(self, batch: List[DMMessage]) -> Dict[str, int]:
        """배치 처리"""
        results = {'processed': 0, 'success': 0, 'failed': 0, 'retries': 0}
        
        for dm in batch:
            if not dm.can_retry():
                if dm.status == DMStatus.FAILED:
                    results['failed'] += 1
                continue
            
            results['processed'] += 1
            
            # 재시도인 경우 카운트
            if dm.attempts > 0:
                results['retries'] += 1
                self.stats['retry_attempts'] += 1
                # 재시도 시 지수 백오프 적용
                time.sleep(min(0.5 * (2 ** (dm.attempts - 1)), 5.0))
            
            # DM 전송 시도
            success = self.send_dm(dm.receiver_id, dm.message)
            dm.mark_attempt(success, None if success else "전송 실패")
            
            if success:
                results['success'] += 1
                logger.info(f"DM 처리 완료: {dm.receiver_id}")
            else:
                if dm.can_retry():
                    # 재시도 가능하면 대기열에 다시 추가
                    self.pending_dms.append(dm)
                    logger.warning(f"DM 재시도 예정: {dm.receiver_id} (시도 {dm.attempts}/{dm.max_attempts})")
                else:
                    results['failed'] += 1
                    logger.error(f"DM 전송 최종 실패: {dm.receiver_id}")
        
        return results
    
    def send_transfer_notification(self, receiver_id: str, giver_name: str, 
                                 giver_subject: str, item_name: str, item_particle: str) -> bool:
        """
        양도 알림 DM 전송
        
        Args:
            receiver_id: 수신자 ID
            giver_name: 양도자 이름
            giver_subject: 양도자 주어 조사 (이/가)
            item_name: 아이템명
            item_particle: 아이템 목적어 조사 (을/를)
            
        Returns:
            bool: 전송 성공 여부
        """
        message = self._format_transfer_message(giver_name, giver_subject, item_name, item_particle)
        return self.send_dm(receiver_id, message)
    
    def queue_transfer_notification(self, receiver_id: str, giver_name: str,
                                  giver_subject: str, item_name: str, item_particle: str,
                                  priority: bool = False) -> bool:
        """
        양도 알림 DM을 대기열에 추가
        
        Args:
            receiver_id: 수신자 ID
            giver_name: 양도자 이름  
            giver_subject: 양도자 주어 조사 (이/가)
            item_name: 아이템명
            item_particle: 아이템 목적어 조사 (을/를)
            priority: 우선순위
            
        Returns:
            bool: 대기열 추가 성공 여부
        """
        message = self._format_transfer_message(giver_name, giver_subject, item_name, item_particle)
        return self.queue_dm(receiver_id, message, priority)
    
    def _format_transfer_message(self, giver_name: str, giver_subject: str, 
                               item_name: str, item_particle: str) -> str:
        """양도 메시지 포맷팅"""
        return f"{giver_name}{giver_subject} 당신에게 {item_name}{item_particle} 양도했습니다."
    
    def _validate_receiver_id(self, receiver_id: str) -> bool:
        """수신자 ID 유효성 검증"""
        if not receiver_id or not receiver_id.strip():
            return False
        
        receiver_id = receiver_id.strip()
        
        # 특수 문자나 공백이 포함된 경우 무효
        if any(char in receiver_id for char in [' ', '\n', '\t', '\r']):
            return False
        
        return True
    
    def _update_stats(self, success: bool):
        """통계 업데이트"""
        self.stats['total_sent'] += 1
        if success:
            self.stats['successful_sent'] += 1
        else:
            self.stats['failed_sent'] += 1
    
    def get_pending_count(self) -> int:
        """대기 중인 DM 개수"""
        return len(self.pending_dms)
    
    def get_stats(self) -> Dict[str, Any]:
        """DM 전송 통계"""
        stats = self.stats.copy()
        stats['pending_dms'] = len(self.pending_dms)
        
        if stats['total_sent'] > 0:
            stats['success_rate'] = (stats['successful_sent'] / stats['total_sent']) * 100
        else:
            stats['success_rate'] = 0
        
        # 상태별 DM 개수
        status_counts = {status.value: 0 for status in DMStatus}
        for dm in self.pending_dms:
            status_counts[dm.status.value] += 1
        stats['status_counts'] = status_counts
        
        return stats
    
    def clear_failed_dms(self) -> int:
        """실패한 DM들을 대기열에서 제거"""
        before_count = len(self.pending_dms)
        self.pending_dms = deque(
            (dm for dm in self.pending_dms if dm.can_retry()),
            maxlen=self.pending_dms.maxlen
        )
        after_count = len(self.pending_dms)
        
        cleared = before_count - after_count
        if cleared > 0:
            logger.info(f"실패한 DM {cleared}개 제거됨")
        
        return cleared
    
    def reset_stats(self) -> None:
        """통계 초기화"""
        self.stats = {
            'total_sent': 0,
            'successful_sent': 0,
            'failed_sent': 0,
            'retry_attempts': 0,
            'queue_overflow': 0
        }
        logger.info("DM 전송 통계 초기화")
    
    def health_check(self) -> Dict[str, Any]:
        """DM 전송기 상태 확인"""
        current_time = time.time()
        
        # 캐시된 결과 반환 (5분 간격)
        if current_time - self._last_health_check < self._health_check_interval:
            return getattr(self, '_cached_health_status', {'status': 'unknown'})
        
        health_status = {
            'status': 'healthy',
            'errors': [],
            'warnings': [],
            'timestamp': current_time
        }
        
        try:
            # 마스토돈 클라이언트 확인
            if not self.mastodon:
                health_status['errors'].append("마스토돈 클라이언트가 없습니다")
                health_status['status'] = 'error'
            
            # 대기 중인 DM 확인
            pending_count = len(self.pending_dms)
            if pending_count > 100:  # 임계값 상향 조정
                health_status['warnings'].append(f"대기 중인 DM이 많습니다: {pending_count}개")
                health_status['status'] = 'warning' if health_status['status'] == 'healthy' else health_status['status']
            
            # 실패율 확인
            if self.stats['total_sent'] > 10:
                failure_rate = (self.stats['failed_sent'] / self.stats['total_sent']) * 100
                if failure_rate > 30:
                    health_status['warnings'].append(f"높은 실패율: {failure_rate:.1f}%")
                    health_status['status'] = 'warning' if health_status['status'] == 'healthy' else health_status['status']
            
            # 대기열 오버플로우 확인
            if self.stats['queue_overflow'] > 0:
                health_status['warnings'].append(f"대기열 오버플로우: {self.stats['queue_overflow']}회")
                health_status['status'] = 'warning' if health_status['status'] == 'healthy' else health_status['status']
            
            # 통계 정보 추가
            health_status['statistics'] = self.get_stats()
            
        except Exception as e:
            health_status['errors'].append(f"상태 확인 중 오류: {str(e)}")
            health_status['status'] = 'error'
        
        # 결과 캐시
        self._cached_health_status = health_status
        self._last_health_check = current_time
        
        return health_status


# 전역 DM 전송기 인스턴스
_global_dm_sender: Optional[DMSender] = None


def initialize_dm_sender(mastodon_client: mastodon.Mastodon, 
                        batch_size: int = 10,
                        retry_delay: float = 1.0,
                        max_queue_size: int = 1000) -> DMSender:
    """
    전역 DM 전송기 초기화
    
    Args:
        mastodon_client: 마스토돈 클라이언트
        batch_size: 배치 처리 크기
        retry_delay: 재시도 간격
        max_queue_size: 최대 대기열 크기
        
    Returns:
        DMSender: 초기화된 DM 전송기
    """
    global _global_dm_sender
    _global_dm_sender = DMSender(
        mastodon_client, 
        batch_size=batch_size,
        retry_delay=retry_delay,
        max_queue_size=max_queue_size
    )
    logger.info("DM 전송기 초기화 완료")
    return _global_dm_sender


def get_dm_sender() -> Optional[DMSender]:
    """전역 DM 전송기 반환"""
    return _global_dm_sender


def send_dm(receiver_id: str, message: str) -> bool:
    """편의 함수: DM 전송"""
    sender = get_dm_sender()
    if sender:
        return sender.send_dm(receiver_id, message)
    else:
        logger.error("DM 전송기가 초기화되지 않았습니다")
        return False


def queue_dm(receiver_id: str, message: str, priority: bool = False) -> bool:
    """편의 함수: DM 대기열 추가"""
    sender = get_dm_sender()
    if sender:
        return sender.queue_dm(receiver_id, message, priority)
    else:
        logger.error("DM 전송기가 초기화되지 않았습니다")
        return False


def process_pending_dms(max_batches: int = 5) -> Dict[str, int]:
    """편의 함수: 대기 중인 DM 처리"""
    sender = get_dm_sender()
    if sender:
        return sender.process_pending_dms(max_batches)
    else:
        logger.error("DM 전송기가 초기화되지 않았습니다")
        return {'processed': 0, 'success': 0, 'failed': 0, 'retries': 0}


def send_transfer_notification(receiver_id: str, giver_name: str, giver_eun_neun: str,
                             item_name: str, item_particle: str) -> bool:
    """편의 함수: 양도 알림 DM 전송"""
    sender = get_dm_sender()
    if sender:
        giver_subject = '이' if giver_eun_neun == '은' else '가'
        return sender.send_transfer_notification(
            receiver_id, giver_name, giver_subject, item_name, item_particle
        )
    else:
        logger.error("DM 전송기가 초기화되지 않았습니다")
        return False


def queue_transfer_notification(receiver_id: str, giver_name: str, giver_eun_neun: str,
                              item_name: str, item_particle: str, priority: bool = False) -> bool:
    """편의 함수: 양도 알림 DM 대기열 추가"""
    sender = get_dm_sender()
    if sender:
        giver_subject = '이' if giver_eun_neun == '은' else '가'
        return sender.queue_transfer_notification(
            receiver_id, giver_name, giver_subject, item_name, item_particle, priority
        )
    else:
        logger.error("DM 전송기가 초기화되지 않았습니다")
        return False


# 테스트 함수
def test_dm_formatting():
    """DM 메시지 포맷팅 테스트"""
    test_cases = [
        ('한참', '은', '반지', '를'),
        ('테스트', '는', '사과', '를'),
        ('울로', '는', '동화책', '을')
    ]
    
    print("=== DM 메시지 포맷팅 테스트 ===")
    for giver_name, eun_neun, item_name, item_particle in test_cases:
        giver_subject = '이' if eun_neun == '은' else '가'
        message = f"{giver_name}{giver_subject} 당신에게 {item_name}{item_particle} 양도했습니다."
        print(f"{giver_name}({eun_neun}) + {item_name}({item_particle}) -> {message}")
    print("=" * 40)


if __name__ == "__main__":
    test_dm_formatting()