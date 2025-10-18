#!/usr/bin/env python3
"""101~150번째 메일 구간에서 문제 있는 메일 찾기"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.mail_query.graph_api_client import GraphAPIClient
from infra.core.token_service import TokenService
from infra.core.logger import get_logger

logger = get_logger(__name__)


async def test_skip_range():
    """101~150 구간을 10개씩 테스트"""

    # 토큰 가져오기
    token_service = TokenService()
    access_token = await token_service.get_valid_access_token("kimghw")

    client = GraphAPIClient()

    # 날짜 필터
    odata_filter = "receivedDateTime ge 2025-08-31T15:00:00.000Z and receivedDateTime le 2025-10-18T00:14:02.000Z"
    select_fields = "id,subject,from,receivedDateTime,hasAttachments,attachments"

    # 101~150 구간을 10개씩 나눠서 테스트
    for skip in range(100, 150, 10):
        logger.info(f"\n{'='*80}")
        logger.info(f"Testing skip={skip}, top=10 (메일 {skip+1}~{skip+10}번째)")
        logger.info(f"{'='*80}")

        try:
            result = await client.query_messages_single_page(
                access_token=access_token,
                odata_filter=odata_filter,
                select_fields=select_fields,
                top=10,
                skip=skip,
                orderby="receivedDateTime desc"
            )

            logger.info(f"✅ Success: {len(result['messages'])} messages retrieved")

            # 각 메일의 첨부파일 개수 확인
            for i, msg in enumerate(result['messages']):
                attachment_count = len(msg.attachments) if msg.attachments else 0
                logger.info(f"   [{skip+i+1}] {msg.subject[:50]:50} | Attachments: {attachment_count}")

        except Exception as e:
            logger.error(f"❌ Failed at skip={skip}: {type(e).__name__}: {str(e)[:200]}")
            logger.error(f"   Problem is likely in emails {skip+1}~{skip+10}")

            # 더 세밀하게 1개씩 테스트
            logger.info(f"\n   🔍 Testing individual emails in this range...")
            for individual_skip in range(skip, skip+10):
                try:
                    result = await client.query_messages_single_page(
                        access_token=access_token,
                        odata_filter=odata_filter,
                        select_fields=select_fields,
                        top=1,
                        skip=individual_skip,
                        orderby="receivedDateTime desc"
                    )
                    if result['messages']:
                        msg = result['messages'][0]
                        attachment_count = len(msg.attachments) if msg.attachments else 0
                        logger.info(f"      ✅ [{individual_skip+1}] {msg.subject[:40]} | Att: {attachment_count}")
                except Exception as e2:
                    logger.error(f"      ❌ [{individual_skip+1}] FAILED: {type(e2).__name__}")

            break

        await asyncio.sleep(1)  # API rate limit 방지


if __name__ == "__main__":
    asyncio.run(test_skip_range())
