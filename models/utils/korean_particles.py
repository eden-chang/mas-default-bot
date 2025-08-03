"""
Korean particle handling utilities
"""

def detect_korean_particle(word: str, particle_type: str) -> str:
    """
    한글 조사 자동 처리
    
    Args:
        word: 조사가 붙을 단어
        particle_type: 조사 타입 ('topic', 'subject', 'object', 'eul_reul', 'i_ga', 'eun_neun', 'wa_gwa')
        
    Returns:
        str: 적절한 조사
    """
    if not word:
        return ""
    
    last_char = word[-1]
    
    # 한글 범위 확인
    if '가' <= last_char <= '힣':
        code = ord(last_char) - ord('가')
        has_final = (code % 28) != 0
        
        if particle_type in ['object', 'eul_reul']:
            return '을' if has_final else '를'
        elif particle_type in ['subject', 'i_ga']:
            return '이' if has_final else '가'
        elif particle_type in ['topic', 'eun_neun']:
            return '은' if has_final else '는'
        elif particle_type in ['with', 'wa_gwa']:
            return '과' if has_final else '와'
    else:
        # 한글이 아닌 경우 기본값
        if particle_type in ['object', 'eul_reul']:
            return '을'
        elif particle_type in ['subject', 'i_ga']:
            return '이'
        elif particle_type in ['topic', 'eun_neun']:
            return '은'
        elif particle_type in ['with', 'wa_gwa']:
            return '과'
    
    return ""


def format_with_particle(word: str, particle_type: str) -> str:
    """
    단어와 조사를 결합
    
    Args:
        word: 단어
        particle_type: 조사 타입
        
    Returns:
        str: 조사가 붙은 단어
    """
    particle = detect_korean_particle(word, particle_type)
    return f"{word}{particle}" 