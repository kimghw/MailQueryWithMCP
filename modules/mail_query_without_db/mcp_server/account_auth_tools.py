"""Account and Authentication Tools for MCP Server"""

import asyncio
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from infra.core.database import get_database_manager
from infra.core.logger import get_logger
from modules.account import AccountOrchestrator
from modules.auth import get_auth_orchestrator, AuthStartRequest

logger = get_logger(__name__)


class AccountAuthTools:
    """계정 관리 및 인증 Tools"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent.parent
        self.enrollment_dir = self.project_root / "enrollment"
        self.db = get_database_manager()

    async def create_enrollment_file(self, arguments: Dict[str, Any]) -> str:
        """
        Enrollment YAML 파일 생성

        Args:
            user_id: 사용자 ID
            email: 이메일 주소
            user_name: 사용자 이름
            oauth_client_id: OAuth Client ID
            oauth_client_secret: OAuth Client Secret
            oauth_tenant_id: OAuth Tenant ID
            oauth_redirect_uri: OAuth Redirect URI (기본: http://localhost:5000/auth/callback)
            delegated_permissions: 권한 목록 (기본: Mail.ReadWrite, Mail.Send, offline_access)
        """
        try:
            user_id = arguments.get("user_id")
            if not user_id:
                return "Error: user_id is required"

            email = arguments.get("email")
            if not email:
                return "Error: email is required"

            oauth_client_id = arguments.get("oauth_client_id")
            oauth_client_secret = arguments.get("oauth_client_secret")
            oauth_tenant_id = arguments.get("oauth_tenant_id")

            if not all([oauth_client_id, oauth_client_secret, oauth_tenant_id]):
                return "Error: oauth_client_id, oauth_client_secret, oauth_tenant_id are required"

            # 기본값 설정
            user_name = arguments.get("user_name", user_id)
            oauth_redirect_uri = arguments.get("oauth_redirect_uri", "http://localhost:5000/auth/callback")
            delegated_permissions = arguments.get("delegated_permissions", [
                "Mail.ReadWrite",
                "Mail.Send",
                "offline_access",
                "Files.ReadWrite.All",
                "Sites.ReadWrite.All"
            ])

            # enrollment 파일 경로
            enrollment_file = self.enrollment_dir / f"{user_id}.yaml"

            # YAML 데이터 구성 (올바른 구조)
            enrollment_data = {
                "account": {
                    "email": email,
                    "name": user_name,
                    "user_id": user_id
                },
                "microsoft_graph": {
                    "client_id": oauth_client_id,
                    "client_secret": oauth_client_secret,
                    "tenant_id": oauth_tenant_id
                },
                "oauth": {
                    "auth_type": "Authorization Code Flow",
                    "redirect_uri": oauth_redirect_uri,
                    "delegated_permissions": delegated_permissions
                }
            }

            # YAML 파일 저장
            self.enrollment_dir.mkdir(parents=True, exist_ok=True)
            with open(enrollment_file, 'w', encoding='utf-8') as f:
                yaml.dump(enrollment_data, f, default_flow_style=False, allow_unicode=True)

            logger.info(f"Enrollment file created: {enrollment_file}")

            return f"""✅ Enrollment 파일 생성 완료

파일 경로: {enrollment_file}
사용자 ID: {user_id}
이메일: {email}
권한: {', '.join(delegated_permissions)}

다음 단계:
1. enroll_account tool을 사용하여 DB에 등록
2. start_authentication tool을 사용하여 OAuth 인증"""

        except Exception as e:
            error_msg = f"Enrollment 파일 생성 실패: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    async def list_enrollments(self, arguments: Dict[str, Any]) -> str:
        """
        Enrollment 파일 목록 조회
        """
        try:
            if not self.enrollment_dir.exists():
                return "Enrollment 디렉토리가 없습니다."

            yaml_files = list(self.enrollment_dir.glob("*.yaml"))

            if not yaml_files:
                return "등록된 enrollment 파일이 없습니다."

            result = ["📋 Enrollment 파일 목록:\n"]

            for yaml_file in sorted(yaml_files):
                try:
                    with open(yaml_file, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)

                    user_id = data.get('user_id', yaml_file.stem)
                    email = data.get('email', 'N/A')

                    result.append(f"• {user_id}")
                    result.append(f"  - 파일: {yaml_file.name}")
                    result.append(f"  - 이메일: {email}")
                    result.append("")

                except Exception as e:
                    result.append(f"• {yaml_file.name} (읽기 실패: {str(e)})")

            return "\n".join(result)

        except Exception as e:
            error_msg = f"Enrollment 목록 조회 실패: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    async def enroll_account(self, arguments: Dict[str, Any]) -> str:
        """
        계정을 DB에 등록

        Args:
            user_id: 사용자 ID (enrollment 파일 이름)
        """
        try:
            user_id = arguments.get("user_id")
            if not user_id:
                return "Error: user_id is required"

            # enrollment 파일 확인
            enrollment_file = self.enrollment_dir / f"{user_id}.yaml"
            if not enrollment_file.exists():
                return f"Error: Enrollment 파일이 없습니다: {enrollment_file}\n\ncreate_enrollment_file tool을 먼저 사용하세요."

            # AccountOrchestrator 사용
            orchestrator = AccountOrchestrator()
            result = orchestrator.account_sync_single_file(str(enrollment_file))

            if result.get("success"):
                action = result.get("action")

                if action == "created":
                    msg = f"""✅ 계정 등록 완료

사용자 ID: {user_id}
상태: 새로 생성됨

다음 단계:
start_authentication tool을 사용하여 OAuth 인증을 진행하세요."""
                elif action == "updated":
                    msg = f"""✅ 계정 업데이트 완료

사용자 ID: {user_id}
상태: 업데이트됨"""
                else:
                    msg = f"""ℹ️  계정이 이미 최신 상태입니다

사용자 ID: {user_id}"""

                return msg
            else:
                error = result.get("error", "알 수 없는 오류")
                return f"Error: 계정 등록 실패 - {error}"

        except Exception as e:
            error_msg = f"계정 등록 실패: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    async def list_accounts(self, arguments: Dict[str, Any]) -> str:
        """
        등록된 계정 목록 조회

        Args:
            status: 계정 상태 필터 (all, active, inactive) - 기본: all
        """
        try:
            status_filter = arguments.get("status", "all")

            query = """
                SELECT user_id, user_name, email, status, is_active,
                       token_expiry, last_sync_time, created_at
                FROM accounts
            """

            if status_filter == "active":
                query += " WHERE is_active = 1 AND status = 'active'"
            elif status_filter == "inactive":
                query += " WHERE is_active = 0 OR status != 'active'"

            query += " ORDER BY user_id"

            accounts = self.db.fetch_all(query)

            if not accounts:
                return "등록된 계정이 없습니다."

            result = [f"📋 등록된 계정 목록 (총 {len(accounts)}개):\n"]

            for account in accounts:
                account_dict = dict(account)
                user_id = account_dict.get('user_id', 'N/A')
                email = account_dict.get('email', 'N/A')
                status = account_dict.get('status', 'N/A')
                is_active = account_dict.get('is_active', False)

                # 토큰 만료 상태
                token_expiry = account_dict.get('token_expiry')
                token_status = "만료" if token_expiry and datetime.fromisoformat(token_expiry) < datetime.now() else "유효"

                active_mark = "✅" if is_active else "❌"

                result.append(f"{active_mark} {user_id}")
                result.append(f"  - 이메일: {email}")
                result.append(f"  - 상태: {status}")
                result.append(f"  - 토큰: {token_status}")
                result.append("")

            return "\n".join(result)

        except Exception as e:
            error_msg = f"계정 목록 조회 실패: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    async def start_authentication(self, arguments: Dict[str, Any]) -> str:
        """
        OAuth 인증 시작

        Args:
            user_id: 사용자 ID
        """
        try:
            user_id = arguments.get("user_id")
            if not user_id:
                return "Error: user_id is required"

            # 계정이 DB에 등록되어 있는지 확인
            account = self.db.fetch_one(
                "SELECT user_id, email FROM accounts WHERE user_id = ?",
                (user_id,)
            )

            if not account:
                return f"Error: 계정이 등록되지 않았습니다: {user_id}\n\nenroll_account tool을 먼저 사용하세요."

            # AuthOrchestrator 사용
            orchestrator = get_auth_orchestrator()
            request = AuthStartRequest(user_id=user_id)
            response = await orchestrator.auth_orchestrator_start_authentication(request)

            return f"""🔐 OAuth 인증 시작

사용자 ID: {user_id}
세션 ID: {response.session_id}
만료 시간: {response.expires_at}

📋 인증 URL:
{response.auth_url}

위 URL을 브라우저에서 열어 Microsoft 로그인을 완료하세요.

인증 상태 확인:
check_auth_status tool을 사용하여 세션 ID로 확인할 수 있습니다."""

        except Exception as e:
            error_msg = f"인증 시작 실패: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    async def check_auth_status(self, arguments: Dict[str, Any]) -> str:
        """
        인증 상태 확인

        Args:
            session_id: 세션 ID (start_authentication에서 반환된 값)
        """
        try:
            session_id = arguments.get("session_id")
            if not session_id:
                return "Error: session_id is required"

            orchestrator = get_auth_orchestrator()
            status = await orchestrator.auth_orchestrator_get_session_status(session_id)

            status_emoji = {
                "PENDING": "⏳",
                "CALLBACK_RECEIVED": "🔄",
                "COMPLETED": "✅",
                "FAILED": "❌",
                "EXPIRED": "⏰"
            }

            emoji = status_emoji.get(status.status.value, "❓")

            result = f"""{emoji} 인증 상태: {status.status.value}

세션 ID: {session_id}
메시지: {status.message}"""

            if status.error_message:
                result += f"\n오류: {status.error_message}"

            if status.status.value == "COMPLETED":
                result += "\n\n✅ 인증이 완료되었습니다! 이제 메일 조회가 가능합니다."
            elif status.status.value == "PENDING":
                result += "\n\n⏳ 브라우저에서 인증을 완료해주세요."
            elif status.status.value == "FAILED" or status.status.value == "EXPIRED":
                result += "\n\n❌ 인증에 실패했습니다. start_authentication을 다시 시도하세요."

            return result

        except Exception as e:
            error_msg = f"인증 상태 확인 실패: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    async def get_account_status(self, arguments: Dict[str, Any]) -> str:
        """
        특정 계정의 상세 상태 조회

        Args:
            user_id: 사용자 ID
        """
        try:
            user_id = arguments.get("user_id")
            if not user_id:
                return "Error: user_id is required"

            account = self.db.fetch_one(
                """
                SELECT user_id, user_name, email, status, is_active,
                       token_expiry, last_sync_time, created_at, updated_at,
                       oauth_client_id, oauth_tenant_id, delegated_permissions
                FROM accounts
                WHERE user_id = ?
                """,
                (user_id,)
            )

            if not account:
                return f"계정을 찾을 수 없습니다: {user_id}"

            account_dict = dict(account)

            # 토큰 상태 확인
            token_expiry = account_dict.get('token_expiry')
            if token_expiry:
                expiry_dt = datetime.fromisoformat(token_expiry)
                token_status = "✅ 유효" if expiry_dt > datetime.now() else "❌ 만료"
                token_expiry_str = expiry_dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                token_status = "❌ 없음"
                token_expiry_str = "N/A"

            # 권한 목록
            permissions = account_dict.get('delegated_permissions', '')
            if permissions:
                import json
                try:
                    perm_list = json.loads(permissions) if isinstance(permissions, str) else permissions
                    permissions_str = "\n  - " + "\n  - ".join(perm_list)
                except:
                    permissions_str = permissions
            else:
                permissions_str = "N/A"

            result = f"""📊 계정 상세 정보: {user_id}

기본 정보:
  - 사용자 이름: {account_dict.get('user_name', 'N/A')}
  - 이메일: {account_dict.get('email', 'N/A')}
  - 상태: {account_dict.get('status', 'N/A')}
  - 활성화: {'예' if account_dict.get('is_active') else '아니오'}

OAuth 정보:
  - Client ID: {account_dict.get('oauth_client_id', 'N/A')[:20]}...
  - Tenant ID: {account_dict.get('oauth_tenant_id', 'N/A')}

토큰 상태:
  - 상태: {token_status}
  - 만료 시간: {token_expiry_str}

권한:{permissions_str}

동기화:
  - 마지막 동기화: {account_dict.get('last_sync_time', 'N/A')}
  - 생성일: {account_dict.get('created_at', 'N/A')}
  - 수정일: {account_dict.get('updated_at', 'N/A')}
"""

            return result

        except Exception as e:
            error_msg = f"계정 상태 조회 실패: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
