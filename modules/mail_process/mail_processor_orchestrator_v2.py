import time
from datetime import datetime
from typing import Dict, Optional, List
import asyncio

from infra.core.logger import get_logger
from modules.mail_query import (
    MailQueryOrchestrator,
    MailQueryRequest,
    MailQueryFilters,
    PaginationOptions,
)
from .mail_processor_schema import MailProcessingResult
from .services.db_service import MailDatabaseService
from .services.filtering_service import FilteringService
from .services.statistics_service import StatisticsService
from .services.queue_service import get_queue_service
from .services.queue_processor import get_queue_processor

logger = get_logger(__name__)


class MailProcessorOrchestratorV2: