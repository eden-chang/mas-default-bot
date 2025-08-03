"""
메시지 분할 및 스레드 전송 시스템
긴 메시지를 여러 툿으로 나누어 전송하는 기능을 제공합니다.
"""

import os
import sys
import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple

# 경로 설정 (VM 환경 대응)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

try:
    from utils.logging_config import logger
    from models.command_result import CommandResult, ShopResult, InventoryResult
    from config.settings import config
except ImportError:
    import logging
    logger = logging.getLogger('message_chunking')


class MessageChunker:
    """메시지 분할 클래스"""
    
    def __init__(self, max_length: Optional[int] = None):
        """
        MessageChunker 초기화
        
        Args:
            max_length: 최대 글자 수 (None이면 설정에서 가져옴)
        """
        if max_length is None:
            # 설정에서 최대 길이를 가져와서 -80자 적용
            base_length = getattr(config, 'MESSAGE_MAX_LENGTH', 500)
            self.max_length = max(base_length - 80, 100)  # 최소 100자 보장
        else:
            self.max_length = max_length
    
    def split_message(self, message: str) -> List[str]:
        """
        기본 메시지 분할
        
        Args:
            message: 원본 메시지
            
        Returns:
            List[str]: 분할된 메시지 리스트
        """
        if len(message) <= self.max_length:
            return [message]
        
        chunks = []
        current_chunk = ""
        lines = message.split('\n')
        
        for line in lines:
            # 한 줄이 너무 긴 경우 단어 단위로 분할
            if len(line) > self.max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                word_chunks = self._split_long_line(line)
                chunks.extend(word_chunks[:-1])  # 마지막 제외하고 추가
                current_chunk = word_chunks[-1] if word_chunks else ""
            else:
                # 현재 청크에 추가했을 때 길이 확인
                test_chunk = current_chunk + line + "\n"
                if len(test_chunk) <= self.max_length:
                    current_chunk = test_chunk
                else:
                    # 현재 청크 저장하고 새로 시작
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = line + "\n"
        
        # 마지막 청크 추가
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return self._add_continuation_markers(chunks)
    
    def split_shop_items(self, items: List[Dict[str, Any]], currency_unit: str) -> List[str]:
        """
        상점 아이템 목록을 항목 단위로 분할
        
        Args:
            items: 아이템 리스트
            currency_unit: 화폐 단위
            
        Returns:
            List[str]: 분할된 메시지 리스트
        """
        if not items:
            return ["현재 상점에 판매중인 아이템이 없습니다."]
        
        header = "상점에서 구매 가능한 목록입니다.\n\n"
        chunks = []
        current_chunk = header
        
        for i, item in enumerate(items):
            item_line = f"{item['name']} ({item['price']}{currency_unit}) : {item['description']}\n"
            
            # 항목을 추가했을 때 길이 확인
            test_chunk = current_chunk + item_line
            
            if len(test_chunk) > self.max_length:
                # 현재 청크를 저장하고 새 청크 시작
                if current_chunk != header:  # 헤더만 있는 게 아니라면
                    chunks.append(current_chunk.strip())
                
                # 새 청크는 헤더 없이 시작 (연속임을 표시)
                current_chunk = item_line
            else:
                current_chunk = test_chunk
        
        # 마지막 청크 추가
        if current_chunk and current_chunk != header:
            chunks.append(current_chunk.strip())
        
        return self._add_continuation_markers(chunks)
    
    def split_inventory_items(self, inventory: Dict[str, int], user_name: str, suffix: str) -> List[str]:
        """
        인벤토리 목록을 항목 단위로 분할
        
        Args:
            inventory: 인벤토리 딕셔너리
            user_name: 사용자 이름
            suffix: 은/는 조사
            
        Returns:
            List[str]: 분할된 메시지 리스트
        """
        if not inventory:
            return [f"{user_name}{suffix} 현재 가지고 있는 소지품이 없습니다."]
        
        header = f"{user_name}의 현재 소지품은 다음과 같습니다.\n\n"
        chunks = []
        current_chunk = header
        
        for item_name, count in inventory.items():
            item_line = f"- {item_name} {count}개\n"
            
            # 항목을 추가했을 때 길이 확인
            test_chunk = current_chunk + item_line
            
            if len(test_chunk) > self.max_length:
                # 현재 청크를 저장하고 새 청크 시작
                if current_chunk != header:  # 헤더만 있는 게 아니라면
                    chunks.append(current_chunk.strip())
                
                # 새 청크는 간단한 헤더로 시작
                current_chunk = f"(계속)\n\n" + item_line
            else:
                current_chunk = test_chunk
        
        # 마지막 청크 추가
        if current_chunk and current_chunk != header:
            chunks.append(current_chunk.strip())
        
        return chunks  # 인벤토리는 이미 @멘션이 있어서 continuation marker 불필요
    
    def _split_long_line(self, line: str) -> List[str]:
        """긴 줄을 단어 단위로 분할"""
        words = line.split(' ')
        chunks = []
        current_chunk = ""
        
        for word in words:
            test_chunk = current_chunk + word + " "
            if len(test_chunk) <= self.max_length:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = word + " "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _add_continuation_markers(self, chunks: List[str]) -> List[str]:
        """연속 표시 마커 추가"""
        if len(chunks) <= 1:
            return chunks
        
        marked_chunks = []
        
        for i, chunk in enumerate(chunks):
            if i == 0:
                # 첫 번째 청크: 계속됨 표시
                marked_chunks.append(chunk + "\n\n(계속...)")
            elif i == len(chunks) - 1:
                # 마지막 청크: 계속 표시
                marked_chunks.append("(계속)\n\n" + chunk)
            else:
                # 중간 청크: 양쪽 표시
                marked_chunks.append("(계속)\n\n" + chunk + "\n\n(계속...)")
        
        return marked_chunks


class ThreadedMessageSender:
    """스레드 메시지 전송 클래스"""
    
    def __init__(self, mastodon_client, delay_between_messages: float = 0.5):
        """
        ThreadedMessageSender 초기화
        
        Args:
            mastodon_client: 마스토돈 클라이언트
            delay_between_messages: 메시지 간 대기 시간 (초)
        """
        self.mastodon = mastodon_client
        self.delay = delay_between_messages
        self.chunker = MessageChunker()  # 설정에서 자동으로 최대 길이 가져옴
    
    def send_reply(self, original_status_id: str, message: str) -> List[Dict]:
        """
        단일 또는 스레드 답장 전송
        
        Args:
            original_status_id: 원본 툿 ID
            message: 전송할 메시지
            
        Returns:
            List[Dict]: 전송된 툿들의 정보
        """
        if len(message) <= self.chunker.max_length:
            # 짧은 메시지는 단일 답장
            return self._send_single_reply(original_status_id, message)
        else:
            # 긴 메시지는 스레드로 전송
            return self._send_threaded_reply(original_status_id, message)
    
    def send_command_result(self, original_status_id: str, result: CommandResult) -> List[Dict]:
        """
        명령어 결과를 적절한 방식으로 전송
        
        Args:
            original_status_id: 원본 툿 ID
            result: 명령어 결과
            
        Returns:
            List[Dict]: 전송된 툿들의 정보
        """
        # 결과 타입별 특별 처리
        if hasattr(result, 'result_data'):
            if isinstance(result.result_data, ShopResult):
                return self._send_shop_result(original_status_id, result.result_data)
            elif isinstance(result.result_data, InventoryResult):
                return self._send_inventory_result(original_status_id, result.result_data)
        
        # 기본 메시지 전송
        return self.send_reply(original_status_id, result.message)
    
    def _send_single_reply(self, original_status_id: str, message: str) -> List[Dict]:
        """단일 답장 전송"""
        try:
            status = self.mastodon.status_reply(
                to_status=original_status_id,
                status=message
            )
            logger.info(f"단일 답장 전송 완료: {len(message)}자")
            return [status]
        
        except Exception as e:
            logger.error(f"단일 답장 전송 실패: {e}")
            return []
    
    def _send_threaded_reply(self, original_status_id: str, message: str) -> List[Dict]:
        """스레드 답장 전송"""
        chunks = self.chunker.split_message(message)
        return self._send_chunks(original_status_id, chunks)
    
    def _send_shop_result(self, original_status_id: str, shop_result: ShopResult) -> List[Dict]:
        """상점 결과 전송"""
        chunks = self.chunker.split_shop_items(shop_result.items, shop_result.currency_unit)
        logger.info(f"상점 목록을 {len(chunks)}개 청크로 분할")
        return self._send_chunks(original_status_id, chunks)
    
    def _send_inventory_result(self, original_status_id: str, inventory_result: InventoryResult) -> List[Dict]:
        """인벤토리 결과 전송"""
        chunks = self.chunker.split_inventory_items(
            inventory_result.inventory, 
            inventory_result.user_name, 
            inventory_result.suffix
        )
        logger.info(f"인벤토리를 {len(chunks)}개 청크로 분할")
        return self._send_chunks(original_status_id, chunks)
    
    def _send_chunks(self, original_status_id: str, chunks: List[str]) -> List[Dict]:
        """청크 리스트를 순차적으로 전송"""
        sent_statuses = []
        reply_to_id = original_status_id
        
        for i, chunk in enumerate(chunks):
            try:
                logger.debug(f"청크 {i+1}/{len(chunks)} 전송 중... ({len(chunk)}자)")
                
                status = self.mastodon.status_reply(
                    to_status=reply_to_id,
                    status=chunk
                )
                
                sent_statuses.append(status)
                reply_to_id = status['id']  # 다음 답장은 방금 보낸 툿에 연결
                
                # API 제한 고려하여 대기 (마지막 제외)
                if i < len(chunks) - 1:
                    time.sleep(self.delay)
                
            except Exception as e:
                logger.error(f"청크 {i+1} 전송 실패: {e}")
                break
        
        logger.info(f"스레드 답장 완료: {len(sent_statuses)}/{len(chunks)}개 툿 전송")
        return sent_statuses


# 전역 인스턴스 관리
_global_message_sender: Optional[ThreadedMessageSender] = None


def initialize_message_sender(mastodon_client) -> ThreadedMessageSender:
    """
    메시지 전송기 초기화
    
    Args:
        mastodon_client: 마스토돈 클라이언트
        
    Returns:
        ThreadedMessageSender: 초기화된 전송기
    """
    global _global_message_sender
    _global_message_sender = ThreadedMessageSender(mastodon_client)
    logger.info("스레드 메시지 전송기 초기화 완료")
    return _global_message_sender


def get_message_sender() -> Optional[ThreadedMessageSender]:
    """전역 메시지 전송기 반환"""
    return _global_message_sender


def send_bot_reply(original_status_id: str, message: str) -> List[Dict]:
    """
    편의 함수: 봇 답장 전송
    
    Args:
        original_status_id: 원본 툿 ID
        message: 전송할 메시지
        
    Returns:
        List[Dict]: 전송된 툿들의 정보
    """
    sender = get_message_sender()
    if sender:
        return sender.send_reply(original_status_id, message)
    else:
        logger.error("메시지 전송기가 초기화되지 않았습니다.")
        return []


def send_command_result(original_status_id: str, result: CommandResult) -> List[Dict]:
    """
    편의 함수: 명령어 결과 전송
    
    Args:
        original_status_id: 원본 툿 ID
        result: 명령어 결과
        
    Returns:
        List[Dict]: 전송된 툿들의 정보
    """
    sender = get_message_sender()
    if sender:
        return sender.send_command_result(original_status_id, result)
    else:
        logger.error("메시지 전송기가 초기화되지 않았습니다.")
        return []


# 테스트 함수
def test_message_chunking():
    """메시지 분할 테스트"""
    # 설정에서 가져온 길이로 테스트
    chunker = MessageChunker()
    print(f"현재 설정된 최대 길이: {chunker.max_length}자")
    
    # 상점 아이템 테스트
    test_items = [
        {'name': '반지', 'price': 3, 'description': '노란색 보석이 박힌 은색 반지다.'},
        {'name': '동화책', 'price': 1, 'description': '아이들이 읽을 법한 귀여운 동화책이다.'},
        {'name': '마법의 지팡이', 'price': 50, 'description': '고대의 마법이 깃든 신비로운 지팡이로, 사용자의 마법력을 증폭시켜준다.'},
        {'name': '치유 물약', 'price': 5, 'description': '상처를 빠르게 치유해주는 마법의 물약이다.'}
    ]
    
    chunks = chunker.split_shop_items(test_items, '갈레온')
    
    print("=== 상점 아이템 분할 테스트 ===")
    for i, chunk in enumerate(chunks):
        print(f"청크 {i+1} ({len(chunk)}자):")
        print(chunk)
        print("-" * 50)


if __name__ == "__main__":
    test_message_chunking()


def chunk_message(message: str, max_length: Optional[int] = None) -> List[str]:
    """
    메시지 청킹 (백워드 호환성)
    
    Args:
        message: 원본 메시지
        max_length: 최대 길이 (None이면 기본값 사용)
        
    Returns:
        List[str]: 분할된 메시지 리스트
    """
    chunker = MessageChunker(max_length)
    return chunker.split_message(message)


def split_long_message(message: str, max_length: Optional[int] = None) -> List[str]:
    """
    긴 메시지 분할 (백워드 호환성)
    
    Args:
        message: 원본 메시지
        max_length: 최대 길이 (None이면 기본값 사용)
        
    Returns:
        List[str]: 분할된 메시지 리스트
    """
    return chunk_message(message, max_length)