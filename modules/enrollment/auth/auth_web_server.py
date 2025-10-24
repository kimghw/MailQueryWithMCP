"""
Auth 모듈의 OAuth 콜백 처리 웹서버

OAuth 2.0 인증 콜백을 처리하는 임시 웹서버입니다.
메모리 세션과 연동하여 인증 코드를 토큰으로 교환하고 결과를 저장합니다.

리팩토링: 비즈니스 로직은 AuthCallbackProcessor로 분리되었습니다.
"""

import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict, Optional
from urllib.parse import parse_qs, urlparse

from infra.core.logger import get_logger

from .auth_callback_processor import AuthCallbackProcessor

logger = get_logger(__name__)


class CallbackHandler(BaseHTTPRequestHandler):
    """OAuth 콜백 요청 핸들러"""

    def do_GET(self):
        """GET 요청 처리"""
        parsed_path = urlparse(self.path)

        if parsed_path.path == "/health":
            self._handle_health_check()
        elif parsed_path.path in ["/auth/callback", "/enrollment/callback"]:
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "server": "oauth_callback_server",
        }
        self.wfile.write(json.dumps(response).encode())

    def _handle_oauth_callback(self):
        """OAuth 콜백 처리"""
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)

        # 쿼리 파라미터를 단일 값으로 변환
        params = {}
        for key, values in query_params.items():
            params[key] = values[0] if values else ""

        logger.debug(f"OAuth 콜백 수신: {list(params.keys())}")

        # 서버 인스턴스에서 콜백 프로세서로 처리
        if hasattr(self.server, "auth_server") and hasattr(self.server.auth_server, "callback_processor"):
            response_html = self.server.auth_server.callback_processor.process_callback(params)
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(response_html.encode("utf-8"))

            # 응답 전송 후 서버 종료 스케줄링
            self._schedule_server_shutdown()
        else:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Server Error")

    def _schedule_server_shutdown(self):
        """응답 전송 후 서버를 안전하게 종료"""
        def shutdown_server():
            import time
            time.sleep(0.5)  # 응답이 완전히 전송될 시간 확보
            if hasattr(self.server, "auth_server"):
                logger.info("OAuth 콜백 처리 완료, 웹서버 종료 중...")
                self.server.shutdown()

        shutdown_thread = threading.Thread(target=shutdown_server, daemon=True)
        shutdown_thread.start()

    def log_message(self, format, *args):
        """로그 메시지 커스터마이징"""
        pass  # 기본 로그 억제


class AuthWebServer:
    """OAuth 콜백 처리를 위한 임시 웹서버 (인프라 레이어)"""

    def __init__(self):
        """웹서버 초기화"""
        # 콜백 프로세서 (비즈니스 로직)
        self.callback_processor = AuthCallbackProcessor()

        # 웹서버 인프라
        self.httpd: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.port = 5000

    def set_session_store(self, session_store: Dict[str, Any]):
        """세션 저장소 설정 (콜백 프로세서로 위임)"""
        self.callback_processor.set_session_store(session_store)
        logger.debug("세션 저장소 설정됨")

    def register_callback_handler(self, state: str, handler: Callable):
        """콜백 핸들러 등록 (콜백 프로세서로 위임)"""
        self.callback_processor.register_callback_handler(state, handler)
        logger.debug(f"콜백 핸들러 등록: state={state[:10]}...")

    async def auth_web_server_start(self, port: int = 5000) -> str:
        """
        웹서버를 시작합니다.

        Args:
            port: 포트 번호

        Returns:
            서버 URL
        """
        try:
            self.port = port

            # HTTPServer 생성
            server_address = ("localhost", port)
            self.httpd = HTTPServer(server_address, CallbackHandler)
            self.httpd.auth_server = self  # 핸들러에서 접근할 수 있도록 참조 추가

            # 별도 스레드에서 서버 실행
            def run_server():
                logger.info(f"OAuth 콜백 웹서버 시작 중: http://localhost:{port}")
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

    async def auth_web_server_stop(self):
        """웹서버를 중지합니다."""
        try:
            self.is_running = False
            self._cleanup()
            logger.info("OAuth 콜백 웹서버 중지됨")
        except Exception as e:
            logger.error(f"웹서버 중지 실패: {str(e)}")

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
            except Exception as e:
                logger.debug(f"Cleanup warning: {e}")


class AuthWebServerManager:
    """웹서버 생명주기 관리 클래스"""

    def __init__(self):
        self.server: Optional[AuthWebServer] = None
        self.server_url: Optional[str] = None

    async def auth_web_server_manager_start(
        self, session_store: Dict[str, Any], port: int = 5000
    ) -> str:
        """
        웹서버를 시작하고 세션 저장소를 설정합니다.

        Args:
            session_store: 세션 저장소
            port: 포트 번호

        Returns:
            서버 URL
        """
        if self.server and self.server.is_running:
            logger.warning("웹서버가 이미 실행 중입니다")
            return self.server_url

        self.server = AuthWebServer()
        self.server.set_session_store(session_store)
        self.server_url = await self.server.auth_web_server_start(port)

        logger.info(f"웹서버 관리자 시작: {self.server_url}")
        return self.server_url

    async def auth_web_server_manager_stop(self):
        """웹서버를 중지합니다."""
        if self.server:
            await self.server.auth_web_server_stop()
            self.server = None
            self.server_url = None
            logger.info("웹서버 관리자 중지됨")

    def auth_web_server_manager_register_callback(self, state: str, handler: Callable):
        """콜백 핸들러를 등록합니다."""
        if self.server:
            self.server.register_callback_handler(state, handler)

    @property
    def is_running(self) -> bool:
        """실행 상태 확인"""
        return self.server is not None and self.server.is_running


# 전역 웹서버 관리자 인스턴스
_web_server_manager = AuthWebServerManager()


def get_auth_web_server_manager() -> AuthWebServerManager:
    """
    웹서버 관리자 인스턴스를 반환합니다.

    Returns:
        AuthWebServerManager 인스턴스
    """
    return _web_server_manager
