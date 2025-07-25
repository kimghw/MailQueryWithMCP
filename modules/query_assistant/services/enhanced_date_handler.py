"""
Enhanced Date Handler for LLM-extracted date parameters
Ensures all date-related templates use LLM-provided dates with 30-day default
"""
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class EnhancedDateHandler:
    """Handle date parameters from LLM and apply defaults"""
    
    DEFAULT_DAYS = 30  # Default to 30 days if no date provided
    
    @staticmethod
    def process_date_parameters(
        template_params: Dict[str, Any],
        llm_extracted_dates: Optional[Dict[str, str]] = None,
        user_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process date parameters with priority:
        1. LLM-extracted dates (highest priority)
        2. User-provided parameters
        3. Template defaults
        4. System default (30 days)
        
        Args:
            template_params: Parameters defined in template
            llm_extracted_dates: Dates extracted by LLM (e.g., {'start': '2024-01-01', 'end': '2024-01-31'})
            user_params: User-provided parameters
            
        Returns:
            Processed parameters with date values
        """
        processed_params = user_params.copy() if user_params else {}
        
        # Check if template has date-related parameters
        has_date_param = any(
            param.get('type') == 'date_range' or param.get('name') in ['date_range', 'days', 'period']
            for param in template_params
        )
        
        if not has_date_param:
            return processed_params
        
        # Process LLM-extracted dates if available
        if llm_extracted_dates:
            logger.info(f"Processing LLM-extracted dates: {llm_extracted_dates}")
            
            # Convert LLM dates to appropriate format
            if 'start' in llm_extracted_dates and 'end' in llm_extracted_dates:
                # Date range provided
                processed_params['date_range'] = {
                    'type': 'range',
                    'from': llm_extracted_dates['start'],
                    'to': llm_extracted_dates['end']
                }
            elif 'date' in llm_extracted_dates:
                # Single date provided - create range from that date to today
                processed_params['date_range'] = {
                    'type': 'range',
                    'from': llm_extracted_dates['date'],
                    'to': datetime.now().strftime('%Y-%m-%d')
                }
            elif 'days' in llm_extracted_dates:
                # Relative days provided
                try:
                    days = int(llm_extracted_dates['days'])
                    processed_params['date_range'] = {
                        'type': 'relative',
                        'days': days
                    }
                except ValueError:
                    logger.warning(f"Invalid days value from LLM: {llm_extracted_dates['days']}")
        
        # Apply defaults if no date parameter is set
        if 'date_range' not in processed_params and 'days' not in processed_params:
            # Look for template default
            template_default = None
            for param in template_params:
                if param.get('name') == 'date_range' and 'default' in param:
                    template_default = param['default']
                    break
            
            if template_default:
                processed_params['date_range'] = template_default
            else:
                # Use system default (30 days)
                processed_params['date_range'] = {
                    'type': 'relative',
                    'days': EnhancedDateHandler.DEFAULT_DAYS
                }
                logger.info(f"Applied system default: {EnhancedDateHandler.DEFAULT_DAYS} days")
        
        return processed_params
    
    @staticmethod
    def extract_date_keywords(query: str) -> Dict[str, Any]:
        """
        Extract date-related keywords from query for better template matching
        
        Returns:
            Dictionary with extracted date information
        """
        date_keywords = {
            'has_date_keyword': False,
            'keywords': [],
            'estimated_days': None
        }
        
        # Date keyword mappings
        keyword_mappings = {
            '오늘': (0, 'today'),
            '어제': (1, 'yesterday'),
            '최근': (7, 'recent'),
            '이번주': (7, 'this_week'),
            '지난주': (14, 'last_week'),
            '이번달': (30, 'this_month'),
            '지난달': (60, 'last_month'),
            '3개월': (90, 'three_months'),
            '올해': (365, 'this_year'),
            '작년': (730, 'last_year'),
        }
        
        query_lower = query.lower()
        for korean, (days, english) in keyword_mappings.items():
            if korean in query_lower:
                date_keywords['has_date_keyword'] = True
                date_keywords['keywords'].append(english)
                if date_keywords['estimated_days'] is None:
                    date_keywords['estimated_days'] = days
        
        return date_keywords
    
    @staticmethod
    def validate_date_format(date_str: str) -> Tuple[bool, Optional[str]]:
        """
        Validate and normalize date format
        
        Args:
            date_str: Date string to validate
            
        Returns:
            Tuple of (is_valid, normalized_date)
        """
        date_formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%Y.%m.%d',
            '%Y년 %m월 %d일',
            '%Y%m%d'
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str.strip(), fmt)
                return True, parsed_date.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return False, None


# Example usage
if __name__ == "__main__":
    # Test LLM date extraction
    handler = EnhancedDateHandler()
    
    # Template parameters
    template_params = [
        {
            "name": "date_range",
            "type": "date_range",
            "required": False,
            "default": {"type": "relative", "days": 90}
        }
    ]
    
    # Test cases
    test_cases = [
        # LLM extracted specific dates
        {
            "llm_dates": {"start": "2024-01-01", "end": "2024-01-31"},
            "user_params": {}
        },
        # LLM extracted relative days
        {
            "llm_dates": {"days": "7"},
            "user_params": {}
        },
        # No LLM dates, should use default
        {
            "llm_dates": None,
            "user_params": {}
        }
    ]
    
    for i, test in enumerate(test_cases):
        print(f"\nTest case {i+1}:")
        result = handler.process_date_parameters(
            template_params,
            test["llm_dates"],
            test["user_params"]
        )
        print(f"Result: {result}")