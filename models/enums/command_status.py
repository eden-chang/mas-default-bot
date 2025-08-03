"""
Command status enumeration
"""

from enum import Enum


class CommandStatus(Enum):
    """명령어 실행 상태"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    ERROR = "error" 