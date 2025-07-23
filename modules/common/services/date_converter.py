"""
Date Converter Service
시간 표현을 실제 날짜로 변환하는 서비스
"""

import re
from datetime import datetime, timedelta, date
from typing import Dict, Optional, Tuple, Union
import logging

logger = logging.getLogger(__name__)


class DateConverter:
    """시간 표현을 날짜로 변환하는 서비스"""
    
    def __init__(self):
        # 상대적 시간 표현 매핑
        self.relative_mappings = {
            # 오늘/어제
            '오늘': 0,
            '금일': 0,
            '당일': 0,
            'today': 0,
            '어제': -1,
            '전일': -1,
            'yesterday': -1,
            '내일': 1,
            '명일': 1,
            '익일': 1,
            'tomorrow': 1,
            
            # 주 단위
            '이번주': ('week', 0),
            '금주': ('week', 0),
            'this_week': ('week', 0),
            '지난주': ('week', -1),
            '전주': ('week', -1),
            'last_week': ('week', -1),
            '다음주': ('week', 1),
            '내주': ('week', 1),
            'next_week': ('week', 1),
            
            # 월 단위
            '이번달': ('month', 0),
            '금월': ('month', 0),
            '당월': ('month', 0),
            'this_month': ('month', 0),
            '지난달': ('month', -1),
            '전월': ('month', -1),
            'last_month': ('month', -1),
            '다음달': ('month', 1),
            '내월': ('month', 1),
            'next_month': ('month', 1),
            
            # 년 단위
            '올해': ('year', 0),
            '금년': ('year', 0),
            'this_year': ('year', 0),
            '작년': ('year', -1),
            '전년': ('year', -1),
            'last_year': ('year', -1),
            '내년': ('year', 1),
            '명년': ('year', 1),
            'next_year': ('year', 1),
            
            # 기타
            '최근': -7,  # 기본 7일
            'recent': -7,
            '최신': -7,
            'latest': -7,
        }
        
    def convert_to_date(self, time_expression: str, base_date: Optional[datetime] = None) -> Optional[Union[date, Tuple[date, date]]]:
        """
        시간 표현을 날짜로 변환
        
        Args:
            time_expression: 변환할 시간 표현
            base_date: 기준 날짜 (기본값: 현재)
            
        Returns:
            date: 특정 날짜
            Tuple[date, date]: 기간인 경우 (시작일, 종료일)
            None: 변환 실패
        """
        if not base_date:
            base_date = datetime.now()
        
        time_expr = time_expression.strip().lower()
        
        # 1. 직접 매핑 확인
        if time_expr in self.relative_mappings:
            mapping = self.relative_mappings[time_expr]
            
            if isinstance(mapping, int):
                # 일 단위
                result_date = base_date + timedelta(days=mapping)
                return result_date.date()
            
            elif isinstance(mapping, tuple):
                # 주/월/년 단위
                unit, offset = mapping
                return self._calculate_period(base_date, unit, offset)
        
        # 2. 패턴 매칭
        # N일 전/후
        days_pattern = r'(\d+)\s*일\s*(전|후|뒤)'
        match = re.search(days_pattern, time_expr)
        if match:
            days = int(match.group(1))
            if match.group(2) == '전':
                days = -days
            result_date = base_date + timedelta(days=days)
            return result_date.date()
        
        # N주 전/후
        weeks_pattern = r'(\d+)\s*주\s*(전|후|뒤)'
        match = re.search(weeks_pattern, time_expr)
        if match:
            weeks = int(match.group(1))
            if match.group(2) == '전':
                weeks = -weeks
            result_date = base_date + timedelta(weeks=weeks)
            return result_date.date()
        
        # N개월 전/후
        months_pattern = r'(\d+)\s*개월\s*(전|후|뒤)'
        match = re.search(months_pattern, time_expr)
        if match:
            months = int(match.group(1))
            if match.group(2) == '전':
                months = -months
            return self._add_months(base_date, months).date()
        
        # 최근 N일
        recent_pattern = r'최근\s*(\d+)\s*일'
        match = re.search(recent_pattern, time_expr)
        if match:
            days = int(match.group(1))
            end_date = base_date.date()
            start_date = (base_date - timedelta(days=days)).date()
            return (start_date, end_date)
        
        # 절대 날짜 (YYYY-MM-DD, YYYY.MM.DD, YYYY/MM/DD)
        date_pattern = r'(\d{4})[-./](\d{1,2})[-./](\d{1,2})'
        match = re.search(date_pattern, time_expr)
        if match:
            try:
                year = int(match.group(1))
                month = int(match.group(2))
                day = int(match.group(3))
                return date(year, month, day)
            except ValueError:
                logger.warning(f"Invalid date: {time_expr}")
                return None
        
        return None
    
    def convert_to_date_range(self, time_expression: str, base_date: Optional[datetime] = None) -> Optional[Tuple[datetime, datetime]]:
        """
        시간 표현을 날짜 범위로 변환 (시간 포함)
        
        Returns:
            Tuple[datetime, datetime]: (시작일시, 종료일시)
        """
        if not base_date:
            base_date = datetime.now()
        
        result = self.convert_to_date(time_expression, base_date)
        
        if not result:
            return None
        
        if isinstance(result, tuple):
            # 이미 범위인 경우
            start_date, end_date = result
            return (
                datetime.combine(start_date, datetime.min.time()),
                datetime.combine(end_date, datetime.max.time())
            )
        else:
            # 단일 날짜인 경우
            return (
                datetime.combine(result, datetime.min.time()),
                datetime.combine(result, datetime.max.time())
            )
    
    def _calculate_period(self, base_date: datetime, unit: str, offset: int) -> Tuple[date, date]:
        """주/월/년 단위 기간 계산"""
        if unit == 'week':
            # 주의 시작은 월요일
            days_since_monday = base_date.weekday()
            week_start = base_date - timedelta(days=days_since_monday)
            week_start += timedelta(weeks=offset)
            week_end = week_start + timedelta(days=6)
            return (week_start.date(), week_end.date())
        
        elif unit == 'month':
            # 월의 시작과 끝
            target_date = self._add_months(base_date, offset)
            month_start = target_date.replace(day=1)
            
            # 다음 달 1일에서 하루 빼면 이번 달 마지막 날
            if target_date.month == 12:
                month_end = target_date.replace(year=target_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = target_date.replace(month=target_date.month + 1, day=1) - timedelta(days=1)
            
            return (month_start.date(), month_end.date())
        
        elif unit == 'year':
            # 년의 시작과 끝
            target_year = base_date.year + offset
            year_start = date(target_year, 1, 1)
            year_end = date(target_year, 12, 31)
            return (year_start, year_end)
        
        return None
    
    def _add_months(self, base_date: datetime, months: int) -> datetime:
        """월 단위 날짜 계산"""
        month = base_date.month + months
        year = base_date.year
        
        while month > 12:
            month -= 12
            year += 1
        
        while month < 1:
            month += 12
            year -= 1
        
        # 마지막 날 처리 (예: 1월 31일 + 1개월 = 2월 28/29일)
        try:
            return base_date.replace(year=year, month=month)
        except ValueError:
            # 해당 월의 마지막 날로 조정
            if month == 2:
                # 윤년 체크
                if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
                    day = 29
                else:
                    day = 28
            elif month in [4, 6, 9, 11]:
                day = 30
            else:
                day = 31
            
            return base_date.replace(year=year, month=month, day=day)
    
    def format_date_for_sql(self, date_value: Union[date, datetime]) -> str:
        """SQL 쿼리용 날짜 포맷"""
        if isinstance(date_value, datetime):
            return date_value.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return date_value.strftime('%Y-%m-%d')