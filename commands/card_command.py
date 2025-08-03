"""
카드 뽑기 명령어 구현 - 최적화된 버전
트럼프 카드 뽑기 기능을 제공하는 명령어 클래스입니다.
새로운 BaseCommand 구조와 최적화된 에러 핸들링을 적용합니다.
"""

import os
import sys
import random
import re
from typing import List, Tuple, Any, Optional, Dict

# 경로 설정 (VM 환경 대응)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

try:
    from config.settings import config
    from utils.logging_config import logger, bot_logger
    from utils.error_handling.exceptions import CardError
    from utils.error_handling.handler import ErrorHandler, get_error_handler
    from commands.base_command import BaseCommand
    from models.user import User
    from models.command_result import CommandType, CommandStatus, CardResult, create_card_result
except ImportError:
    # VM 환경에서 임포트 실패 시 폴백
    import logging
    logger = logging.getLogger('card_command')
    
    # 기본 클래스들 정의
    class CardError(Exception):
        pass
    
    class BaseCommand:
        pass
    
    class User:
        def __init__(self, id: str, name: str = ""):
            self.id = id
            self.name = name
        
        def get_display_name(self):
            return self.name or self.id
    
    class CommandType:
        CARD = "card"
    
    class CommandStatus:
        SUCCESS = "success"
        ERROR = "error"
    
    class CardResult:
        def __init__(self, cards: list, **kwargs):
            self.cards = cards
            for key, value in kwargs.items():
                setattr(self, key, value)


class CardCommand(BaseCommand):
    """
    최적화된 카드 뽑기 명령어 클래스
    
    지원하는 형식:
    - [카드뽑기/5장] : 트럼프 카드 5장 뽑기
    - [카드뽑기/1] : 트럼프 카드 1장 뽑기 (장 생략 가능)
    - [카드/10장] : 카드뽑기 줄임말
    """
    
    # 트럼프 카드 덱 구성
    SUITS = ['♠', '♥', '♦', '♣']  # 스페이드, 하트, 다이아몬드, 클럽
    RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    
    # 무늬별 한글 이름
    SUIT_NAMES = {
        '♠': '스페이드',
        '♥': '하트', 
        '♦': '다이아몬드',
        '♣': '클럽'
    }
    
    # 랭크별 한글 이름
    RANK_NAMES = {
        'A': '에이스',
        'J': '잭',
        'Q': '퀸', 
        'K': '킹'
    }
    
    def _get_command_type(self) -> CommandType:
        """명령어 타입 반환"""
        return CommandType.CARD
    
    def _get_command_name(self) -> str:
        """명령어 이름 반환"""
        return "카드뽑기"
    
    def _execute_command(self, user: User, keywords: List[str]) -> Tuple[str, CardResult]:
        """
        카드 뽑기 명령어 실행
        
        Args:
            user: 사용자 객체
            keywords: 키워드 리스트 ([카드뽑기, 5장] 또는 [카드, 5])
            
        Returns:
            Tuple[str, CardResult]: (결과 메시지, 카드 결과 객체)
            
        Raises:
            CardError: 카드 개수 오류 또는 형식 오류
        """
        # 키워드에서 카드 개수 추출
        card_count = self._extract_card_count(keywords)
        
        # 카드 개수 검증
        self._validate_card_count(card_count)
        
        # 카드 덱 생성 및 섞기
        deck = self._create_deck()
        self._shuffle_deck(deck)
        
        # 카드 뽑기
        drawn_cards = self._draw_cards(deck, card_count)
        
        # 결과 객체 생성
        card_result = create_card_result(drawn_cards)
        
        # 결과 메시지 생성
        message = self._format_result_message(card_result)
        
        return message, card_result
    
    def _extract_card_count(self, keywords: List[str]) -> int:
        """
        키워드에서 카드 개수 추출
        
        Args:
            keywords: 키워드 리스트
            
        Returns:
            int: 카드 개수
            
        Raises:
            CardError: 개수 추출 실패 또는 형식 오류
        """
        if not keywords:
            raise CardError("카드 개수를 입력해주세요.")
        
        # 첫 번째 키워드가 명령어인지 확인
        first_keyword = keywords[0].lower()
        if first_keyword in ['카드뽑기', '카드']:
            if len(keywords) < 2:
                raise CardError("카드 개수를 입력해주세요.")
            count_str = keywords[1]
        else:
            # 첫 번째 키워드가 바로 개수인 경우 (예: [5장])
            count_str = keywords[0]
        
        # 개수 문자열 파싱
        return self._parse_card_count(count_str)
    
    def _parse_card_count(self, count_str: str) -> int:
        """
        카드 개수 문자열 파싱
        
        Args:
            count_str: 개수 문자열 (예: "5장", "10", "3")
            
        Returns:
            int: 파싱된 개수
            
        Raises:
            CardError: 파싱 실패
        """
        if not count_str:
            raise CardError("카드 개수를 입력해주세요.")
        
        # 공백 제거
        count_str = count_str.strip()
        
        # "장" 제거
        if count_str.endswith('장'):
            count_str = count_str[:-1]
        
        # 숫자 추출 (한글 숫자도 지원)
        number = self._extract_number(count_str)
        
        if number is None:
            raise CardError(f"'{count_str}'은(는) 올바른 카드 개수가 아닙니다.")
        
        return number
    
    def _extract_number(self, text: str) -> Optional[int]:
        """
        텍스트에서 숫자 추출 (한글 숫자 포함)
        
        Args:
            text: 숫자를 포함한 텍스트
            
        Returns:
            Optional[int]: 추출된 숫자 또는 None
        """
        # 먼저 아라비아 숫자 시도
        digit_match = re.search(r'\d+', text)
        if digit_match:
            try:
                return int(digit_match.group())
            except ValueError:
                pass
        
        # 한글 숫자 매핑
        korean_numbers = {
            '영': 0, '공': 0, '하나': 1, '일': 1, '둘': 2, '이': 2, 
            '셋': 3, '삼': 3, '넷': 4, '사': 4, '다섯': 5, '오': 5,
            '여섯': 6, '육': 6, '일곱': 7, '칠': 7, '여덟': 8, '팔': 8,
            '아홉': 9, '구': 9, '열': 10, '십': 10
        }
        
        # 한글 숫자 확인
        text_lower = text.lower()
        for korean, number in korean_numbers.items():
            if korean in text_lower:
                return number
        
        # 직접 숫자 변환 시도
        try:
            return int(text)
        except ValueError:
            return None
    
    def _validate_card_count(self, count: int) -> None:
        """
        카드 개수 유효성 검증
        
        Args:
            count: 카드 개수
            
        Raises:
            CardError: 개수가 범위를 벗어남
        """
        if count < 1:
            raise CardError("카드는 최소 1장부터 뽑을 수 있습니다.")
        
        if count > config.MAX_CARD_COUNT:
            raise CardError(f"카드는 최대 {config.MAX_CARD_COUNT}장까지만 뽑을 수 있습니다.")
        
        logger.debug(f"카드 개수 검증 완료: {count}장")
    
    def _create_deck(self) -> List[str]:
        """
        트럼프 카드 덱 생성
        
        Returns:
            List[str]: 52장의 카드 리스트
        """
        deck = []
        for suit in self.SUITS:
            for rank in self.RANKS:
                card = f"{suit}{rank}"
                deck.append(card)
        
        logger.debug(f"카드 덱 생성: {len(deck)}장")
        return deck
    
    def _shuffle_deck(self, deck: List[str]) -> None:
        """
        카드 덱 섞기 (인플레이스)
        
        Args:
            deck: 섞을 카드 덱
        """
        random.shuffle(deck)
        logger.debug("카드 덱 섞기 완료")
    
    def _draw_cards(self, deck: List[str], count: int) -> List[str]:
        """
        카드 뽑기
        
        Args:
            deck: 카드 덱
            count: 뽑을 카드 개수
            
        Returns:
            List[str]: 뽑힌 카드들
        """
        drawn_cards = deck[:count]
        logger.debug(f"카드 뽑기: {count}장 - {drawn_cards}")
        return drawn_cards
    
    def _format_result_message(self, card_result: CardResult) -> str:
        """
        결과 메시지 포맷팅
        
        Args:
            card_result: 카드 결과
            
        Returns:
            str: 포맷된 결과 메시지
        """
        return card_result.get_result_text()
    
    def get_help_text(self) -> str:
        """도움말 텍스트 반환"""
        return "[카드뽑기/N장] - 트럼프 카드를 N장 뽑습니다."
    
    def get_extended_help(self) -> str:
        """확장 도움말 반환"""
        return (
            f"{self.get_help_text()}\n\n"
            f"📋 사용 예시:\n"
            f"[카드뽑기/5장] - 트럼프 카드 5장 뽑기\n"
            f"[카드뽑기/1] - 트럼프 카드 1장 뽑기\n"
            f"[카드/10장] - 줄임말 사용 가능\n"
            f"[카드뽑기/열장] - 한글 숫자도 지원\n\n"
            f"🃏 카드 구성:\n"
            f"• 무늬: {', '.join(self.SUITS)} (스페이드, 하트, 다이아몬드, 클럽)\n"
            f"• 숫자: {', '.join(self.RANKS)} (에이스, 2~10, 잭, 퀸, 킹)\n"
            f"• 총 52장\n\n"
            f"⚙️ 제한사항:\n"
            f"• 최소 카드 개수: 1장\n"
            f"• 최대 카드 개수: {config.MAX_CARD_COUNT}장\n"
            f"• 중복 없이 뽑기 (한 덱에서)"
        )
    
    def get_card_statistics(self, card_result: CardResult) -> Dict[str, Any]:
        """
        뽑힌 카드의 통계 분석
        
        Args:
            card_result: 카드 결과
            
        Returns:
            Dict: 카드 통계
        """
        if not card_result.cards:
            return {}
        
        suits_count = card_result.get_suits_summary()
        ranks_count = card_result.get_ranks_summary()
        
        # 추가 분석
        stats = {
            'total_cards': len(card_result.cards),
            'suits_distribution': suits_count,
            'ranks_distribution': ranks_count,
            'most_common_suit': max(suits_count.items(), key=lambda x: x[1])[0] if suits_count else None,
            'unique_suits': len([suit for suit, count in suits_count.items() if count > 0]),
            'unique_ranks': len(ranks_count),
        }
        
        # 특별한 조합 확인
        special_combinations = self._check_special_combinations(card_result.cards)
        stats['special_combinations'] = special_combinations
        
        return stats
    
    def _check_special_combinations(self, cards: List[str]) -> List[str]:
        """
        특별한 카드 조합 확인 (포커 등)
        
        Args:
            cards: 뽑힌 카드들
            
        Returns:
            List[str]: 발견된 특별한 조합들
        """
        combinations = []
        
        if len(cards) < 2:
            return combinations
        
        # 카드 파싱
        suits = [card[0] for card in cards]
        ranks = [card[1:] for card in cards]
        
        # 같은 무늬 확인
        suit_counts = {}
        for suit in suits:
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
        
        max_same_suit = max(suit_counts.values()) if suit_counts else 0
        if max_same_suit >= 5:
            combinations.append("플러시 가능")
        elif max_same_suit >= 3:
            combinations.append(f"같은 무늬 {max_same_suit}장")
        
        # 같은 숫자 확인
        rank_counts = {}
        for rank in ranks:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
        
        max_same_rank = max(rank_counts.values()) if rank_counts else 0
        if max_same_rank >= 4:
            combinations.append("포카드")
        elif max_same_rank >= 3:
            combinations.append("트리플")
        elif max_same_rank >= 2:
            pair_count = sum(1 for count in rank_counts.values() if count >= 2)
            if pair_count >= 2:
                combinations.append("투페어")
            else:
                combinations.append("원페어")
        
        # 연속 숫자 확인 (간단한 버전)
        if len(cards) >= 5:
            rank_values = []
            for rank in ranks:
                if rank == 'A':
                    rank_values.append(1)  # 에이스는 1 또는 14
                elif rank == 'J':
                    rank_values.append(11)
                elif rank == 'Q':
                    rank_values.append(12)
                elif rank == 'K':
                    rank_values.append(13)
                else:
                    rank_values.append(int(rank))
            
            rank_values.sort()
            consecutive = 1
            max_consecutive = 1
            
            for i in range(1, len(rank_values)):
                if rank_values[i] == rank_values[i-1] + 1:
                    consecutive += 1
                    max_consecutive = max(max_consecutive, consecutive)
                else:
                    consecutive = 1
            
            if max_consecutive >= 5:
                combinations.append("스트레이트 가능")
            elif max_consecutive >= 3:
                combinations.append(f"연속 {max_consecutive}장")
        
        return combinations
    
    def validate_card_count_format(self, count_str: str) -> Tuple[bool, Optional[str]]:
        """
        카드 개수 형식 검증 (미리 검증용)
        
        Args:
            count_str: 검증할 개수 문자열
            
        Returns:
            Tuple[bool, Optional[str]]: (유효성, 오류 메시지)
        """
        try:
            count = self._parse_card_count(count_str)
            self._validate_card_count(count)
            return True, None
        except CardError as e:
            return False, str(e)
        except Exception as e:
            return False, f"형식 검증 오류: {str(e)}"
    
    def get_random_example(self) -> str:
        """랜덤한 카드뽑기 예시 반환"""
        examples = [
            "1장", "3장", "5장", "7장", "10장",
            "1", "3", "5", "하나", "다섯"
        ]
        return random.choice(examples)
    
    def simulate_card_drawing(self, count: int, iterations: int = 1000) -> Dict[str, Any]:
        """
        카드 뽑기 시뮬레이션 (통계용)
        
        Args:
            count: 뽑을 카드 개수
            iterations: 시뮬레이션 횟수
            
        Returns:
            Dict: 시뮬레이션 결과 통계
        """
        if iterations > 1000:  # 과도한 시뮬레이션 방지
            iterations = 1000
        
        try:
            self._validate_card_count(count)
            
            suit_totals = {suit: 0 for suit in self.SUITS}
            rank_totals = {rank: 0 for rank in self.RANKS}
            special_combinations_count = {}
            
            for _ in range(iterations):
                deck = self._create_deck()
                self._shuffle_deck(deck)
                cards = self._draw_cards(deck, count)
                
                # 무늬별 카운트
                for card in cards:
                    suit = card[0]
                    rank = card[1:]
                    suit_totals[suit] += 1
                    rank_totals[rank] += 1
                
                # 특별한 조합 카운트
                combinations = self._check_special_combinations(cards)
                for combo in combinations:
                    special_combinations_count[combo] = special_combinations_count.get(combo, 0) + 1
            
            # 확률 계산
            total_cards_drawn = count * iterations
            suit_probabilities = {suit: (count / total_cards_drawn) * 100 for suit, count in suit_totals.items()}
            rank_probabilities = {rank: (count / total_cards_drawn) * 100 for rank, count in rank_totals.items()}
            
            return {
                'card_count': count,
                'iterations': iterations,
                'total_cards_drawn': total_cards_drawn,
                'suit_distribution': suit_totals,
                'rank_distribution': rank_totals,
                'suit_probabilities': suit_probabilities,
                'rank_probabilities': rank_probabilities,
                'special_combinations': special_combinations_count,
                'most_drawn_suit': max(suit_totals.items(), key=lambda x: x[1])[0],
                'most_drawn_rank': max(rank_totals.items(), key=lambda x: x[1])[0]
            }
            
        except Exception as e:
            return {'error': str(e)}


# 카드 관련 유틸리티 함수들
def is_card_command(keyword: str) -> bool:
    """
    키워드가 카드 명령어인지 확인
    
    Args:
        keyword: 확인할 키워드
        
    Returns:
        bool: 카드 명령어 여부
    """
    if not keyword:
        return False
    
    keyword = keyword.lower().strip()
    return keyword in ['카드뽑기', '카드']


def parse_card_count_from_text(text: str) -> Optional[int]:
    """
    텍스트에서 카드 개수 추출
    
    Args:
        text: 분석할 텍스트
        
    Returns:
        Optional[int]: 추출된 개수 또는 None
    """
    try:
        card_command = CardCommand()
        return card_command._parse_card_count(text)
    except:
        return None


def validate_card_count(count: int) -> Tuple[bool, str]:
    """
    카드 개수 유효성 검사 (독립 함수)
    
    Args:
        count: 검증할 개수
        
    Returns:
        Tuple[bool, str]: (유효성, 메시지)
    """
    try:
        card_command = CardCommand()
        card_command._validate_card_count(count)
        return True, "유효한 카드 개수입니다."
    except CardError as e:
        return False, str(e)
    except Exception as e:
        return False, f"검증 오류: {str(e)}"


def get_card_info(card: str) -> Dict[str, str]:
    """
    카드 정보 반환
    
    Args:
        card: 카드 문자열 (예: "♠A", "♥10")
        
    Returns:
        Dict: 카드 정보
    """
    if len(card) < 2:
        return {}
    
    suit = card[0]
    rank = card[1:]
    
    suit_name = CardCommand.SUIT_NAMES.get(suit, suit)
    rank_name = CardCommand.RANK_NAMES.get(rank, rank)
    
    return {
        'card': card,
        'suit': suit,
        'rank': rank,
        'suit_name': suit_name,
        'rank_name': rank_name,
        'full_name': f"{suit_name} {rank_name}"
    }


def format_cards_korean(cards: List[str]) -> str:
    """
    카드를 한글로 포맷팅
    
    Args:
        cards: 카드 리스트
        
    Returns:
        str: 한글 포맷된 카드 문자열
    """
    korean_cards = []
    for card in cards:
        info = get_card_info(card)
        if info:
            korean_cards.append(info['full_name'])
        else:
            korean_cards.append(card)
    
    return ', '.join(korean_cards)


# 카드 명령어 인스턴스 생성 함수
def create_card_command(sheets_manager=None) -> CardCommand:
    """
    카드 명령어 인스턴스 생성
    
    Args:
        sheets_manager: Google Sheets 관리자
        
    Returns:
        CardCommand: 카드 명령어 인스턴스
    """
    return CardCommand(sheets_manager)