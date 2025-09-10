"""Mail Data Refresher for automatic database updates"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from infra.core.database import get_database_manager
from modules.account import AccountOrchestrator
from modules.mail_query import MailQueryOrchestrator, MailQueryRequest
from modules.mail_process import MailProcessorOrchestrator
from modules.mail_dashboard import EmailDashboardOrchestrator
from infra.core.kafka_client import get_kafka_client

logger = logging.getLogger(__name__)


class MailDataRefresher:
    """자동으로 메일 데이터를 조회하고 SQLite DB에 저장하는 클래스"""
    
    def __init__(self):
        self.db_manager = get_database_manager()
        self.account_orchestrator = AccountOrchestrator()
        self.mail_query_orchestrator = MailQueryOrchestrator()
        self.mail_processor = MailProcessorOrchestrator()
        self.dashboard_orchestrator = EmailDashboardOrchestrator()
        self.kafka_client = get_kafka_client()
        logger.info("📧 MailDataRefresher initialized")
        
    async def get_last_mail_date(self, user_id: str) -> Optional[datetime]:
        """agenda_all에서 마지막 메일 수신 시간 조회"""
        try:
            query = """
            SELECT MAX(sent_time) as last_received
            FROM agenda_all
            """
            
            # Use synchronous database call - no parameters needed
            result = self.db_manager.fetch_one(query)
            
            if result and result[0]:
                # ISO format string to datetime
                if isinstance(result[0], str):
                    return datetime.fromisoformat(result[0].replace('Z', '+00:00'))
                return result[0]
            
            # 데이터가 없으면 30일 전부터
            return datetime.now() - timedelta(days=30)
            
        except Exception as e:
            logger.error(f"Error getting last mail date: {e}")
            return datetime.now() - timedelta(days=30)
    
    async def refresh_mail_data_for_user(
        self, 
        user_id: str = "krsdtp",
        max_mails: int = 1000,
        use_last_date: bool = True
    ) -> Dict[str, Any]:
        """특정 사용자의 메일 데이터 최신화"""
        logger.info(f"🔄 Starting mail data refresh for user: {user_id}")
        
        try:
            # 1. 계정 정보 가져오기
            account = self.account_orchestrator.account_get_by_user_id(user_id)
            if not account:
                raise ValueError(f"Account not found for user_id: {user_id}")
            
            if not account.is_active:
                raise ValueError(f"Account is not active: {user_id}")
            
            # 2. 시작 날짜 결정
            if use_last_date:
                start_date = await self.get_last_mail_date(user_id)
                if start_date:
                    logger.info(f"📅 Using last mail date from agenda_all: {start_date}")
                else:
                    logger.info(f"📅 No previous mail found, using 30 days back")
                    start_date = datetime.now() - timedelta(days=30)
            else:
                start_date = datetime.now() - timedelta(days=30)
                
            # 날짜 계산 - timezone aware 처리
            from datetime import timezone
            
            # 항상 timezone aware datetime 사용
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            
            # 현재 시간도 UTC로
            now = datetime.now(timezone.utc)
                
            days_back = (now - start_date).days
            if days_back < 1:
                days_back = 1
                
            logger.info(f"📊 Query parameters: days_back={days_back}, max_mails={max_mails}")
            
            # 3. 메일 조회 - 날짜 필터 추가
            from modules.mail_query.mail_query_schema import MailQueryFilters, PaginationOptions
            
            # 날짜 필터 생성
            filters = MailQueryFilters(
                date_from=start_date,  # 마지막 수신 날짜부터
                date_to=now  # 현재까지
            )
            
            # 페이징 옵션
            pagination = PaginationOptions(
                top=50,  # 한 번에 50개씩
                max_pages=max_mails // 50 if max_mails > 50 else 1  # 최대 페이지 수 계산
            )
            
            query_request = MailQueryRequest(
                user_id=user_id,
                filters=filters,
                pagination=pagination
            )
            
            logger.info(f"🔍 Querying emails for {user_id}...")
            logger.info(f"📅 Date filter: {start_date.strftime('%Y-%m-%d %H:%M:%S')} to {now.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"📊 Filter object: date_from={filters.date_from}, date_to={filters.date_to}")
            logger.info(f"📄 Pagination: top={pagination.top}, max_pages={pagination.max_pages}")
            query_response = await self.mail_query_orchestrator.mail_query_user_emails(query_request)
            
            mail_count = len(query_response.messages) if query_response.messages else 0
            logger.info(f"📬 Found {mail_count} emails")
            
            # 4. 메일 처리 및 DB 저장
            processed_count = 0
            if query_response.messages:
                logger.info(f"💾 Processing and saving emails to database...")
                
                # 배치로 처리
                await self.mail_processor.enqueue_mail_batch(
                    account.id, 
                    query_response.messages
                )
                
                # 처리 실행
                process_result = await self.mail_processor.process_batch()
                
                # process_result가 dict인지 확인
                if isinstance(process_result, dict):
                    processed_count = process_result.get('processed_count', 0)
                elif isinstance(process_result, list):
                    processed_count = len(process_result)
                else:
                    processed_count = 0
                
                logger.info(f"✅ Processed {processed_count} emails")
            
            # 5. 이벤트 수집 및 agenda_chair 저장
            events_processed = 0
            if processed_count > 0:
                logger.info(f"📨 Collecting events from Kafka and saving to agenda_chair...")
                events_result = await self.collect_and_save_events(
                    max_events=processed_count * 2,  # 여유있게 설정
                    timeout_seconds=30
                )
                events_processed = events_result.get('processed_count', 0)
                logger.info(f"✅ Processed {events_processed} events to agenda_chair")
            
            return {
                "status": "success",
                "user_id": user_id,
                "start_date": start_date.isoformat(),
                "end_date": datetime.now().isoformat(),
                "days_back": days_back,
                "mail_count": mail_count,
                "processed_count": processed_count,
                "events_processed": events_processed,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error refreshing mail data for {user_id}: {e}")
            return {
                "status": "failed",
                "user_id": user_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def collect_and_save_events(
        self, 
        max_events: int = 1000,
        timeout_seconds: int = 30,
        topic: str = "email.received",
        consumer_group: str = "mcp-mail-refresher"
    ) -> Dict[str, Any]:
        """Kafka에서 이벤트를 수집하여 agenda_chair 테이블에 저장"""
        try:
            import json
            from kafka import KafkaConsumer
            
            logger.info(f"🔄 Starting event collection from Kafka topic: {topic}")
            
            # Kafka consumer 설정
            consumer_config = {
                "bootstrap_servers": "localhost:9092",
                "group_id": consumer_group,
                "auto_offset_reset": "earliest",
                "enable_auto_commit": True,
                "consumer_timeout_ms": timeout_seconds * 1000,
                "max_poll_records": max_events,
                "value_deserializer": lambda x: (
                    json.loads(x.decode("utf-8")) if x else None
                ),
            }
            
            consumer = KafkaConsumer(topic, **consumer_config)
            
            collected_events = []
            processed_count = 0
            chair_events = 0
            member_events = 0
            
            # 이벤트 수집
            logger.info(f"📥 Collecting up to {max_events} events...")
            for message in consumer:
                try:
                    event_data = message.value
                    if event_data:
                        collected_events.append(event_data)
                        
                        # 이벤트 타입 확인
                        event_info = event_data.get("event_info", {})
                        sender_type = str(event_info.get("sender_type", "")).upper()
                        
                        if sender_type == "CHAIR":
                            chair_events += 1
                        elif sender_type == "MEMBER":
                            member_events += 1
                        
                        if len(collected_events) >= max_events:
                            break
                            
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    continue
            
            consumer.close()
            
            logger.info(f"📊 Collected {len(collected_events)} events (Chair: {chair_events}, Member: {member_events})")
            
            # 이벤트 처리 및 저장
            if collected_events:
                logger.info(f"💾 Processing events and saving to dashboard tables...")
                
                for event in collected_events:
                    try:
                        # EmailDashboardOrchestrator를 통해 이벤트 처리
                        result = self.dashboard_orchestrator.handle_email_event(event)
                        
                        if result.get("success"):
                            processed_count += 1
                        else:
                            logger.warning(f"Failed to process event: {result.get('message')}")
                            
                    except Exception as e:
                        logger.error(f"Error handling event: {e}")
                        continue
                
                logger.info(f"✅ Successfully processed {processed_count} events")
            
            return {
                "status": "success",
                "collected_count": len(collected_events),
                "processed_count": processed_count,
                "chair_events": chair_events,
                "member_events": member_events,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error collecting events: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "collected_count": 0,
                "processed_count": 0,
                "timestamp": datetime.now().isoformat()
            }
    
    async def refresh_all_active_accounts(
        self,
        max_mails_per_account: int = 100
    ) -> Dict[str, Any]:
        """모든 활성 계정의 메일 데이터 최신화"""
        logger.info("🔄 Starting mail data refresh for all active accounts")
        
        try:
            # 활성 계정 목록 가져오기 - 직접 DB 쿼리
            query = """
            SELECT id, user_id, user_name, email, is_active
            FROM accounts 
            WHERE is_active = 1
            ORDER BY user_id
            """
            
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()
                
            accounts = []
            for row in rows:
                accounts.append({
                    'id': row[0],
                    'user_id': row[1],
                    'user_name': row[2],
                    'email': row[3],
                    'is_active': row[4]
                })
            
            results = []
            total_mails = 0
            total_processed = 0
            
            for account in accounts:
                result = await self.refresh_mail_data_for_user(
                    user_id=account['user_id'],
                    max_mails=max_mails_per_account,
                    use_last_date=True
                )
                
                results.append(result)
                
                if result['status'] == 'success':
                    total_mails += result.get('mail_count', 0)
                    total_processed += result.get('processed_count', 0)
            
            return {
                "status": "completed",
                "total_accounts": len(accounts),
                "total_mails": total_mails,
                "total_processed": total_processed,
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error refreshing all accounts: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Test function
async def test_refresh():
    """Test mail data refresh"""
    refresher = MailDataRefresher()
    result = await refresher.refresh_mail_data_for_user("krsdtp", max_mails=10)
    print(f"Test result: {result}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run test
    asyncio.run(test_refresh())