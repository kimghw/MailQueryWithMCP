"""
JSON-RPC 요청/응답 로깅
모든 MCP 도구 호출을 데이터베이스에 저장
"""

import json
import time
import functools
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Callable
from pathlib import Path

from infra.core.logger import get_logger
from infra.core.database import get_database_manager

logger = get_logger(__name__)


class JSONRPCLogger:
    """JSON-RPC 요청/응답 로거"""

    def __init__(self):
        self.db = get_database_manager()
        self._initialize_table()

    def _initialize_table(self):
        """로깅 테이블 초기화"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS jsonrpc_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_id TEXT,
            tool_name TEXT NOT NULL,
            action TEXT,
            request_data TEXT NOT NULL,
            response_data TEXT,
            success BOOLEAN,
            error_message TEXT,
            execution_time_ms INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        create_index_sql = """
        CREATE INDEX IF NOT EXISTS idx_jsonrpc_logs_timestamp
        ON jsonrpc_logs(timestamp);

        CREATE INDEX IF NOT EXISTS idx_jsonrpc_logs_user_tool
        ON jsonrpc_logs(user_id, tool_name);

        CREATE INDEX IF NOT EXISTS idx_jsonrpc_logs_action
        ON jsonrpc_logs(action);
        """

        try:
            with self.db.get_connection() as conn:
                conn.execute(create_table_sql)
                conn.executescript(create_index_sql)
                conn.commit()
            logger.info("✅ JSON-RPC 로깅 테이블 초기화 완료")
        except Exception as e:
            logger.error(f"❌ JSON-RPC 로깅 테이블 초기화 실패: {str(e)}")

    def log_request(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        response: Any = None,
        success: bool = True,
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None
    ) -> int:
        """
        JSON-RPC 요청/응답 로깅

        Args:
            tool_name: 도구 이름
            arguments: 요청 파라미터
            response: 응답 데이터
            success: 성공 여부
            error_message: 에러 메시지
            execution_time_ms: 실행 시간 (밀리초)

        Returns:
            로그 ID
        """
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            user_id = arguments.get("user_id")
            action = arguments.get("action")

            # 요청 데이터 JSON 직렬화
            request_json = json.dumps(arguments, ensure_ascii=False)

            # 응답 데이터 직렬화
            response_json = None
            if response is not None:
                if isinstance(response, list):
                    # TextContent 리스트인 경우
                    response_json = json.dumps(
                        [{"type": r.type, "text": r.text} for r in response],
                        ensure_ascii=False
                    )
                elif isinstance(response, dict):
                    response_json = json.dumps(response, ensure_ascii=False)
                else:
                    response_json = str(response)

            insert_sql = """
            INSERT INTO jsonrpc_logs
            (timestamp, user_id, tool_name, action, request_data, response_data,
             success, error_message, execution_time_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            with self.db.get_connection() as conn:
                cursor = conn.execute(
                    insert_sql,
                    (
                        timestamp,
                        user_id,
                        tool_name,
                        action,
                        request_json,
                        response_json,
                        success,
                        error_message,
                        execution_time_ms
                    )
                )
                conn.commit()
                log_id = cursor.lastrowid

            logger.debug(f"📝 JSON-RPC 로그 저장: {tool_name} (action={action}, log_id={log_id})")
            return log_id

        except Exception as e:
            logger.error(f"❌ JSON-RPC 로그 저장 실패: {str(e)}")
            return -1

    def get_logs(
        self,
        user_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """
        로그 조회

        Args:
            user_id: 사용자 ID 필터
            tool_name: 도구 이름 필터
            action: 액션 필터
            limit: 조회 개수
            offset: 오프셋

        Returns:
            로그 리스트
        """
        try:
            where_clauses = []
            params = []

            if user_id:
                where_clauses.append("user_id = ?")
                params.append(user_id)

            if tool_name:
                where_clauses.append("tool_name = ?")
                params.append(tool_name)

            if action:
                where_clauses.append("action = ?")
                params.append(action)

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            query_sql = f"""
            SELECT id, timestamp, user_id, tool_name, action,
                   request_data, response_data, success, error_message,
                   execution_time_ms, created_at
            FROM jsonrpc_logs
            WHERE {where_sql}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """

            params.extend([limit, offset])

            with self.db.get_connection() as conn:
                cursor = conn.execute(query_sql, params)
                rows = cursor.fetchall()

            logs = []
            for row in rows:
                logs.append({
                    "id": row[0],
                    "timestamp": row[1],
                    "user_id": row[2],
                    "tool_name": row[3],
                    "action": row[4],
                    "request_data": json.loads(row[5]) if row[5] else None,
                    "response_data": json.loads(row[6]) if row[6] else None,
                    "success": bool(row[7]),
                    "error_message": row[8],
                    "execution_time_ms": row[9],
                    "created_at": row[10]
                })

            return logs

        except Exception as e:
            logger.error(f"❌ 로그 조회 실패: {str(e)}")
            return []

    def get_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        통계 조회

        Args:
            user_id: 사용자 ID (선택)

        Returns:
            통계 데이터
        """
        try:
            where_clause = "WHERE user_id = ?" if user_id else ""
            params = [user_id] if user_id else []

            stats_sql = f"""
            SELECT
                COUNT(*) as total_calls,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_calls,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_calls,
                AVG(execution_time_ms) as avg_execution_time,
                tool_name,
                action
            FROM jsonrpc_logs
            {where_clause}
            GROUP BY tool_name, action
            ORDER BY total_calls DESC
            """

            with self.db.get_connection() as conn:
                cursor = conn.execute(stats_sql, params)
                rows = cursor.fetchall()

            stats = {
                "tools": []
            }

            for row in rows:
                stats["tools"].append({
                    "tool_name": row[4],
                    "action": row[5],
                    "total_calls": row[0],
                    "success_calls": row[1],
                    "failed_calls": row[2],
                    "avg_execution_time_ms": round(row[3], 2) if row[3] else None
                })

            return stats

        except Exception as e:
            logger.error(f"❌ 통계 조회 실패: {str(e)}")
            return {"tools": []}


# 전역 인스턴스
_jsonrpc_logger = None


def get_jsonrpc_logger() -> JSONRPCLogger:
    """JSON-RPC 로거 싱글톤 인스턴스 반환"""
    global _jsonrpc_logger
    if _jsonrpc_logger is None:
        _jsonrpc_logger = JSONRPCLogger()
    return _jsonrpc_logger


def log_jsonrpc_call(func: Callable) -> Callable:
    """
    JSON-RPC 호출 로깅 데코레이터

    Usage:
        @log_jsonrpc_call
        async def handle_call_tool(self, name: str, arguments: Dict[str, Any]):
            ...
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # 시작 시간
        start_time = time.time()

        # 파라미터 추출
        tool_name = args[1] if len(args) > 1 else kwargs.get("name", "unknown")
        arguments = args[2] if len(args) > 2 else kwargs.get("arguments", {})

        logger = get_jsonrpc_logger()

        try:
            # 원본 함수 실행
            result = await func(*args, **kwargs)

            # 실행 시간 계산
            execution_time_ms = int((time.time() - start_time) * 1000)

            # 성공 로그
            logger.log_request(
                tool_name=tool_name,
                arguments=arguments,
                response=result,
                success=True,
                execution_time_ms=execution_time_ms
            )

            return result

        except Exception as e:
            # 실행 시간 계산
            execution_time_ms = int((time.time() - start_time) * 1000)

            # 실패 로그
            logger.log_request(
                tool_name=tool_name,
                arguments=arguments,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time_ms
            )

            # 예외 재발생
            raise

    return wrapper
