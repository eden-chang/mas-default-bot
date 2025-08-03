"""
플러그인 시스템 테스트 스크립트
1단계 구현 검증용
"""

import sys
import os
import logging

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plugins.base.plugin_manager import PluginManager
from models.base.registry import result_registry


def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_plugin_manager():
    """플러그인 관리자 테스트"""
    print("=== 플러그인 관리자 테스트 ===")
    
    # 플러그인 관리자 생성
    manager = PluginManager()
    
    # 플러그인 디렉토리 추가
    plugin_dir = os.path.join(os.path.dirname(__file__), "plugins", "examples")
    manager.add_plugin_directory(plugin_dir)
    
    print(f"플러그인 디렉토리 추가: {plugin_dir}")
    
    # 플러그인 발견
    discovered = manager.discover_plugins()
    print(f"발견된 플러그인: {discovered}")
    
    # 플러그인 로드
    results = manager.load_all_plugins()
    print(f"플러그인 로드 결과: {results}")
    
    # 플러그인 상태 확인
    status = manager.get_all_plugin_status()
    print(f"플러그인 상태: {status}")
    
    # 플러그인 활성화
    for plugin_name in manager.get_all_plugins():
        success = manager.enable_plugin(plugin_name)
        print(f"플러그인 활성화 {plugin_name}: {'성공' if success else '실패'}")
    
    # 활성화된 플러그인 확인
    enabled_plugins = manager.get_enabled_plugins()
    print(f"활성화된 플러그인: {list(enabled_plugins.keys())}")
    
    # 플러그인 기능 테스트
    hello_plugin = manager.get_plugin("HelloPlugin")
    if hello_plugin and hello_plugin.is_enabled():
        message = hello_plugin.say_hello("테스트")
        print(f"플러그인 메시지: {message}")
        
        stats = hello_plugin.get_stats()
        print(f"플러그인 통계: {stats}")
    
    return manager


def test_registry_integration():
    """레지스트리 통합 테스트"""
    print("\n=== 레지스트리 통합 테스트 ===")
    
    # 기존 등록된 타입 확인
    registered_types = result_registry.list_registered_types()
    print(f"기존 등록된 타입: {registered_types}")
    
    # 플러그인 결과 등록 테스트
    from models.base.base_result import BaseResult
    
    class TestPluginResult(BaseResult):
        def __init__(self, message: str):
            super().__init__()
            self.message = message
        
        def get_result_text(self) -> str:
            return f"플러그인 결과: {self.message}"
    
    # 플러그인 결과 등록
    result_registry.register_plugin_result("test_plugin", TestPluginResult)
    
    # 등록 확인
    plugin_results = result_registry.get_plugin_results()
    print(f"플러그인 결과: {list(plugin_results.keys())}")
    
    # 결과 생성 테스트
    result = result_registry.create_result("test_plugin", message="테스트 메시지")
    if result:
        print(f"생성된 결과: {result.get_result_text()}")
    
    # 플러그인 결과 등록 해제
    result_registry.unregister_plugin_result("test_plugin")
    print("플러그인 결과 등록 해제 완료")


def test_event_callbacks():
    """이벤트 콜백 테스트"""
    print("\n=== 이벤트 콜백 테스트 ===")
    
    def on_plugin_loaded(plugin):
        print(f"이벤트: 플러그인 로드됨 - {plugin.get_name()}")
    
    def on_plugin_enabled(plugin):
        print(f"이벤트: 플러그인 활성화됨 - {plugin.get_name()}")
    
    def on_plugin_disabled(plugin):
        print(f"이벤트: 플러그인 비활성화됨 - {plugin.get_name()}")
    
    def on_plugin_unloaded(plugin):
        print(f"이벤트: 플러그인 언로드됨 - {plugin.get_name()}")
    
    # 플러그인 관리자 생성 및 이벤트 콜백 설정
    manager = PluginManager()
    manager.set_event_callbacks(
        on_loaded=on_plugin_loaded,
        on_enabled=on_plugin_enabled,
        on_disabled=on_plugin_disabled,
        on_unloaded=on_plugin_unloaded
    )
    
    # 플러그인 디렉토리 추가 및 로드
    plugin_dir = os.path.join(os.path.dirname(__file__), "plugins", "examples")
    manager.add_plugin_directory(plugin_dir)
    
    # 플러그인 로드 및 활성화
    manager.load_all_plugins()
    for plugin_name in manager.get_all_plugins():
        manager.enable_plugin(plugin_name)
    
    # 플러그인 비활성화 및 언로드
    for plugin_name in list(manager.get_all_plugins().keys()):
        manager.disable_plugin(plugin_name)
        manager.unload_plugin(plugin_name)


def main():
    """메인 테스트 함수"""
    print("플러그인 시스템 1단계 테스트 시작")
    print("=" * 50)
    
    # 로깅 설정
    setup_logging()
    
    # 1. 플러그인 관리자 테스트
    manager = test_plugin_manager()
    
    # 2. 레지스트리 통합 테스트
    test_registry_integration()
    
    # 3. 이벤트 콜백 테스트
    test_event_callbacks()
    
    print("\n" + "=" * 50)
    print("플러그인 시스템 1단계 테스트 완료")
    print("✅ 기본 플러그인 인프라가 정상적으로 작동합니다!")


if __name__ == "__main__":
    main() 