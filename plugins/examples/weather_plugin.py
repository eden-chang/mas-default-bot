"""
날씨 명령어 플러그인
2단계 테스트용 플러그인
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from typing import Dict, Any, Optional, List
from plugins.base.plugin_base import PluginBase, PluginMetadata
from plugins.commands.command_plugin import CommandPlugin, CommandContext
from models.base.base_result import BaseResult


# 플러그인 메타데이터
PLUGIN_METADATA = PluginMetadata(
    name="WeatherPlugin",
    version="1.0.0",
    description="날씨 정보를 제공하는 플러그인",
    author="Plugin System",
    dependencies=[],
    permissions=[]
)


class WeatherResult(BaseResult):
    """날씨 결과 클래스"""
    
    def __init__(self, location: str, temperature: float, condition: str, humidity: int):
        super().__init__()
        self.location = location
        self.temperature = temperature
        self.condition = condition
        self.humidity = humidity
    
    def get_result_text(self) -> str:
        """결과 텍스트 생성"""
        return f"📍 {self.location}의 날씨\n🌡️ 온도: {self.temperature}°C\n☁️ 날씨: {self.condition}\n💧 습도: {self.humidity}%"


class WeatherPlugin(CommandPlugin):
    """날씨 명령어 플러그인"""
    
    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        self.weather_data = {
            "서울": {"temp": 25, "condition": "맑음", "humidity": 60},
            "부산": {"temp": 28, "condition": "흐림", "humidity": 75},
            "대구": {"temp": 30, "condition": "맑음", "humidity": 45},
            "인천": {"temp": 23, "condition": "비", "humidity": 85},
            "광주": {"temp": 27, "condition": "맑음", "humidity": 55}
        }
        self.logger.info("WeatherPlugin.__init__() 호출됨")
        # 명령어 정보 직접 초기화
        self.logger.info("WeatherPlugin.__init__()에서 _initialize_command_info() 호출 시작")
        self._initialize_command_info()
        self.logger.info("WeatherPlugin.__init__()에서 _initialize_command_info() 호출 완료")
    
    def _initialize_command_info(self):
        """명령어 정보 초기화"""
        self.logger.info("WeatherPlugin._initialize_command_info() 호출됨")
        # 명령어 패턴 설정
        self.command_patterns = [
            "날씨 {location}",
            "weather {location}",
            "{location} 날씨"
        ]
        self.help_text = "날씨 정보를 조회합니다. 사용법: 날씨 [도시명]"
        self.permissions = []
        self.logger.info(f"WeatherPlugin 명령어 패턴 초기화 완료: {self.command_patterns}")
        self.logger.info(f"WeatherPlugin 도움말 초기화 완료: {self.help_text}")
        # 디버깅을 위한 추가 로그
        self.logger.info(f"WeatherPlugin 패턴 설정 후 확인: {self.command_patterns}")
    
    def execute(self, context: CommandContext) -> Optional[BaseResult]:
        """명령어 실행"""
        try:
            # 인수에서 위치 추출
            location = self._extract_location(context)
            if not location:
                return None
            
            # 날씨 데이터 가져오기
            weather_info = self._get_weather_info(location)
            if not weather_info:
                return None
            
            # 결과 생성
            result = WeatherResult(
                location=location,
                temperature=weather_info["temp"],
                condition=weather_info["condition"],
                humidity=weather_info["humidity"]
            )
            
            self.logger.info(f"날씨 정보 조회: {context.user_name} -> {location}")
            return result
            
        except Exception as e:
            self.logger.error(f"날씨 명령어 실행 오류: {e}")
            return None
    
    def _extract_location(self, context: CommandContext) -> Optional[str]:
        """위치 정보 추출"""
        # 패턴에서 위치 정보 추출
        if context.additional_data and 'args' in context.additional_data:
            args = context.additional_data['args']
            if args:
                return args[0]
        
        # 메시지에서 위치 추출 시도
        message = context.message.lower()
        for location in self.weather_data.keys():
            if location in message:
                return location
        
        return None
    
    def _get_weather_info(self, location: str) -> Optional[Dict[str, Any]]:
        """날씨 정보 가져오기"""
        return self.weather_data.get(location)
    
    def get_available_locations(self) -> List[str]:
        """사용 가능한 위치 목록 반환"""
        return list(self.weather_data.keys()) 