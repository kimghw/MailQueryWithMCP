import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import deque
import os

from infra.core.logger import get_logger
from infra.core.database import get_database_manager
from modules.mail_process.mail_processor_schema import GraphMailItem
from modules.mail_process.utilities.text_cleaner import TextCleaner
from .db_service import MailDatabaseService


class MailQueueService: