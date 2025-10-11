"""Help content for MCP tools"""

TOOL_HELP = {
    "query_email": {
        "title": "📧 Email Query Tool",
        "description": "이메일을 조회하고 첨부파일을 다운로드합니다.",
        "usage": """
기본 사용법:
  query_email(
    user_id="kimghw",
    start_date="2024-01-01",
    end_date="2024-12-31"
  )

날짜 지정 방법:
  - start_date, end_date: YYYY-MM-DD 또는 YYYY-MM-DD HH:MM (KST 기준)
  - days_back: 최근 N일간의 메일 조회 (start_date/end_date보다 낮은 우선순위)

필터링:
  - sender_address: 특정 발신자의 메일만 조회
  - subject_contains: 제목에 특정 텍스트 포함된 메일
  - keyword: 전체 필드 검색 (간단한 키워드)
  - keyword_filter: 고급 검색 (AND/OR/NOT 조건)
  - conversation_with: 특정 사람과 주고받은 모든 메일
  - recipient_address: 내가 특정 수신자에게 보낸 메일

옵션:
  - max_mails: 최대 조회 개수 (기본값: 300)
  - include_body: 본문 포함 여부 (기본값: true)
  - download_attachments: 첨부파일 다운로드 (기본값: false)
  - save_emails: 메일을 텍스트 파일로 저장 (기본값: true)
  - save_csv: CSV 파일로 메타데이터 내보내기 (기본값: false)
        """,
        "parameters": {
            "user_id": {
                "type": "string",
                "required": True,
                "description": "조회할 사용자 ID (예: 'kimghw')",
                "example": "kimghw"
            },
            "start_date": {
                "type": "string",
                "required": True,
                "description": "시작 날짜 (YYYY-MM-DD 또는 YYYY-MM-DD HH:MM, KST 기준)",
                "example": "2024-01-01 09:00"
            },
            "end_date": {
                "type": "string",
                "required": True,
                "description": "종료 날짜 (YYYY-MM-DD 또는 YYYY-MM-DD HH:MM, KST 기준)",
                "example": "2024-12-31 18:00"
            },
            "days_back": {
                "type": "integer",
                "required": False,
                "description": "최근 N일간 조회 (start_date/end_date보다 낮은 우선순위)",
                "default": 30,
                "example": 7
            },
            "max_mails": {
                "type": "integer",
                "required": False,
                "description": "최대 조회 개수",
                "default": 300,
                "example": 100
            },
            "sender_address": {
                "type": "string",
                "required": False,
                "description": "받은 메일 필터: 특정 발신자의 메일만 조회",
                "example": "sender@company.com"
            },
            "subject_contains": {
                "type": "string",
                "required": False,
                "description": "제목 필터: 특정 텍스트가 포함된 메일만 조회",
                "example": "계약서"
            },
            "keyword": {
                "type": "string",
                "required": False,
                "description": "간단한 키워드 검색 (모든 필드)",
                "example": "프로젝트"
            },
            "keyword_filter": {
                "type": "object",
                "required": False,
                "description": "고급 키워드 검색 (AND/OR/NOT 조건 조합)",
                "example": {
                    "and_keywords": ["계약서", "2024"],
                    "not_keywords": ["취소"]
                },
                "fields": {
                    "and_keywords": "모든 키워드가 포함되어야 함",
                    "or_keywords": "하나 이상의 키워드가 포함되어야 함",
                    "not_keywords": "이 키워드들이 포함되지 않아야 함"
                }
            },
            "conversation_with": {
                "type": "array",
                "required": False,
                "description": "특정 사람과 주고받은 모든 메일 (받은메일 + 보낸메일)",
                "example": ["person@company.com"]
            },
            "recipient_address": {
                "type": "string",
                "required": False,
                "description": "보낸 메일 필터: 내가 특정 수신자에게 보낸 메일만",
                "example": "recipient@company.com"
            },
            "include_body": {
                "type": "boolean",
                "required": False,
                "description": "이메일 본문 포함 여부",
                "default": True,
                "example": False
            },
            "download_attachments": {
                "type": "boolean",
                "required": False,
                "description": "첨부파일 다운로드 및 텍스트 변환",
                "default": False,
                "example": True
            },
            "save_emails": {
                "type": "boolean",
                "required": False,
                "description": "메일을 텍스트 파일로 저장",
                "default": True,
                "example": False
            },
            "save_csv": {
                "type": "boolean",
                "required": False,
                "description": "메타데이터를 CSV 파일로 내보내기",
                "default": False,
                "example": True
            }
        },
        "examples": [
            {
                "name": "최근 7일간 메일 조회",
                "code": """query_email(
    user_id="kimghw",
    start_date="2024-01-01",
    end_date="2024-01-07"
)"""
            },
            {
                "name": "특정 발신자의 메일만 조회",
                "code": """query_email(
    user_id="kimghw",
    start_date="2024-01-01",
    end_date="2024-12-31",
    sender_address="boss@company.com"
)"""
            },
            {
                "name": "키워드 검색 (AND 조건)",
                "code": """query_email(
    user_id="kimghw",
    start_date="2024-01-01",
    end_date="2024-12-31",
    keyword_filter={
        "and_keywords": ["계약서", "2024"],
        "not_keywords": ["취소"]
    }
)"""
            },
            {
                "name": "제목만 빠르게 조회",
                "code": """query_email(
    user_id="kimghw",
    start_date="2024-01-01",
    end_date="2024-12-31",
    include_body=False,
    save_emails=False,
    download_attachments=False
)"""
            }
        ]
    },
    "create_enrollment_file": {
        "title": "📝 Create Enrollment File",
        "description": "계정 등록을 위한 YAML 설정 파일을 생성합니다.",
        "usage": """
기본 사용법:
  create_enrollment_file(
    user_id="kimghw",
    email="kimghw@krs.co.kr",
    oauth_client_id="12345678-1234-1234-1234-123456789012",
    oauth_client_secret="your-secret-here",
    oauth_tenant_id="87654321-4321-4321-4321-210987654321"
  )

필수 입력:
  - user_id: 사용자 ID (3-50자, 영숫자/점/하이픈/언더스코어)
  - email: 이메일 주소 (유효한 형식)
  - oauth_client_id: Azure App Client ID (GUID 형식)
  - oauth_client_secret: Azure App Client Secret (최소 8자)
  - oauth_tenant_id: Azure AD Tenant ID (GUID 형식)

선택 입력:
  - user_name: 사용자 이름 (기본값: user_id)
  - oauth_redirect_uri: 리다이렉트 URI (기본값: http://localhost:5000/auth/callback)
  - delegated_permissions: 권한 목록 (기본값: 기본 권한 세트)
        """,
        "parameters": {
            "user_id": {
                "type": "string",
                "required": True,
                "description": "사용자 ID (3-50자, 영숫자로 시작)",
                "example": "kimghw",
                "validation": "3-50자, 영숫자/점/하이픈/언더스코어만 허용"
            },
            "email": {
                "type": "string",
                "required": True,
                "description": "이메일 주소",
                "example": "kimghw@krs.co.kr",
                "validation": "유효한 이메일 형식 (user@domain.com)"
            },
            "oauth_client_id": {
                "type": "string",
                "required": True,
                "description": "Azure App OAuth Client ID",
                "example": "12345678-1234-1234-1234-123456789012",
                "validation": "GUID 형식 (8-4-4-4-12)"
            },
            "oauth_client_secret": {
                "type": "string",
                "required": True,
                "description": "Azure App OAuth Client Secret",
                "example": "SecretKey123456",
                "validation": "8-256자"
            },
            "oauth_tenant_id": {
                "type": "string",
                "required": True,
                "description": "Azure AD Tenant ID",
                "example": "87654321-4321-4321-4321-210987654321",
                "validation": "GUID 형식 (8-4-4-4-12)"
            },
            "user_name": {
                "type": "string",
                "required": False,
                "description": "사용자 표시 이름",
                "default": "user_id 값",
                "example": "김경환"
            },
            "oauth_redirect_uri": {
                "type": "string",
                "required": False,
                "description": "OAuth 리다이렉트 URI",
                "default": "http://localhost:5000/auth/callback",
                "example": "http://localhost:5000/auth/callback"
            },
            "delegated_permissions": {
                "type": "array",
                "required": False,
                "description": "위임된 권한 목록",
                "default": ["Mail.ReadWrite", "Mail.Send", "offline_access", "Files.ReadWrite.All", "Sites.ReadWrite.All"],
                "example": ["Mail.ReadWrite", "Mail.Send", "offline_access"]
            }
        },
        "examples": [
            {
                "name": "기본 계정 등록",
                "code": """create_enrollment_file(
    user_id="kimghw",
    email="kimghw@krs.co.kr",
    oauth_client_id="12345678-1234-1234-1234-123456789012",
    oauth_client_secret="YourSecretHere",
    oauth_tenant_id="87654321-4321-4321-4321-210987654321"
)"""
            }
        ]
    },
    "list_enrollments": {
        "title": "📋 List Enrollment Files",
        "description": "등록 대기 중인 enrollment 파일 목록을 조회합니다.",
        "usage": "list_enrollments()",
        "parameters": {},
        "examples": [
            {
                "name": "Enrollment 파일 목록 조회",
                "code": "list_enrollments()"
            }
        ]
    },
    "enroll_account": {
        "title": "✅ Enroll Account to Database",
        "description": "Enrollment 파일을 기반으로 계정을 데이터베이스에 등록합니다.",
        "usage": "enroll_account(user_id='kimghw')",
        "parameters": {
            "user_id": {
                "type": "string",
                "required": True,
                "description": "등록할 사용자 ID (enrollment 파일이 존재해야 함)",
                "example": "kimghw"
            }
        },
        "examples": [
            {
                "name": "계정 등록",
                "code": "enroll_account(user_id='kimghw')"
            }
        ]
    },
    "list_accounts": {
        "title": "👥 List Registered Accounts",
        "description": "데이터베이스에 등록된 계정 목록을 조회합니다.",
        "usage": "list_accounts(status='all')",
        "parameters": {
            "status": {
                "type": "string",
                "required": False,
                "description": "계정 상태 필터",
                "default": "all",
                "example": "active",
                "options": ["all", "active", "inactive"]
            }
        },
        "examples": [
            {
                "name": "모든 계정 조회",
                "code": "list_accounts()"
            },
            {
                "name": "활성 계정만 조회",
                "code": "list_accounts(status='active')"
            }
        ]
    },
    "get_account_status": {
        "title": "📊 Get Account Status",
        "description": "특정 계정의 상세 상태 정보를 조회합니다.",
        "usage": "get_account_status(user_id='kimghw')",
        "parameters": {
            "user_id": {
                "type": "string",
                "required": True,
                "description": "조회할 사용자 ID",
                "example": "kimghw"
            }
        },
        "examples": [
            {
                "name": "계정 상태 조회",
                "code": "get_account_status(user_id='kimghw')"
            }
        ]
    },
    "start_authentication": {
        "title": "🔐 Start OAuth Authentication",
        "description": "OAuth 인증 프로세스를 시작합니다. 브라우저에서 열어야 하는 인증 URL을 반환합니다.",
        "usage": "start_authentication(user_id='kimghw')",
        "parameters": {
            "user_id": {
                "type": "string",
                "required": True,
                "description": "인증할 사용자 ID (데이터베이스에 등록되어 있어야 함)",
                "example": "kimghw"
            }
        },
        "examples": [
            {
                "name": "인증 시작",
                "code": "start_authentication(user_id='kimghw')"
            }
        ]
    },
    "check_auth_status": {
        "title": "🔍 Check Authentication Status",
        "description": "인증 세션의 상태를 확인합니다.",
        "usage": "check_auth_status(session_id='abc123')",
        "parameters": {
            "session_id": {
                "type": "string",
                "required": True,
                "description": "start_authentication에서 반환된 세션 ID",
                "example": "abc123def456"
            }
        },
        "examples": [
            {
                "name": "인증 상태 확인",
                "code": "check_auth_status(session_id='abc123def456')"
            }
        ]
    },
    "list_active_accounts": {
        "title": "👥 List Active Email Accounts",
        "description": "활성화된 이메일 계정 목록을 조회합니다.",
        "usage": "list_active_accounts()",
        "parameters": {},
        "examples": [
            {
                "name": "활성 계정 조회",
                "code": "list_active_accounts()"
            }
        ]
    }
}


def get_tool_help(tool_name: str = None) -> str:
    """
    Get help content for a specific tool or all tools

    Args:
        tool_name: Name of the tool (optional)

    Returns:
        Formatted help text
    """
    if tool_name:
        if tool_name not in TOOL_HELP:
            return f"❌ Tool '{tool_name}' not found. Use help() to see all available tools."

        tool = TOOL_HELP[tool_name]
        help_text = f"""
{'='*60}
{tool['title']}
{'='*60}

📖 설명:
{tool['description']}

💡 사용법:
{tool['usage']}
"""

        if tool['parameters']:
            help_text += "\n📋 파라미터:\n"
            for param_name, param_info in tool['parameters'].items():
                required = "필수" if param_info.get('required', False) else "선택"
                default = f" (기본값: {param_info.get('default')})" if 'default' in param_info else ""
                validation = f"\n     검증: {param_info.get('validation')}" if 'validation' in param_info else ""
                options = f"\n     옵션: {', '.join(param_info.get('options', []))}" if 'options' in param_info else ""

                help_text += f"""
  • {param_name} [{required}]
    타입: {param_info['type']}{default}
    설명: {param_info['description']}{validation}{options}
    예시: {param_info.get('example', 'N/A')}
"""

                # Handle nested fields (like keyword_filter)
                if 'fields' in param_info:
                    help_text += "    하위 필드:\n"
                    for field_name, field_desc in param_info['fields'].items():
                        help_text += f"      - {field_name}: {field_desc}\n"

        if tool['examples']:
            help_text += "\n📚 예제:\n"
            for idx, example in enumerate(tool['examples'], 1):
                help_text += f"""
{idx}. {example['name']}
{example['code']}
"""

        return help_text.strip()

    else:
        # List all tools
        help_text = """
{'='*60}
📖 MCP Mail Query Server - Available Tools
{'='*60}

이메일 조회:
  • query_email - 이메일 조회 및 첨부파일 다운로드

계정 관리:
  • create_enrollment_file - Enrollment 파일 생성
  • list_enrollments - Enrollment 파일 목록
  • enroll_account - 계정 등록
  • list_accounts - 등록된 계정 목록
  • get_account_status - 계정 상태 조회
  • list_active_accounts - 활성 계정 목록

인증:
  • start_authentication - OAuth 인증 시작
  • check_auth_status - 인증 상태 확인

특정 tool의 자세한 사용법을 보려면:
  help(tool_name='query_email')

{'='*60}
"""
        return help_text.strip()
