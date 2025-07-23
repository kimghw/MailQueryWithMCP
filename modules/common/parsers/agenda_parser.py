"""
Agenda Parser Module
mail_process의 IACS 파싱 기능을 재사용 가능하도록 분리
"""

import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class AgendaParser:
    """IACS 아젠다 코드 파서"""
    
    def __init__(self):
        # 조직 코드
        self.org_codes = {
            'ABS', 'BV', 'CCS', 'CRS', 'DNV', 'IRS', 'KR', 'LR', 'NK', 'PRS', 'RINA', 'RS',
            'TL', 'VL', 'ABSSEA', 'BVWS', 'DNVAS', 'IRSNS', 'LRCC', 'IACS'
        }
        
        # 패널 타입
        self.panel_types = {'PL', 'PS', 'JWG-CS', 'JWG-SDT', 'SOG', 'SMICC'}
        
        # SynonymService 초기화
        from ..services.synonym_service import SynonymService
        self.synonym_service = SynonymService()
        
    def parse_agenda_code(self, text: str) -> Optional[Dict[str, Any]]:
        """
        텍스트에서 IACS 아젠다 코드 추출
        
        Returns:
            {
                'full_code': 'PL25016aIRa',
                'agenda_code': 'PL25016a',
                'panel': 'PL',
                'year': '25',
                'number': '016',
                'agenda_version': 'a',
                'response_org': 'IR',
                'response_version': 'a'
            }
        """
        # 응답 코드 패턴 (PL25016aIRa)
        response_patterns = [
            r'(PL|PS)(\d{2})(\d{3})([a-z])([A-Z]{2,})([a-z])',  # 붙어있는 형식
            r'(PL|PS)(\d{2})(\d{3})([a-z])_([A-Z]{2,})([a-z])',  # 언더스코어 형식
            r'(PL|PS)(\d{2})(\d{3})_([a-z])([A-Z]{2,})([a-z])',  # 다른 언더스코어 형식
        ]
        
        for pattern in response_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                return {
                    'full_code': match.group(0),
                    'agenda_code': f"{groups[0]}{groups[1]}{groups[2]}{groups[3]}",
                    'panel': groups[0].upper(),
                    'year': groups[1],
                    'number': groups[2],
                    'agenda_version': groups[3].lower(),
                    'response_org': groups[4].upper(),
                    'response_version': groups[5].lower()
                }
        
        # 기본 아젠다 코드 패턴 (PL25016a)
        agenda_patterns = [
            r'(PL|PS)(\d{2})(\d{3})([a-z])?',
            r'(JWG-(?:CS|SDT))(\d{2})(\d{3})([a-z])?',
        ]
        
        for pattern in agenda_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                agenda_code = f"{groups[0]}{groups[1]}{groups[2]}"
                if groups[3]:
                    agenda_code += groups[3]
                    
                return {
                    'full_code': match.group(0),
                    'agenda_code': agenda_code,
                    'panel': groups[0].upper(),
                    'year': groups[1],
                    'number': groups[2],
                    'agenda_version': groups[3].lower() if groups[3] else None,
                    'response_org': None,
                    'response_version': None
                }
        
        return None
    
    def extract_organizations(self, text: str) -> List[str]:
        """텍스트에서 조직 코드 추출"""
        organizations = []
        
        # SynonymService를 통한 조직명 추출
        org_code = self.synonym_service.get_organization_code(text)
        if org_code:
            organizations.append(org_code)
        
        # 직접 코드 매칭 (여러 조직이 언급될 수 있음)
        for org_code in self.org_codes:
            if re.search(rf'\b{org_code}\b', text, re.IGNORECASE):
                if org_code not in organizations:
                    organizations.append(org_code)
        
        # 특수 패턴: "KR의", "BV에서" 등
        korean_pattern = r'([A-Z]{2,})[의|에서|에게|로부터|이|가]'
        matches = re.findall(korean_pattern, text)
        for match in matches:
            if match in self.org_codes and match not in organizations:
                organizations.append(match)
        
        return organizations
    
    def extract_date_info(self, text: str) -> Optional[Dict[str, Any]]:
        """날짜 정보 추출"""
        now = datetime.now()
        
        # 상대적 시간 표현
        relative_patterns = {
            '오늘': 0,
            '어제': 1,
            '최근': 7,
            '이번주': 7,
            '지난주': 14,
            '이번달': 30,
            '지난달': 60,
            '올해': 365,
            '작년': 730,
        }
        
        for pattern, days in relative_patterns.items():
            if pattern in text:
                return {
                    'type': 'relative',
                    'days': days,
                    'start_date': now - timedelta(days=days),
                    'end_date': now
                }
        
        # N일/주/개월 전 패턴
        patterns = [
            (r'(\d+)\s*일\s*전', lambda x: int(x)),
            (r'(\d+)\s*주\s*전', lambda x: int(x) * 7),
            (r'(\d+)\s*개월\s*전', lambda x: int(x) * 30),
            (r'최근\s*(\d+)\s*일', lambda x: int(x)),
        ]
        
        for pattern, converter in patterns:
            match = re.search(pattern, text)
            if match:
                days = converter(match.group(1))
                return {
                    'type': 'relative',
                    'days': days,
                    'start_date': now - timedelta(days=days),
                    'end_date': now
                }
        
        # 절대 날짜 패턴
        date_pattern = r'(\d{4})[-./](\d{1,2})[-./](\d{1,2})'
        match = re.search(date_pattern, text)
        if match:
            try:
                year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                date = datetime(year, month, day)
                return {
                    'type': 'absolute',
                    'date': date,
                    'start_date': date,
                    'end_date': date
                }
            except:
                pass
        
        return None
    
    def extract_panel(self, text: str) -> Optional[str]:
        """패널 정보만 추출"""
        text_upper = text.upper()
        
        for panel in self.panel_types:
            if panel in text_upper:
                return panel
        
        return None