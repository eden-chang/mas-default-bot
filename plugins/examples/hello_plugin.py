"""
Hello 플러그인 예제
플러그인 시스템 테스트용
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from plugins.base.plugin_base import PluginBase, PluginMetadata


# 플러그인 메타데이터
PLUGIN_METADATA = PluginMetadata(
    name="HelloPlugin",
    version="1.0.0",
    description="간단한 인사 플러그인",
    author="Plugin System",
    dependencies=[],
    permissions=[]
)


class HelloPlugin(PluginBase):
    """Hello 플러그인"""
    
    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        self.message_count = 0
    
    def _load_implementation(self):
        """플러그인 로드 구현"""
        self.logger.info("Hello 플러그인 로드 중...")
        # 여기서 필요한 리소스 초기화
        self.message_count = 0
    
    def _enable_implementation(self):
        """플러그인 활성화 구현"""
        self.logger.info("Hello 플러그인 활성화 중...")
        # 여기서 명령어 등록 등 수행
        self.logger.info("Hello 플러그인이 활성화되었습니다!")
    
    def _disable_implementation(self):
        """플러그인 비활성화 구현"""
        self.logger.info("Hello 플러그인 비활성화 중...")
        # 여기서 명령어 등록 해제 등 수행
        self.logger.info("Hello 플러그인이 비활성화되었습니다.")
    
    def _unload_implementation(self):
        """플러그인 언로드 구현"""
        self.logger.info("Hello 플러그인 언로드 중...")
        # 여기서 리소스 정리
        self.message_count = 0
    
    def say_hello(self, name: str = "World") -> str:
        """인사 메시지 생성"""
        self.message_count += 1
        return f"Hello, {name}! (메시지 #{self.message_count})"
    
    def get_stats(self) -> dict:
        """플러그인 통계 반환"""
        return {
            "message_count": self.message_count,
            "enabled": self.is_enabled(),
            "loaded": self.is_loaded()
        } 