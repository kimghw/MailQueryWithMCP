"""
OAuth 콜백 처리 웹서버
"""

import asyncio
import json
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from infra.core.config import get_config
from infra.core.logger import get_logger

from .service.oauth_callback_service import OAuthCallbackService

logger = get_logger(__name__)


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """OAuth 콜백 요청 핸들러"""

    def do_GET(self):
        """GET 요청 처리"""
        parsed_path = urlparse(self.path)

        if parsed_path.path == "/health":
            self._handle_health_check()
        elif parsed_path.path == "/auth/callback":
            self._handle_oauth_callback()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def _handle_health_check(self):
        """헬스체크 처리"""
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        response = {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "server": "oauth_callback_server",
        }
        self.wfile.write(json.dumps(response).encode())

    def _handle_oauth_callback(self):
        """OAuth 콜백 처리"""
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)

        params = {key: values[0] for key, values in query_params.items() if values}
        logger.debug(f"OAuth 콜백 수신: {list(params.keys())}")

        if hasattr(self.server, "oauth_server"):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response_html = loop.run_until_complete(
                self.server.oauth_server.process_callback_async(params)
            )
            loop.close()

            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(response_html.encode("utf-8"))
        else:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Server Error")

    def log_message(self, format, *args):
        """기본 로그 억제"""
        pass


class OAuthWebServer:
    """OAuth 콜백 처리를 위한 임시 웹서버"""

    def __init__(self):
        """웹서버 초기화"""
        self.config = get_config()
        self.callback_service = OAuthCallbackService()

        self.httpd: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.port = 5000

        self.session_store: Optional[Dict[str, Any]] = None

    def set_session_store(self, session_store: Dict[str, Any]):
        """세션 저장소 설정"""
        self.session_store = session_store
        self.callback_service.set_session_store(session_store)
        logger.debug("웹서버에 세션 저장소 설정됨")

    async def start_server(self, port: int = 5000) -> str:
        """
        웹서버를 시작합니다.
        """
        try:
            self.port = port

            server_address = ("localhost", port)
            self.httpd = HTTPServer(server_address, OAuthCallbackHandler)
            self.httpd.oauth_server = self

            def run_server():
                logger.info(f"OAuth 콜백 웹서버 시작: http://localhost:{port}")
                self.httpd.serve_forever()

            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()

            self.is_running = True
            server_url = f"http://localhost:{port}"

            logger.info(f"OAuth 콜백 웹서버 시작됨: {server_url}")
            return server_url

        except Exception as e:
            logger.error(f"웹서버 시작 실패: {str(e)}")
            self._cleanup()
            raise

    async def stop_server(self):
        """웹서버를 중지합니다."""
        try:
            self.is_running = False
            self._cleanup()
            logger.info("OAuth 콜백 웹서버 중지됨")
        except Exception as e:
            logger.error(f"웹서버 중지 실패: {str(e)}")

    async def process_callback_async(self, query_params: Dict[str, str]) -> str:
        """
        OAuth 콜백을 비동기로 처리합니다.
        """
        if not self.session_store:
            logger.error("세션 저장소가 설정되지 않음")
            return "<h1>서버 오류</h1><p>세션 저장소가 없습니다.</p>"

        return await self.callback_service.process_callback(query_params)

    def _cleanup(self):
        """리소스 정리"""
        try:
            if self.httpd:
                self.httpd.shutdown()
                self.httpd = None

            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=5)
                self.server_thread = None

        except Exception as e:
            logger.error(f"웹서버 정리 실패: {str(e)}")

    def __del__(self):
        """소멸자"""
        if self.is_running:
            try:
                self._cleanup()
            except:
                pass


class OAuthWebServerManager:
    """웹서버 생명주기 관리 클래스"""

    def __init__(self):
        self.server: Optional[OAuthWebServer] = None
        self.server_url: Optional[str] = None

    async def start_server(
        self, session_store: Dict[str, Any], port: int = 5000
    ) -> str:
        """
        웹서버를 시작하고 세션 저장소를 설정합니다.
        """
        if self.server and self.server.is_running:
            logger.warning("웹서버가 이미 실행 중입니다")
            return self.server_url

        self.server = OAuthWebServer()
        self.server.set_session_store(session_store)
        self.server_url = await self.server.start_server(port)

        logger.info(f"웹서버 관리자 시작: {self.server_url}")
        return self.server_url

    async def stop_server(self):
        """웹서버를 중지합니다."""
        if self.server:
            await self.server.stop_server()
            self.server = None
            self.server_url = None
            logger.info("웹서버 관리자 중지됨")

    @property
    def is_running(self) -> bool:
        """실행 상태 확인"""
        return self.server is not None and self.server.is_running


# 전역 웹서버 관리자 인스턴스
_web_server_manager = OAuthWebServerManager()


def get_auth_web_server_manager() -> OAuthWebServerManager:
    """
    웹서버 관리자 인스턴스를 반환합니다.

    Returns:
        OAuthWebServerManager 인스턴스
    """
    return _web_server_manager
