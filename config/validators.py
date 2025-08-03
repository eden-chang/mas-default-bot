"""
설정 검증 모듈 (보완된 버전)
애플리케이션 설정과 환경을 엄격하게 검증합니다.
"""

import os
import sys
import re
import socket
import ssl
import urllib.parse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union
from dataclasses import dataclass, field
from functools import lru_cache
import json
import hashlib

# 경로 설정 (VM 환경 대응)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

try:
    from config.settings import Config
except ImportError:
    # VM 환경에서 임포트 실패 시 폴백
    import importlib.util
    settings_path = os.path.join(os.path.dirname(__file__), 'settings.py')
    spec = importlib.util.spec_from_file_location("settings", settings_path)
    settings_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(settings_module)
    Config = settings_module.Config


@dataclass
class ValidationResult:
    """검증 결과를 담는 데이터 클래스 (보완된 버전)"""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    security_issues: List[str] = field(default_factory=list)
    performance_issues: List[str] = field(default_factory=list)
    network_issues: List[str] = field(default_factory=list)
    
    def add_error(self, error: str) -> None:
        """에러 추가"""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """경고 추가"""
        self.warnings.append(warning)
    
    def add_security_issue(self, issue: str) -> None:
        """보안 이슈 추가"""
        self.security_issues.append(issue)
        self.warnings.append(f"보안: {issue}")
    
    def add_performance_issue(self, issue: str) -> None:
        """성능 이슈 추가"""
        self.performance_issues.append(issue)
        self.warnings.append(f"성능: {issue}")
    
    def add_network_issue(self, issue: str) -> None:
        """네트워크 이슈 추가"""
        self.network_issues.append(issue)
        self.warnings.append(f"네트워크: {issue}")
    
    def get_summary(self) -> str:
        """검증 결과 요약 반환 (보완된 버전)"""
        if not any([self.errors, self.warnings, self.security_issues, 
                   self.performance_issues, self.network_issues]):
            return "✅ 모든 설정이 유효합니다."
        
        summary = []
        
        if self.is_valid:
            summary.append("✅ 모든 설정이 유효합니다.")
        else:
            summary.append("❌ 설정 검증 실패")
            
        if self.errors:
            summary.append("\n🚨 오류:")
            summary.extend(f"  - {error}" for error in self.errors)
        
        if self.security_issues:
            summary.append("\n🔒 보안 이슈:")
            summary.extend(f"  - {issue}" for issue in self.security_issues)
                
        if self.performance_issues:
            summary.append("\n⚡ 성능 이슈:")
            summary.extend(f"  - {issue}" for issue in self.performance_issues)
        
        if self.network_issues:
            summary.append("\n🌐 네트워크 이슈:")
            summary.extend(f"  - {issue}" for issue in self.network_issues)
                
        if self.warnings:
            summary.append("\n⚠️ 경고:")
            summary.extend(f"  - {warning}" for warning in self.warnings)
                
        return "\n".join(summary)
    
    def get_severity_score(self) -> int:
        """검증 결과의 심각도 점수 반환 (0-100)"""
        score = 0
        score += len(self.errors) * 20  # 에러: 20점씩
        score += len(self.security_issues) * 15  # 보안: 15점씩
        score += len(self.performance_issues) * 10  # 성능: 10점씩
        score += len(self.network_issues) * 8  # 네트워크: 8점씩
        score += len(self.warnings) * 5  # 경고: 5점씩
        return min(score, 100)


class ConfigValidator:
    """설정 검증 클래스 (보완된 버전)"""
    
    # 상수 정의 (성능 최적화)
    VALID_LOG_LEVELS = frozenset(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
    HTTP_PREFIXES = ('http://', 'https://')
    
    # 보안 관련 상수
    MIN_TOKEN_LENGTH = 20
    MIN_CLIENT_ID_LENGTH = 10
    MIN_CLIENT_SECRET_LENGTH = 20
    FORBIDDEN_PATTERNS = [
        r'password\s*=\s*["\']\w+["\']',
        r'secret\s*=\s*["\']\w+["\']',
        r'token\s*=\s*["\']\w+["\']',
    ]
    
    # 성능 관련 상수
    MAX_CACHE_SIZE = 1000
    MAX_LOG_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    MIN_MEMORY_REQUIREMENT = 512 * 1024 * 1024  # 512MB
    
    # 네트워크 관련 상수
    NETWORK_TIMEOUT = 10
    SSL_VERIFY_TIMEOUT = 5
    
    # 검증 규칙 정의 (보완된 버전)
    NUMERIC_CONFIGS = [
        ('MAX_RETRIES', 1, 10),
        ('BASE_WAIT_TIME', 1, 60),
        ('MAX_DICE_COUNT', 1, 100),
        ('MAX_DICE_SIDES', 2, 10000),
        ('MAX_CARD_COUNT', 1, 52),
        ('FORTUNE_CACHE_TTL', 0, 3600),
        ('LOG_MAX_BYTES', 1024, 104857600),  # 1KB ~ 100MB
        ('LOG_BACKUP_COUNT', 1, 20),
        ('MESSAGE_MAX_LENGTH', 100, 5000),
        ('API_TIMEOUT', 5, 60),
        ('CONNECTION_RETRY_INTERVAL', 1, 30),
        ('MAX_CONNECTION_RETRIES', 1, 10),
    ]
    
    REQUIRED_ENV_VARS = [
        'MASTODON_CLIENT_ID',
        'MASTODON_CLIENT_SECRET', 
        'MASTODON_ACCESS_TOKEN',
    ]
    
    OPTIONAL_ENV_VARS = [
        'MASTODON_API_BASE_URL',
        'SHEET_NAME',
        'GOOGLE_CREDENTIALS_PATH',
        'SYSTEM_ADMIN_ID',
        'LOG_LEVEL',
        'DEBUG_MODE',
    ]
    
    WORKSHEET_VALIDATION_RULES = {
        'ROSTER': {
            'required_headers': ['아이디', '이름'],
            'min_data_rows': 0,
            'validate_data': False,
            'max_data_rows': 10000,  # 최대 10,000명
            'data_validation': lambda record: (
                str(record.get('아이디', '')).strip() and 
                str(record.get('이름', '')).strip()
            )
        },
        'CUSTOM': {
            'required_headers': ['명령어', '문구'],
            'min_data_rows': 1,
            'validate_data': True,
            'max_data_rows': 1000,  # 최대 1,000개 커스텀 명령어
            'data_validation': lambda record: (
                str(record.get('명령어', '')).strip() and 
                str(record.get('문구', '')).strip() and
                len(str(record.get('문구', ''))) <= 500  # 문구 최대 500자
            )
        },
        'HELP': {
            'required_headers': ['명령어', '설명'],
            'min_data_rows': 1,
            'validate_data': True,
            'max_data_rows': 100,  # 최대 100개 도움말
            'data_validation': lambda record: (
                str(record.get('명령어', '')).strip() and 
                str(record.get('설명', '')).strip() and
                len(str(record.get('설명', ''))) <= 200  # 설명 최대 200자
            )
        },
        'FORTUNE': {
            'required_headers': ['문구'],
            'min_data_rows': 1,
            'validate_data': True,
            'max_data_rows': 500,  # 최대 500개 운세
            'data_validation': lambda record: (
                str(record.get('문구', '')).strip() and
                len(str(record.get('문구', ''))) <= 300  # 운세 최대 300자
            )
        }
    }
    
    @staticmethod
    def validate_environment() -> ValidationResult:
        """
        환경 변수와 기본 설정을 엄격하게 검증합니다.
        
        Returns:
            ValidationResult: 검증 결과
        """
        result = ValidationResult()
        
        # 1. 필수 환경 변수 검증
        ConfigValidator._validate_required_env_vars(result)
        
        # 2. 보안 검증
        ConfigValidator._validate_security_settings(result)
        
        # 3. 네트워크 연결 검증
        ConfigValidator._validate_network_connectivity(result)
        
        # 4. 성능 검증
        ConfigValidator._validate_performance_settings(result)
        
        # 5. 파일 시스템 검증
        ConfigValidator._validate_file_system(result)
        
        # 6. 숫자 설정값 검증
        ConfigValidator._validate_numeric_configs(result)
        
        # 7. 로그 설정 검증
        ConfigValidator._validate_logging_settings(result)
        
        # 8. API 설정 검증
        ConfigValidator._validate_api_settings(result)
        
        return result
    
    @staticmethod
    def _validate_required_env_vars(result: ValidationResult) -> None:
        """필수 환경 변수 검증"""
        for var_name in ConfigValidator.REQUIRED_ENV_VARS:
            var_value = getattr(Config, var_name, '')
            if not var_value or var_value.strip() == '':
                result.add_error(f"필수 환경 변수 '{var_name}'가 설정되지 않았습니다.")
            else:
                # 토큰 길이 검증
                if var_name == 'MASTODON_ACCESS_TOKEN' and len(var_value) < ConfigValidator.MIN_TOKEN_LENGTH:
                    result.add_security_issue(f"액세스 토큰이 너무 짧습니다. 최소 {ConfigValidator.MIN_TOKEN_LENGTH}자 필요.")
                
                if var_name == 'MASTODON_CLIENT_ID' and len(var_value) < ConfigValidator.MIN_CLIENT_ID_LENGTH:
                    result.add_security_issue(f"클라이언트 ID가 너무 짧습니다. 최소 {ConfigValidator.MIN_CLIENT_ID_LENGTH}자 필요.")
                
                if var_name == 'MASTODON_CLIENT_SECRET' and len(var_value) < ConfigValidator.MIN_CLIENT_SECRET_LENGTH:
                    result.add_security_issue(f"클라이언트 시크릿이 너무 짧습니다. 최소 {ConfigValidator.MIN_CLIENT_SECRET_LENGTH}자 필요.")
    
    @staticmethod
    def _validate_security_settings(result: ValidationResult) -> None:
        """보안 설정 검증"""
        # HTTPS URL 검증
        api_url = getattr(Config, 'MASTODON_API_BASE_URL', '')
        if api_url and not api_url.startswith('https://'):
            result.add_security_issue("API URL이 HTTPS가 아닙니다. 보안을 위해 HTTPS를 사용하세요.")
        
        # 민감한 정보 노출 검증
        for pattern in ConfigValidator.FORBIDDEN_PATTERNS:
            if re.search(pattern, str(Config.__dict__), re.IGNORECASE):
                result.add_security_issue("설정에 민감한 정보가 노출되어 있습니다.")
                break
        
        # 관리자 ID 검증
        admin_id = getattr(Config, 'SYSTEM_ADMIN_ID', '')
        if not admin_id or admin_id.strip() == '':
            result.add_warning("SYSTEM_ADMIN_ID가 설정되지 않았습니다. 오류 알림을 받을 수 없습니다.")
        elif len(admin_id) < 3:
            result.add_security_issue("관리자 ID가 너무 짧습니다.")
    
    @staticmethod
    def _validate_network_connectivity(result: ValidationResult) -> None:
        """네트워크 연결 검증"""
        try:
            # DNS 연결 테스트
            socket.gethostbyname("8.8.8.8")
        except socket.gaierror:
            result.add_network_issue("DNS 연결에 문제가 있습니다.")
        
        # API 서버 연결 테스트
        api_url = getattr(Config, 'MASTODON_API_BASE_URL', '')
        if api_url:
            try:
                parsed_url = urllib.parse.urlparse(api_url)
                host = parsed_url.netloc
                port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(ConfigValidator.NETWORK_TIMEOUT)
                sock.connect((host, port))
                sock.close()
            except Exception as e:
                result.add_network_issue(f"API 서버 연결 실패: {host}:{port} - {str(e)}")
        
        # Google 서비스 연결 테스트
        try:
            socket.gethostbyname("sheets.googleapis.com")
        except socket.gaierror:
            result.add_network_issue("Google Sheets API 연결에 문제가 있습니다.")
    
    @staticmethod
    def _validate_performance_settings(result: ValidationResult) -> None:
        """성능 설정 검증"""
        # 메모리 사용량 검증
        try:
            import psutil
            available_memory = psutil.virtual_memory().available
            if available_memory < ConfigValidator.MIN_MEMORY_REQUIREMENT:
                result.add_performance_issue(f"사용 가능한 메모리가 부족합니다. 최소 {ConfigValidator.MIN_MEMORY_REQUIREMENT // (1024*1024)}MB 필요.")
        except ImportError:
            result.add_warning("psutil이 설치되지 않아 메모리 검증을 건너뜁니다.")
        
        # 캐시 설정 검증
        cache_ttl = getattr(Config, 'FORTUNE_CACHE_TTL', 3600)
        if cache_ttl > 86400:  # 24시간
            result.add_performance_issue("캐시 TTL이 너무 깁니다. 메모리 사용량이 증가할 수 있습니다.")
        
        # 로그 파일 크기 검증
        log_max_bytes = getattr(Config, 'LOG_MAX_BYTES', 10485760)
        if log_max_bytes > ConfigValidator.MAX_LOG_FILE_SIZE:
            result.add_performance_issue("로그 파일 크기가 너무 큽니다. 디스크 공간을 많이 사용할 수 있습니다.")
    
    @staticmethod
    def _validate_file_system(result: ValidationResult) -> None:
        """파일 시스템 검증"""
        # Google 인증 파일 검증
        cred_path = Config.get_credentials_path()
        if not cred_path.exists():
            result.add_error(f"Google 인증 파일을 찾을 수 없습니다: {cred_path}")
        elif not cred_path.is_file():
            result.add_error(f"Google 인증 파일이 올바른 파일이 아닙니다: {cred_path}")
        else:
            # 파일 크기 검증
            if cred_path.stat().st_size > 1024 * 1024:  # 1MB
                result.add_security_issue("Google 인증 파일이 너무 큽니다. 보안상 문제가 있을 수 있습니다.")
            
            # 파일 권한 검증
            try:
                if os.access(cred_path, os.R_OK):
                    result.add_security_issue("Google 인증 파일이 다른 사용자에게 읽기 권한이 있습니다.")
            except OSError:
                pass
        
        # 로그 디렉토리 검증
        ConfigValidator._validate_log_directory(result)
    
    @staticmethod
    def _validate_numeric_configs(result: ValidationResult) -> None:
        """숫자 설정값 검증"""
        for name, min_val, max_val in ConfigValidator.NUMERIC_CONFIGS:
            value = getattr(Config, name, None)
            if not isinstance(value, int) or value < min_val or value > max_val:
                result.add_error(f"{name}은 {min_val}과 {max_val} 사이의 정수여야 합니다. 현재값: {value}")
    
    @staticmethod
    def _validate_logging_settings(result: ValidationResult) -> None:
        """로깅 설정 검증"""
        # 로그 레벨 검증
        log_level = getattr(Config, 'LOG_LEVEL', 'INFO')
        if log_level.upper() not in ConfigValidator.VALID_LOG_LEVELS:
            result.add_error(f"LOG_LEVEL은 다음 중 하나여야 합니다: {', '.join(ConfigValidator.VALID_LOG_LEVELS)}")
        
        # 디버그 모드 검증
        debug_mode = getattr(Config, 'DEBUG_MODE', False)
        if debug_mode and log_level.upper() != 'DEBUG':
            result.add_warning("디버그 모드가 활성화되었지만 로그 레벨이 DEBUG가 아닙니다.")
        
        # 시트 이름 검증
        sheet_name = getattr(Config, 'SHEET_NAME', '')
        if not sheet_name or sheet_name.strip() == '':
            result.add_error("SHEET_NAME이 설정되지 않았습니다.")
        elif len(sheet_name) > 100:
            result.add_warning("시트 이름이 너무 깁니다.")
    
    @staticmethod
    def _validate_api_settings(result: ValidationResult) -> None:
        """API 설정 검증"""
        # API URL 형식 검증
        api_url = getattr(Config, 'MASTODON_API_BASE_URL', '')
        if api_url:
            try:
                parsed = urllib.parse.urlparse(api_url)
                if not parsed.scheme or not parsed.netloc:
                    result.add_error("API URL 형식이 올바르지 않습니다.")
                elif parsed.scheme not in ['http', 'https']:
                    result.add_error("API URL은 http 또는 https 프로토콜을 사용해야 합니다.")
            except Exception as e:
                result.add_error(f"API URL 파싱 실패: {str(e)}")
    
    @staticmethod
    def _validate_log_directory(result: ValidationResult) -> None:
        """로그 디렉토리 검증 및 생성 (보완된 버전)"""
        log_dir = Path(Config.LOG_FILE_PATH).parent
        if not log_dir.exists():
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
                result.add_warning(f"로그 디렉토리를 생성했습니다: {log_dir}")
            except PermissionError:
                result.add_error(f"로그 디렉토리를 생성할 권한이 없습니다: {log_dir}")
            except Exception as e:
                result.add_error(f"로그 디렉토리 생성 실패: {str(e)}")
        else:
            # 디렉토리 권한 검증
            try:
                if not os.access(log_dir, os.W_OK):
                    result.add_error(f"로그 디렉토리에 쓰기 권한이 없습니다: {log_dir}")
            except OSError:
                result.add_error(f"로그 디렉토리 권한 확인 실패: {log_dir}")
    
    @staticmethod
    def validate_sheet_structure(sheet) -> ValidationResult:
        """
        Google Sheets 구조를 엄격하게 검증합니다.
        
        Args:
            sheet: Google Spreadsheet 객체
            
        Returns:
            ValidationResult: 검증 결과
        """
        result = ValidationResult()
        
        try:
            # 1. 필수 워크시트 존재 확인
            ConfigValidator._validate_required_worksheets(sheet, result)
            
            # 2. 각 워크시트별 구조 검증
            for sheet_key, rules in ConfigValidator.WORKSHEET_VALIDATION_RULES.items():
                ConfigValidator._validate_worksheet(sheet, sheet_key, rules, result)
            
            # 3. 데이터 무결성 검증
            ConfigValidator._validate_data_integrity(sheet, result)
            
        except Exception as e:
            result.add_error(f"시트 구조 검증 중 오류 발생: {str(e)}")
        
        return result
    
    @staticmethod
    def _validate_required_worksheets(sheet, result: ValidationResult) -> None:
        """필수 워크시트 존재 확인"""
        worksheet_titles = frozenset(ws.title for ws in sheet.worksheets())
        required_worksheets = frozenset(Config.WORKSHEET_NAMES.values())
        
        missing_worksheets = required_worksheets - worksheet_titles
        for missing_sheet in missing_worksheets:
            result.add_error(f"필수 워크시트 '{missing_sheet}'가 없습니다.")
        
        # 추가 워크시트 확인
        extra_worksheets = worksheet_titles - required_worksheets
        if extra_worksheets:
            result.add_warning(f"추가 워크시트가 발견되었습니다: {', '.join(extra_worksheets)}")
    
    @staticmethod
    def _validate_worksheet(sheet, sheet_key: str, rules: Dict, result: ValidationResult) -> None:
        """워크시트 검증 (보완된 버전)"""
        try:
            worksheet_name = Config.get_worksheet_name(sheet_key)
            if not worksheet_name:
                result.add_error(f"워크시트 이름을 찾을 수 없습니다: {sheet_key}")
                return
                
            worksheet = sheet.worksheet(worksheet_name)
            headers = worksheet.row_values(1) if worksheet.row_count > 0 else []
            
            # 1. 헤더 검증
            ConfigValidator._validate_worksheet_headers(worksheet_name, headers, rules, result)
            
            # 2. 데이터 검증
            if rules.get('validate_data', False):
                ConfigValidator._validate_worksheet_data(worksheet, worksheet_name, rules, result)
            
            # 3. 데이터 양 검증
            ConfigValidator._validate_data_volume(worksheet, worksheet_name, rules, result)
                
        except Exception as e:
            result.add_error(f"'{worksheet_name}' 시트 검증 실패: {str(e)}")
    
    @staticmethod
    def _validate_worksheet_headers(worksheet_name: str, headers: List[str], rules: Dict, result: ValidationResult) -> None:
        """워크시트 헤더 검증"""
        required_headers = rules.get('required_headers', [])
        missing_headers = [h for h in required_headers if h not in headers]
        
        for header in missing_headers:
            result.add_error(f"'{worksheet_name}' 시트에 '{header}' 헤더가 없습니다.")
        
        # 추가 헤더 확인
        extra_headers = [h for h in headers if h not in required_headers]
        if extra_headers:
            result.add_warning(f"'{worksheet_name}' 시트에 추가 헤더가 있습니다: {', '.join(extra_headers)}")
    
    @staticmethod
    def _validate_worksheet_data(worksheet, worksheet_name: str, rules: Dict, result: ValidationResult) -> None:
        """워크시트 데이터 검증 (보완된 버전)"""
        min_data_rows = rules.get('min_data_rows', 0)
        data_validation = rules.get('data_validation')
        
        if worksheet.row_count <= 1:  # 헤더만 있는 경우
            if min_data_rows > 0:
                result.add_error(f"'{worksheet_name}' 시트에 데이터가 없습니다.")
            return
        
        if data_validation:
            all_records = worksheet.get_all_records()
            valid_records = []
            invalid_records = []
            
            for i, record in enumerate(all_records, start=2):  # 2부터 시작 (헤더 제외)
                if data_validation(record):
                    valid_records.append(record)
                else:
                    invalid_records.append(i)
            
            if len(valid_records) == 0:
                if min_data_rows > 0:
                    result.add_error(f"'{worksheet_name}' 시트에 유효한 데이터가 없습니다.")
                else:
                    result.add_warning(f"'{worksheet_name}' 시트에 유효한 데이터가 없습니다.")
            
            if invalid_records:
                result.add_warning(f"'{worksheet_name}' 시트에 {len(invalid_records)}개의 유효하지 않은 행이 있습니다: {invalid_records[:5]}{'...' if len(invalid_records) > 5 else ''}")
            
            # 커스텀 시트 특별 검증
            if worksheet_name == Config.get_worksheet_name('CUSTOM'):
                ConfigValidator._validate_custom_commands(valid_records, result)
    
    @staticmethod
    def _validate_data_volume(worksheet, worksheet_name: str, rules: Dict, result: ValidationResult) -> None:
        """데이터 양 검증"""
        max_data_rows = rules.get('max_data_rows', 10000)
        data_rows = worksheet.row_count - 1  # 헤더 제외
        
        if data_rows > max_data_rows:
            result.add_performance_issue(f"'{worksheet_name}' 시트의 데이터가 너무 많습니다. 최대 {max_data_rows}행 권장, 현재 {data_rows}행")
    
    @staticmethod
    def _validate_custom_commands(all_records: List[Dict], result: ValidationResult) -> None:
        """커스텀 명령어 중복 검증 (보완된 버전)"""
        commands = []
        duplicates = []
        
        for record in all_records:
            command = str(record.get('명령어', '')).strip()
            if command:
                if command in commands:
                    duplicates.append(command)
                else:
                    commands.append(command)
                
                # 시스템 키워드 중복 검사
                if Config.is_system_keyword(command):
                    result.add_warning(f"커스텀 명령어 '{command}'가 시스템 키워드와 중복됩니다.")
                
                # 명령어 형식 검사
                if len(command) < 2:
                    result.add_warning(f"커스텀 명령어 '{command}'가 너무 짧습니다.")
                elif len(command) > 50:
                    result.add_warning(f"커스텀 명령어 '{command}'가 너무 깁니다.")
        
        if duplicates:
            result.add_error(f"중복된 커스텀 명령어가 있습니다: {', '.join(set(duplicates))}")
    
    @staticmethod
    def _validate_data_integrity(sheet, result: ValidationResult) -> None:
        """데이터 무결성 검증"""
        try:
            # 전체 시트 크기 검증
            total_cells = sum(ws.row_count * ws.col_count for ws in sheet.worksheets())
            if total_cells > 1000000:  # 100만 셀
                result.add_performance_issue("전체 시트 크기가 너무 큽니다. 성능에 영향을 줄 수 있습니다.")
            
            # 빈 시트 확인
            empty_worksheets = []
            for ws in sheet.worksheets():
                if ws.row_count <= 1:  # 헤더만 있거나 빈 시트
                    empty_worksheets.append(ws.title)
            
            if empty_worksheets:
                result.add_warning(f"빈 워크시트가 있습니다: {', '.join(empty_worksheets)}")
                
        except Exception as e:
            result.add_warning(f"데이터 무결성 검증 중 오류: {str(e)}")
    
    @staticmethod
    def validate_all(sheet=None) -> ValidationResult:
        """
        모든 설정을 종합적으로 검증합니다.
        
        Args:
            sheet: Google Spreadsheet 객체 (선택사항)
            
        Returns:
            ValidationResult: 종합 검증 결과
        """
        # 환경 설정 검증
        env_result = ConfigValidator.validate_environment()
        
        # 시트가 제공된 경우 시트 구조도 검증
        if sheet is not None:
            sheet_result = ConfigValidator.validate_sheet_structure(sheet)
            
            # 결과 합성
            combined_result = ValidationResult(
                is_valid=env_result.is_valid and sheet_result.is_valid,
                errors=env_result.errors + sheet_result.errors,
                warnings=env_result.warnings + sheet_result.warnings,
                security_issues=env_result.security_issues + sheet_result.security_issues,
                performance_issues=env_result.performance_issues + sheet_result.performance_issues,
                network_issues=env_result.network_issues + sheet_result.network_issues
            )
        else:
            combined_result = env_result
            combined_result.add_warning("시트 구조 검증을 수행하지 않았습니다.")
        
        return combined_result
    
    @staticmethod
    def get_validation_report() -> Dict[str, Any]:
        """상세한 검증 리포트 생성"""
        result = ConfigValidator.validate_all()
        
        return {
            'is_valid': result.is_valid,
            'severity_score': result.get_severity_score(),
            'summary': result.get_summary(),
            'error_count': len(result.errors),
            'warning_count': len(result.warnings),
            'security_issue_count': len(result.security_issues),
            'performance_issue_count': len(result.performance_issues),
            'network_issue_count': len(result.network_issues),
            'total_issues': len(result.errors) + len(result.warnings) + 
                           len(result.security_issues) + len(result.performance_issues) + 
                           len(result.network_issues)
        }


def validate_startup_config(sheet=None) -> Tuple[bool, str]:
    """
    시작시 설정 검증을 수행하고 결과를 반환합니다.
    
    Args:
        sheet: Google Spreadsheet 객체 (선택사항)
        
    Returns:
        Tuple[bool, str]: (검증 성공 여부, 검증 결과 메시지)
    """
    result = ConfigValidator.validate_all(sheet)
    return result.is_valid, result.get_summary()


def get_detailed_validation_report(sheet=None) -> Dict[str, Any]:
    """
    상세한 검증 리포트를 반환합니다.
    
    Args:
        sheet: Google Spreadsheet 객체 (선택사항)
        
    Returns:
        Dict[str, Any]: 상세한 검증 리포트
    """
    return ConfigValidator.get_validation_report()


def validate_network_connectivity() -> Tuple[bool, List[str]]:
    """
    네트워크 연결을 테스트합니다.
    
    Returns:
        Tuple[bool, List[str]]: (연결 성공 여부, 문제 목록)
    """
    issues = []
    
    # DNS 연결 테스트
    try:
        socket.gethostbyname("8.8.8.8")
    except socket.gaierror:
        issues.append("DNS 연결 실패")
    
    # Google 서비스 연결 테스트
    try:
        socket.gethostbyname("sheets.googleapis.com")
    except socket.gaierror:
        issues.append("Google Sheets API 연결 실패")
    
    # API 서버 연결 테스트
    api_url = getattr(Config, 'MASTODON_API_BASE_URL', '')
    if api_url:
        try:
            parsed_url = urllib.parse.urlparse(api_url)
            host = parsed_url.netloc
            port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(ConfigValidator.NETWORK_TIMEOUT)
            sock.connect((host, port))
            sock.close()
        except Exception as e:
            issues.append(f"API 서버 연결 실패: {str(e)}")
    
    return len(issues) == 0, issues