"""
Synonym Service Module
동의어/유사어 처리 서비스 - DB 기반 및 하드코딩 동의어 관리
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SynonymService:
    """동의어/유사어 처리 서비스"""
    
    def __init__(self, preprocessing_repo=None):
        self.preprocessing_repo = preprocessing_repo
        self._synonym_cache = {}
        self._last_cache_update = None
        self._cache_ttl = 300  # 5분
        
        # 하드코딩된 동의어 (빠른 접근용)
        self.default_synonyms = {
            # 아젠다 관련
            '아젠다': 'agenda',
            '안건': 'agenda',
            '의제': 'agenda',
            '어젠다': 'agenda',
            '아젠더': 'agenda',
            '의안': 'agenda',
            '협의사항': 'agenda',
            '논의사항': 'agenda',
            
            # 응답 관련
            '응답': 'response',
            '답변': 'response',
            '회신': 'response',
            '의견': 'response',
            '코멘트': 'response',
            '회답': 'response',
            '답신': 'response',
            '리플': 'response',
            '리플라이': 'response',
            'reply': 'response',
            
            # 조직/기관 관련
            '기관': 'organization',
            '부서': 'organization',
            '조직': 'organization',
            '선급': 'class_society',
            '단체': 'organization',
            '회사': 'organization',
            '업체': 'organization',
            '소속': 'organization',
            
            # 상태 관련
            '승인': 'approved',
            '허가': 'approved',
            '수락': 'approved',
            '통과': 'approved',
            '가결': 'approved',
            '인정': 'approved',
            '반려': 'rejected',
            '거부': 'rejected',
            '거절': 'rejected',
            '부결': 'rejected',
            '불가': 'rejected',
            '기각': 'rejected',
            '미결정': 'pending',
            '대기': 'pending',
            '보류': 'pending',
            '미처리': 'pending',
            '진행중': 'pending',
            '진행 중': 'pending',
            '진행중인': 'pending',
            '검토중': 'pending',
            '처리중': 'pending',
            '미완료': 'pending',
            
            # 시간 표현
            '최근': 'recent',
            '최신': 'latest',
            '오늘': 'today',
            '어제': 'yesterday',
            '금일': 'today',
            '당일': 'today',
            '전일': 'yesterday',
            '작일': 'yesterday',
            '익일': 'tomorrow',
            '내일': 'tomorrow',
            '명일': 'tomorrow',
            '이번주': 'this_week',
            '지난주': 'last_week',
            '금주': 'this_week',
            '이번달': 'this_month',
            '지난달': 'last_month',
            '금월': 'this_month',
            '당월': 'this_month',
            '전월': 'last_month',
            '올해': 'this_year',
            '작년': 'last_year',
            
            # 동작 관련
            '조회': 'search',
            '검색': 'search',
            '찾기': 'search',
            '보기': 'view',
            '확인': 'view',
            '열람': 'view',
            '분석': 'analyze',
            '통계': 'statistics',
            '집계': 'statistics',
            '요약': 'summary',
            '정리': 'summary',
            
            # 문서 타입
            '제안': 'proposal',
            '제안서': 'proposal',
            '보고서': 'report',
            '리포트': 'report',
            '회의록': 'minutes',
            '의사록': 'minutes',
            '메일': 'mail',
            '이메일': 'mail',
            'email': 'mail',
            '편지': 'mail',
            
            # 마감/기한 관련
            '마감': 'deadline',
            '기한': 'deadline',
            '마감일': 'deadline',
            
            # 긴급도 관련
            '임박': 'urgent',
            '긴급': 'urgent',
            '시급': 'urgent'
        }
        
        # 선급/기관 동의어 사전
        self.organization_synonyms = {
            # ABS (American Bureau of Shipping)
            'ABS': [
                'ABS', 'abs', 'Abs', 'A.B.S',
                '미국선급', '미국선급협회', '미선', '미국선급회',
                'American Bureau of Shipping', 'American Bureau', 'AmericanBureau',
                '아메리칸뷰로', '아메리칸 뷰로', '아메리칸뷰로오브쉬핑',
                '에이비에스', '에이.비.에스'
            ],
            
            # KR (Korean Register)
            'KR': [
                'KR', 'kr', 'Kr', 'K.R',
                '한국선급', '한국선급협회', '한선', '한국선급회', '한국',
                'Korean Register', 'Korean Register of Shipping', 'KoreanRegister',
                'Korea Register', 'KRS', 'krs',
                '케이알', '케이.알', '한국레지스터'
            ],
            
            # LR (Lloyd's Register)
            'LR': [
                'LR', 'lr', 'Lr', 'L.R',
                '로이드선급', '로이드', '로이드선급협회', '영국선급', '로이드선급회',
                "Lloyd's Register", 'Lloyds Register', 'Lloyd Register', 
                'Lloyds', 'Lloyd', 'LloydRegister',
                '엘알', '엘.알', '로이드레지스터'
            ],
            
            # DNV (Det Norske Veritas)
            'DNV': [
                'DNV', 'dnv', 'Dnv', 'D.N.V',
                'DNV GL', 'DNVGL', 'DNV-GL', 'dnvgl', 'DnvGl',
                '노르웨이선급', '노르웨이선급협회', '노선', '노르웨이선급회',
                'Det Norske Veritas', 'DetNorskeVeritas', 'GL',
                '디엔브이', '디엔브이지엘', '디.엔.브이'
            ],
            
            # BV (Bureau Veritas)
            'BV': [
                'BV', 'bv', 'Bv', 'B.V',
                '프랑스선급', '프랑스선급협회', '프선', '불란서선급', '프랑스선급회',
                'Bureau Veritas', 'BureauVeritas', 'Bureau',
                '뷰로베리타스', '뷰로 베리타스', '뷰로',
                '비브이', '비.브이', '뷰로베리따스'
            ],
            
            # NK (Nippon Kaiji Kyokai)
            'NK': [
                'NK', 'nk', 'Nk', 'N.K',
                'ClassNK', 'Class NK', 'classNK', 'classnk',
                '일본선급', '일본선급협회', '일선', '일본해사협회', '일본선급회',
                'Nippon Kaiji Kyokai', 'NKK', 'nkk', 'Nippon Kaiji',
                'Japan Classification', 'JCS',
                '엔케이', '엔.케이', '니뽄까이지쿄카이', '클래스엔케이'
            ],
            
            # CCS (China Classification Society)
            'CCS': [
                'CCS', 'ccs', 'Ccs', 'C.C.S',
                '중국선급', '중국선급사', '중선', '중국선급협회', '중국선급회',
                'China Classification Society', 'ChinaClassification',
                'China Class', 'ChinaClass',
                '씨씨에스', '씨.씨.에스', '차이나클래스'
            ],
            
            # RINA (Registro Italiano Navale)
            'RINA': [
                'RINA', 'rina', 'Rina', 'R.I.N.A',
                '이탈리아선급', '이탈리아선급협회', '이선', '이태리선급', '이탈리아선급회',
                'Registro Italiano Navale', 'RegistroItalianoNavale',
                'Italian Register', 'Italy Class',
                '리나', '리.나', '레지스트로이탈리아노나발레'
            ],
            
            # IRS (Indian Register of Shipping)
            'IRS': [
                'IRS', 'irs', 'Irs', 'I.R.S',
                '인도선급', '인도선급협회', '인선', '인도선급회',
                'Indian Register of Shipping', 'IndianRegister',
                'India Register', 'India Class',
                '아이알에스', '아이.알.에스', '인디안레지스터'
            ],
            
            # PRS (Polski Rejestr Statków)
            'PRS': [
                'PRS', 'prs', 'Prs', 'P.R.S',
                '폴란드선급', '폴란드선급협회', '폴선', '폴란드선급회',
                'Polski Rejestr Statków', 'Polski Rejestr', 'PolskiRejestr',
                'Polish Register', 'Poland Class',
                '피알에스', '피.알.에스', '폴스키레예스트르'
            ],
            
            # CRS (Croatian Register of Shipping)
            'CRS': [
                'CRS', 'crs', 'Crs', 'C.R.S',
                '크로아티아선급', '크로아티아선급협회', '크선', '크로아티아선급회',
                'Croatian Register of Shipping', 'CroatianRegister',
                'Croatia Register', 'Croatia Class',
                '씨알에스', '씨.알.에스', '크로아티안레지스터'
            ],
            
            # RS (Russian Maritime Register of Shipping)
            'RS': [
                'RS', 'rs', 'Rs', 'R.S',
                '러시아선급', '러시아선급협회', '러선', '러시아선급회',
                'Russian Maritime Register', 'Russian Register',
                'Russia Class', 'RMRS', 'rmrs',
                '알에스', '알.에스', '러시안레지스터'
            ],
            
            # TL (Türk Loydu)
            'TL': [
                'TL', 'tl', 'Tl', 'T.L',
                '터키선급', '터키선급협회', '터선', '터키선급회', '투르크선급',
                'Türk Loydu', 'Turk Loydu', 'Turkish Lloyd',
                'Turkey Class', 'Turkish Register',
                '티엘', '티.엘', '튀르크로이두'
            ],
            
            # VL (Vietnam Register)
            'VL': [
                'VL', 'vl', 'Vl', 'V.L',
                '베트남선급', '베트남선급협회', '베선', '베트남선급회', '월남선급',
                'Vietnam Register', 'VietnamRegister', 'VR',
                'Vietnam Class', 'Vietnamese Register',
                '브이엘', '브이.엘', '베트남레지스터'
            ],
            
            # IACS
            'IACS': [
                'IACS', 'iacs', 'I.A.C.S',
                '국제선급연합회', '국제선급협회', '국제선급연합',
                'International Association of Classification Societies',
                'Classification Societies', 'IntlAssociation',
                '아이에이씨에스', '아이.에이.씨.에스'
            ]
        }
    
    def normalize_text(self, text: str, use_db: bool = True) -> str:
        """
        텍스트 정규화 (동의어 치환)
        
        Args:
            text: 정규화할 텍스트
            use_db: DB 기반 동의어 사용 여부
            
        Returns:
            정규화된 텍스트
        """
        normalized = text
        
        # DB 기반 동의어 처리
        if use_db and self.preprocessing_repo:
            try:
                self._update_cache_if_needed()
                
                # 캐시된 동의어 사용
                sorted_synonyms = sorted(
                    self._synonym_cache.items(), 
                    key=lambda x: len(x[0]), 
                    reverse=True
                )
                
                for original, normalized_term in sorted_synonyms:
                    pattern = rf'\b{re.escape(original)}\b'
                    normalized = re.sub(pattern, normalized_term, normalized, flags=re.IGNORECASE)
            except Exception as e:
                logger.warning(f"DB 동의어 처리 실패: {e}")
        
        # 기본 동의어 처리
        sorted_defaults = sorted(
            self.default_synonyms.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )
        
        for original, normalized_term in sorted_defaults:
            pattern = rf'\b{re.escape(original)}\b'
            normalized = re.sub(pattern, normalized_term, normalized, flags=re.IGNORECASE)
        
        # 기관명 정규화
        for org_code, synonyms in self.organization_synonyms.items():
            for synonym in synonyms:
                if synonym != org_code:  # 코드 자체는 변경하지 않음
                    pattern = rf'\b{re.escape(synonym)}\b'
                    normalized = re.sub(pattern, org_code, normalized, flags=re.IGNORECASE)
        
        return normalized
    
    def get_synonyms_for_term(self, term: str) -> List[str]:
        """특정 용어의 모든 동의어 가져오기"""
        synonyms = []
        term_lower = term.lower()
        
        # 정규화된 형태 찾기
        normalized = None
        
        # 기본 동의어에서 찾기
        if term_lower in self.default_synonyms:
            normalized = self.default_synonyms[term_lower]
        
        # DB에서 찾기
        if self.preprocessing_repo:
            self._update_cache_if_needed()
            if term_lower in self._synonym_cache:
                normalized = self._synonym_cache[term_lower]
        
        if not normalized:
            return []
        
        # 같은 정규화 형태를 가진 모든 용어 찾기
        # 기본 동의어에서
        for original, norm in self.default_synonyms.items():
            if norm == normalized and original != term_lower:
                synonyms.append(original)
        
        # DB 동의어에서
        if self._synonym_cache:
            for original, norm in self._synonym_cache.items():
                if norm == normalized and original != term_lower and original not in synonyms:
                    synonyms.append(original)
        
        # 기관명 동의어에서
        for org_code, org_synonyms in self.organization_synonyms.items():
            if term_lower in [s.lower() for s in org_synonyms]:
                # 해당 기관의 모든 동의어 추가 (입력 term 제외)
                for syn in org_synonyms:
                    if syn.lower() != term_lower and syn not in synonyms:
                        synonyms.append(syn)
                break
        
        return synonyms
    
    def expand_keywords(self, keywords: List[str]) -> List[str]:
        """키워드 목록을 동의어로 확장"""
        expanded = set(keywords)
        
        for keyword in keywords:
            # 동의어 추가
            synonyms = self.get_synonyms_for_term(keyword)
            expanded.update(synonyms)
            
            # 정규화된 형태도 추가
            normalized = self.normalize_text(keyword, use_db=False)
            if normalized != keyword:
                expanded.add(normalized)
        
        return list(expanded)
    
    def _update_cache_if_needed(self):
        """필요시 캐시 업데이트"""
        if not self.preprocessing_repo:
            return
            
        now = datetime.now()
        
        if (self._last_cache_update is None or 
            (now - self._last_cache_update).seconds > self._cache_ttl):
            
            try:
                # DB에서 모든 동의어 로드
                synonyms = self.preprocessing_repo.get_all_synonyms()
                
                # 캐시 재구성
                self._synonym_cache.clear()
                for synonym in synonyms:
                    original = synonym['original_term'].lower()
                    normalized = synonym['normalized_term']
                    self._synonym_cache[original] = normalized
                
                self._last_cache_update = now
                logger.debug(f"Updated synonym cache with {len(self._synonym_cache)} entries")
                
            except Exception as e:
                logger.error(f"Failed to update synonym cache: {e}")
    
    def get_all_synonyms(self) -> Dict[str, str]:
        """모든 동의어 반환 (기본 + DB)"""
        all_synonyms = self.default_synonyms.copy()
        
        if self._synonym_cache:
            all_synonyms.update(self._synonym_cache)
        
        return all_synonyms
    
    def get_organization_code(self, text: str) -> Optional[str]:
        """텍스트에서 기관 코드 추출 (동의어 매칭)"""
        text_lower = text.lower()
        
        for org_code, synonyms in self.organization_synonyms.items():
            for synonym in synonyms:
                if synonym.lower() in text_lower:
                    return org_code
        
        return None
    
    def is_organization(self, text: str) -> bool:
        """텍스트가 기관명인지 확인"""
        return self.get_organization_code(text) is not None