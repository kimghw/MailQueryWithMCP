"""
Query Parameter Extractor
자연어 쿼리에서 파라미터 추출 및 동의어 처리
"""

import re
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from .agenda_parser import AgendaParser
from ..services.synonym_service import SynonymService

logger = logging.getLogger(__name__)


class QueryParameterExtractor:
    """쿼리 파라미터 추출기"""
    
    def __init__(self, preprocessing_repo=None):
        self.agenda_parser = AgendaParser()
        self.synonym_service = SynonymService(preprocessing_repo)
        
    def extract_parameters(self, query: str) -> Dict[str, Any]:
        """
        자연어 쿼리에서 파라미터 추출
        
        Returns:
            {
                'agenda_code': 'PL25016a',
                'agenda_base_version': 'a',
                'agenda_panel': 'PL',
                'sender_organization': 'KR',
                'response_org': 'BV',
                'date_range': {'start': datetime, 'end': datetime},
                'days': 30,
                'status': 'approved',
                'limit': 10,
                'keyword': 'search_term',
                'normalized_query': '동의어 처리된 쿼리'
            }
        """
        # 동의어 정규화
        normalized_query = self.normalize_query(query)
        
        result = {
            'original_query': query,
            'normalized_query': normalized_query
        }
        
        # 1. 아젠다 코드 파싱
        agenda_info = self.agenda_parser.parse_agenda_code(query)
        if agenda_info:
            # agenda_base: 패널+년도+번호 (예: PL25016)
            result['agenda_base'] = f"{agenda_info['panel']}{agenda_info['year']}{agenda_info['number']}"
            # agenda_base_version: 버전 (예: a, b, c)
            result['agenda_base_version'] = agenda_info['agenda_version']
            # 전체 코드도 저장
            result['agenda_code'] = agenda_info['agenda_code']
            result['agenda_panel'] = agenda_info['panel']
            
            if agenda_info['response_org']:
                result['response_org'] = agenda_info['response_org']
        
        # 2. 조직 정보 추출
        organizations = self.agenda_parser.extract_organizations(query)
        if organizations:
            # organization_code: 조직 코드 (예: KR, ABS, LR)
            result['organization_code'] = organizations[0]
            # organization: 조직명 전체 (동의어 사전에서 원본 텍스트 찾기)
            org_text = self._extract_organization_text(query, organizations[0])
            if org_text:
                result['organization'] = org_text
            else:
                result['organization'] = organizations[0]
            
            # 이전 호환성 유지
            result['sender_organization'] = organizations[0]
            if len(organizations) > 1 and 'response_org' not in result:
                result['response_org'] = organizations[1]
        
        # 3. 날짜 정보 추출
        date_info = self.agenda_parser.extract_date_info(query)
        if date_info:
            if 'start_date' in date_info:
                result['date_range'] = {
                    'start': date_info['start_date'],
                    'end': date_info['end_date']
                }
            if 'days' in date_info:
                result['days'] = date_info['days']
        
        # 4. 상태 정보 추출
        status = self._extract_status(normalized_query)
        if status:
            result['status'] = status
        
        # 5. 숫자 파라미터 추출 (limit)
        limit = self._extract_limit(query)
        if limit:
            result['limit'] = limit
        
        # 6. 키워드 추출
        keyword = self._extract_keyword(query)
        if keyword:
            result['keyword'] = keyword
        
        # 7. 패널 정보 (코드가 없는 경우)
        if 'agenda_panel' not in result:
            panel = self.agenda_parser.extract_panel(query)
            if panel:
                result['agenda_panel'] = panel
        
        return result
    
    def normalize_query(self, query: str) -> str:
        """동의어를 사용하여 쿼리 정규화"""
        return self.synonym_service.normalize_text(query)
    
    def _extract_status(self, text: str) -> Optional[str]:
        """상태 정보 추출"""
        status_patterns = {
            'approved': ['승인', 'approved', '허가', '통과'],
            'rejected': ['반려', 'rejected', '거부', '거절', '기각'],
            'pending': ['미결정', 'pending', '대기', '보류', '검토중']
        }
        
        text_lower = text.lower()
        for status, patterns in status_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    return status
        
        return None
    
    def _extract_limit(self, text: str) -> Optional[int]:
        """숫자 제한 추출"""
        patterns = [
            r'(\d+)\s*개',
            r'(\d+)\s*건',
            r'상위\s*(\d+)',
            r'최대\s*(\d+)',
            r'limit\s*(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None
    
    def _extract_keyword(self, text: str) -> Optional[str]:
        """검색 키워드 추출"""
        # 따옴표로 묶인 텍스트
        patterns = [
            r'"([^"]+)"',
            r"'([^']+)'",
            r'키워드\s*[:：]\s*(\S+)',
            r'검색어\s*[:：]\s*(\S+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def fill_template_placeholders(self, sql_template: str, parameters: Dict[str, Any]) -> str:
        """SQL 템플릿의 placeholder를 실제 값으로 채우기"""
        filled_sql = sql_template
        
        # :param 스타일 placeholder 처리
        for param_name, param_value in parameters.items():
            placeholder = f":{param_name}"
            
            if placeholder in filled_sql:
                if isinstance(param_value, str):
                    filled_sql = filled_sql.replace(placeholder, f"'{param_value}'")
                elif isinstance(param_value, datetime):
                    filled_sql = filled_sql.replace(placeholder, f"'{param_value.strftime('%Y-%m-%d')}'")
                elif isinstance(param_value, dict) and 'start' in param_value:
                    # date_range 처리
                    if ':start_date' in filled_sql:
                        filled_sql = filled_sql.replace(':start_date', f"'{param_value['start'].strftime('%Y-%m-%d')}'")
                    if ':end_date' in filled_sql:
                        filled_sql = filled_sql.replace(':end_date', f"'{param_value['end'].strftime('%Y-%m-%d')}'")
                else:
                    filled_sql = filled_sql.replace(placeholder, str(param_value))
        
        # {param} 스타일 placeholder 처리
        for param_name, param_value in parameters.items():
            placeholder = f"{{{param_name}}}"
            
            if placeholder in filled_sql:
                if isinstance(param_value, str):
                    filled_sql = filled_sql.replace(placeholder, f"'{param_value}'")
                else:
                    filled_sql = filled_sql.replace(placeholder, str(param_value))
        
        return filled_sql
    
    def _extract_organization_text(self, query: str, org_code: str) -> Optional[str]:
        """쿼리에서 조직명 원본 텍스트 추출"""
        # 동의어 사전에서 해당 조직의 모든 동의어 가져오기
        org_synonyms = self.synonym_service.organization_synonyms.get(org_code, [])
        
        # 쿼리에서 매칭되는 동의어 찾기
        query_lower = query.lower()
        for synonym in org_synonyms:
            if synonym.lower() in query_lower:
                # 대소문자 구분 없이 찾고, 원본 케이스 반환
                pattern = re.compile(re.escape(synonym), re.IGNORECASE)
                match = pattern.search(query)
                if match:
                    return match.group(0)
        
        return None