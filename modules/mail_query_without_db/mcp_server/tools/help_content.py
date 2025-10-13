"""Help content for MCP tools - Simplified to 5 essential tools"""

TOOL_HELP = {
    "register_account": {
        "title": "📝 Register Account",
        "description": "새 이메일 계정을 OAuth 인증 정보와 함께 데이터베이스에 등록합니다.",
        "usage": """
기본 사용법:
  register_account(
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
  - oauth_redirect_uri: 리다이렉트 URI (기본값: 자동 설정)
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
                "default": "자동 설정 (로컬/프로덕션 환경에 따라)",
                "example": "http://localhost:5000/auth/callback"
            }
        },
        "examples": [
            {
                "name": "기본 계정 등록",
                "code": """register_account(
    user_id="kimghw",
    email="kimghw@krs.co.kr",
    oauth_client_id="12345678-1234-1234-1234-123456789012",
    oauth_client_secret="YourSecretHere",
    oauth_tenant_id="87654321-4321-4321-4321-210987654321"
)"""
            }
        ]
    },
    "get_account_status": {
        "title": "📊 Get Account Status",
        "description": "특정 계정의 상세 상태 및 인증 정보를 조회합니다.",
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
        "description": "OAuth 인증 프로세스를 시작합니다. 반환된 인증 URL을 반드시 브라우저에서 열어 Microsoft 로그인을 완료해야 합니다.",
        "usage": """
start_authentication(user_id='kimghw')

⚠️  중요 안내:
1. 이 툴은 인증 URL을 반환합니다
2. 반환된 URL을 클릭하여 브라우저에서 열어주세요
3. Microsoft 계정으로 로그인하고 권한을 승인하세요
4. 승인 완료 후 자동으로 인증이 완료됩니다
5. get_account_status로 인증 상태를 확인할 수 있습니다
        """,
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
                "name": "OAuth 인증 시작",
                "code": """start_authentication(user_id='kimghw')

# 반환된 URL을 브라우저에서 열어 로그인 완료"""
            }
        ]
    },
    "query_email": {
        "title": "📧 Query Email",
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
            }
        ]
    },
    "help": {
        "title": "❓ Help",
        "description": "사용 가능한 툴의 도움말과 문서를 확인합니다.",
        "usage": "help() 또는 help(tool_name='register_account')",
        "parameters": {
            "tool_name": {
                "type": "string",
                "required": False,
                "description": "도움말을 볼 툴 이름 (선택사항)",
                "example": "register_account",
                "options": ["register_account", "get_account_status", "start_authentication", "query_email", "help"]
            }
        },
        "examples": [
            {
                "name": "전체 툴 목록 보기",
                "code": "help()"
            },
            {
                "name": "특정 툴 도움말",
                "code": "help(tool_name='query_email')"
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
        # List all tools (simplified to 5 essential tools)
        help_text = """
{'='*60}
📖 MCP Mail Query Server - Available Tools
{'='*60}

🔧 핵심 툴 (5개):

1. 📝 register_account
   계정 등록: OAuth 인증 정보와 함께 새 이메일 계정을 등록합니다.

2. 📊 get_account_status
   계정 상태 확인: 등록된 계정의 상태와 인증 정보를 조회합니다.

3. 🔐 start_authentication
   인증 시작: OAuth 인증을 시작하고 인증 URL을 받습니다.

4. 📧 query_email
   이메일 조회: 이메일을 조회하고 첨부파일을 다운로드/변환합니다.

5. ❓ help
   도움말: 각 툴의 자세한 사용법을 확인합니다.

📖 사용 순서:
  1️⃣ register_account     - 계정 등록
  2️⃣ start_authentication - OAuth 인증
  3️⃣ get_account_status   - 인증 상태 확인
  4️⃣ query_email         - 메일 조회

특정 tool의 자세한 사용법을 보려면:
  help(tool_name='query_email')

{'='*60}
"""
        return help_text.strip()
