"""mail_process 모듈 환경설정"""

import os
from pathlib import Path
from typing import List, Optional


class MailProcessConfig:
    """메일 처리 모듈 설정 (환경변수 기반)"""

    # ===== Processing Limits =====
    @property
    def max_keywords_per_mail(self) -> int:
        return int(os.getenv('MAX_KEYWORDS_PER_MAIL', '5'))

    @property
    def max_mails_per_account(self) -> int:
        return int(os.getenv('MAX_MAILS_PER_ACCOUNT', '200'))

    @property
    def mail_batch_size(self) -> int:
        return int(os.getenv('MAIL_BATCH_SIZE', '100'))

    # ===== Processing Options =====
    @property
    def process_duplicate_mails(self) -> bool:
        return os.getenv('PROCESS_DUPLICATE_MAILS', 'true').lower() == 'true'

    @property
    def enable_mail_filtering(self) -> bool:
        return os.getenv('ENABLE_MAIL_FILTERING', 'true').lower() == 'true'

    @property
    def enable_structured_extraction(self) -> bool:
        return os.getenv('ENABLE_STRUCTURED_EXTRACTION', 'true').lower() == 'true'

    # ===== Filtering Rules =====
    @property
    def blocked_domains(self) -> List[str]:
        """차단할 도메인 목록"""
        domains_str = os.getenv('BLOCKED_DOMAINS', '')
        if not domains_str:
            return []
        return [d.strip() for d in domains_str.split(',') if d.strip()]

    @property
    def blocked_keywords(self) -> List[str]:
        """차단할 키워드 목록"""
        keywords_str = os.getenv('BLOCKED_KEYWORDS', '')
        if not keywords_str:
            return []
        return [k.strip() for k in keywords_str.split(',') if k.strip()]

    @property
    def blocked_sender_patterns(self) -> List[str]:
        """차단할 발신자 패턴 목록"""
        patterns_str = os.getenv('BLOCKED_SENDER_PATTERNS', '')
        if not patterns_str:
            return []
        return [p.strip() for p in patterns_str.split(',') if p.strip()]

    # ===== Default Directories =====
    @property
    def default_output_dir(self) -> Path:
        """기본 출력 디렉토리"""
        return Path(os.getenv('MAIL_OUTPUT_DIR', './mail_data'))

    @property
    def default_temp_dir(self) -> Optional[Path]:
        """기본 임시 디렉토리"""
        temp_dir = os.getenv('MAIL_TEMP_DIR', '')
        if temp_dir:
            return Path(temp_dir)
        return None


# 싱글톤 인스턴스
_config = MailProcessConfig()


def get_mail_process_config() -> MailProcessConfig:
    """메일 처리 설정 가져오기"""
    return _config
