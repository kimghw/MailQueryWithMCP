import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import time

from infra.core.logger import get_logger
from modules.mail_process.mail_processor_schema import (
    ProcessedMailData,
    ProcessingStatus,
    GraphMailItem,
)
from .queue_service import get_queue_service
from .processing_service import ProcessingService
from .persistence_service import PersistenceService
from .event_service import MailEventService


class MailQueueProcessor: