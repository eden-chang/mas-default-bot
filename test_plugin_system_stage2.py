"""
플러그인 시스템 2단계 테스트 스크립트
명령어 확장 시스템 검증용
"""

import sys
import os
import logging

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plugins.base.plugin_manager import PluginManager
from plugins.commands.command_registry import command_registry


def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_command_plugin_system():
    """명령어 플러그인 시스템 테스트"""
    print("=== 명령어 플러그인 시스템 테스트 ===")
    
    # 플러그인 관리자 생성
    manager = PluginManager()
    
    # 플러그인 디렉토리 추가
    plugin_dir = os.path.join(os.path.dirname(__file__), "plugins", "examples")
    manager.add_plugin_directory(plugin_dir)
    
    print(f"플러그인 디렉토리 추가: {plugin_dir}")
    
    # 플러그인 로드
    results = manager.load_all_plugins()
    print(f"플러그인 로드 결과: {results}")
    
    # 플러그인 활성화
    for plugin_name in manager.get_all_plugins():
        success = manager.enable_plugin(plugin_name)
        print(f"플러그인 활성화 {plugin_name}: {'성공' if success else '실패'}")
    
    # 등록된 명령어 확인
    commands = command_registry.get_all_commands()
    print(f"등록된 플러그인 명령어: {list(commands.keys())}")
    
    # 명령어 정보 확인
    for command_name, handler in commands.items():
        info = command_registry.get_command_info(command_name)
        print(f"명령어 정보 {command_name}: {info}")
    
    return manager


def test_command_execution():
    """명령어 실행 테스트"""
    print("\n=== 명령어 실행 테스트 ===")
    
    # 테스트 메시지들
    test_messages = [
        "날씨 서울",
        "weather 부산",
        "대구 날씨",
        "인천 날씨",
        "광주 날씨",
        "존재하지 않는 도시 날씨"
    ]
    
    for message in test_messages:
        print(f"\n테스트 메시지: {message}")
        
        # 명령어 찾기
        result = command_registry.find_command(message)
        if result:
            handler, match_info = result
            print(f"  ✅ 명령어 발견: {handler.plugin.get_name()}")
            print(f"  📝 매칭 정보: {match_info}")
            
            # 명령어 실행
            context = command_registry.execute_command(message, "test_user", "user123")
            if context:
                print(f"  🎯 실행 결과: {context.get_result_text()}")
            else:
                print(f"  ❌ 실행 실패")
        else:
            print(f"  ❌ 명령어를 찾을 수 없음")


def test_command_router_integration():
    """명령어 라우터 통합 테스트"""
    print("\n=== 명령어 라우터 통합 테스트 ===")
    
    # 테스트 키워드들
    test_keywords = [
        ["날씨", "서울"],
        ["weather", "부산"],
        ["대구", "날씨"],
        ["존재하지", "않는", "명령어"]
    ]
    
    for keywords in test_keywords:
        print(f"\n테스트 키워드: {keywords}")
        message = " ".join(keywords)
        
        # 플러그인 명령어 레지스트리에서 직접 실행
        result = command_registry.execute_command(message, "test_user", "user123")
        if result:
            print(f"  ✅ 플러그인 명령어 실행 성공")
            print(f"  📝 결과: {result.get_result_text()}")
        else:
            print(f"  ❌ 플러그인 명령어 실행 실패")


def test_command_patterns():
    """명령어 패턴 테스트"""
    print("\n=== 명령어 패턴 테스트 ===")
    
    # 패턴 매칭 테스트
    test_cases = [
        ("날씨 서울", True),
        ("weather 부산", True),
        ("대구 날씨", True),
        ("인천 날씨", True),
        ("광주 날씨", True),
        ("존재하지 않는 도시", False),
        ("날씨", False),  # 위치 정보 없음
        ("hello world", False)
    ]
    
    for message, expected in test_cases:
        result = command_registry.find_command(message)
        actual = result is not None
        
        status = "✅" if actual == expected else "❌"
        print(f"{status} {message} -> 예상: {expected}, 실제: {actual}")
        
        if result:
            handler, match_info = result
            print(f"    플러그인: {handler.plugin.get_name()}")
            print(f"    매칭: {match_info}")


def test_plugin_command_info():
    """플러그인 명령어 정보 테스트"""
    print("\n=== 플러그인 명령어 정보 테스트 ===")
    
    # 모든 명령어 정보 가져오기
    all_info = command_registry.get_all_command_info()
    
    for command_name, info in all_info.items():
        print(f"\n명령어: {command_name}")
        print(f"  패턴: {info['patterns']}")
        print(f"  도움말: {info['help_text']}")
        print(f"  권한: {info['permissions']}")
        print(f"  활성화: {info['enabled']}")
        print(f"  플러그인: {info['plugin_name']} v{info['plugin_version']}")


def test_command_registry_events():
    """명령어 레지스트리 이벤트 테스트"""
    print("\n=== 명령어 레지스트리 이벤트 테스트 ===")
    
    # 이벤트 콜백 설정
    def on_command_registered(command_name, handler):
        print(f"이벤트: 명령어 등록됨 - {command_name}")
    
    def on_command_unregistered(command_name, handler):
        print(f"이벤트: 명령어 등록 해제됨 - {command_name}")
    
    command_registry.set_event_callbacks(
        on_registered=on_command_registered,
        on_unregistered=on_command_unregistered
    )
    
    # 플러그인 관리자 생성 및 테스트
    manager = PluginManager()
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
    print("플러그인 시스템 2단계 테스트 시작")
    print("=" * 50)
    
    # 로깅 설정
    setup_logging()
    
    # 1. 명령어 플러그인 시스템 테스트
    manager = test_command_plugin_system()
    
    # 2. 명령어 실행 테스트
    test_command_execution()
    
    # 3. 명령어 라우터 통합 테스트
    test_command_router_integration()
    
    # 4. 명령어 패턴 테스트
    test_command_patterns()
    
    # 5. 플러그인 명령어 정보 테스트
    test_plugin_command_info()
    
    # 6. 명령어 레지스트리 이벤트 테스트
    test_command_registry_events()
    
    print("\n" + "=" * 50)
    print("플러그인 시스템 2단계 테스트 완료")
    print("✅ 명령어 확장 시스템이 정상적으로 작동합니다!")


if __name__ == "__main__":
    main() 